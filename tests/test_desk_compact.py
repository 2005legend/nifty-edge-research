import json
from datetime import date, datetime, timedelta

import pandas as pd
import pytest

from quantdesk.desk.compact import (DEEP, QUICK, DeskError, GroqLLM, TooLarge, extract_json, format_desk, option_stats,
                                    run_desk, technical_stats, unverified_numbers)

BUNDLE = {"technical": {"NIFTY": {"last_close": 25010.5, "change_5d_pct": 1.2, "high_20d": 25400.0,
                                  "low_20d": 24300.0, "typical_move_pct": 0.8, "vix": 13.4, "vix_implied_move_pct": 0.84}},
          "macro": {"global": [{"name": "S&P 500", "change_pct": 0.6}], "fii_long_pct": 12.0, "events": []},
          "options": {"NIFTY": {"expiry": "2026-10-27", "pcr": 0.92, "max_call_oi_strike": 25500.0,
                                "max_put_oi_strike": 24800.0}},
          "news": {"headlines": [f"0{i}:00 Nifty headline {i}" for i in range(40)]}}

GOOD = {
    "analyst": {"view": "up", "confidence": 0.6, "points": ["Close 25010.5 sits below the 20-day high 25400"]},
    "case": {"points": ["PCR 0.92 is neutral to supportive"]},
    "risk": {"caution_flags": [{"flag": "event", "reason": "none scheduled"}], "notes": ["VIX 13.4 is calm"]},
    "judge": {"bias": "up", "confidence": 0.55, "expected_range_pct": 0.8,
              "summary": "Mild up bias; resistance near 25500, support near 24800.", "caution_flags": []},
}


class FakeLLM:
    def __init__(self, replies=None, too_large=()):
        self.calls, self.replies, self.too_large = [], replies or {}, list(too_large)
        self.usage = {}

    def call(self, model, system, user, max_tokens=900):
        role = system.split(":", 1)[0].strip().lower()
        self.calls.append((model, role, len(user)))
        if role in self.too_large:
            self.too_large.remove(role)
            raise TooLarge(role)
        kind = "analyst" if role in ("technical", "macro", "options", "news") else \
            "case" if role in ("bull", "bear") else role
        reply = self.replies.get(role, GOOD[kind])
        return reply.pop(0) if isinstance(reply, list) else reply


def test_json_comes_out_of_thinking_and_code_fences():
    assert extract_json('<think>hmm {"no": 1}</think>```json\n{"view": "up"}\n```') == {"view": "up"}
    with pytest.raises(DeskError):
        extract_json("no json here")


def test_the_number_checker_catches_a_planted_number():
    allowed = [25010.5, 0.92, 25500.0]
    assert unverified_numbers("Close 25,010 and PCR 0.92 with resistance at 25500", allowed) == []
    assert unverified_numbers("Close 25010 but resistance at 26200 on a 5-day view", allowed) == [26200.0]


def test_eight_calls_six_quick_two_deep_and_a_verified_brief():
    llm = FakeLLM()
    out = run_desk(BUNDLE, llm, date(2026, 10, 23))
    models = [m for m, _, _ in llm.calls]
    assert len(llm.calls) == 8 and models.count(QUICK) == 6 and models.count(DEEP) == 2
    assert [r for _, r, _ in llm.calls][-1] == "judge"
    assert out["judge"]["bias"] == "up" and out["verified"] and out["path"] == "B" and not out["failed_roles"]


def test_a_bad_reply_is_retried_once_and_an_invented_number_marks_the_brief_unverified():
    bad_then_good = [{"view": "sideways"}, GOOD["analyst"]]
    invented = dict(GOOD["judge"], summary="Target 26,900 by Friday")
    out = run_desk(BUNDLE, FakeLLM({"technical": bad_then_good, "judge": invented}), date(2026, 10, 23))
    assert out["views"]["technical"]["view"] == "up"
    assert not out["verified"] and 26900.0 in out["unverified"]


def test_a_too_large_prompt_is_shrunk_once_then_the_role_is_skipped():
    llm = FakeLLM(too_large=["news"])
    out = run_desk(BUNDLE, llm, date(2026, 10, 23))
    sizes = [n for _, r, n in llm.calls if r == "news"]
    assert len(sizes) == 2 and sizes[1] < sizes[0] and "news" not in out["failed_roles"]
    out = run_desk(BUNDLE, FakeLLM(too_large=["news", "news"]), date(2026, 10, 23))
    assert out["failed_roles"] == ["news"] and out["judge"]["bias"] == "up"


def test_groq_calls_back_off_on_429_and_ask_for_json():
    sent, waits = [], []

    class Response:
        def __init__(self, code, body):
            self.status_code, self._body = code, body
            self.text = json.dumps(body)

        def json(self):
            return self._body

    replies = [Response(429, {"error": "rate"}),
               Response(200, {"choices": [{"message": {"content": '{"view": "up"}'}}],
                              "usage": {"prompt_tokens": 100, "completion_tokens": 20}})]

    def post(url, json, headers, timeout):
        sent.append(json)
        return replies.pop(0)

    llm = GroqLLM("key", post=post, sleep=waits.append)
    assert llm.call(QUICK, "technical: x", "{}") == {"view": "up"}
    assert len(sent) == 2 and sent[0]["response_format"] == {"type": "json_object"} and waits
    assert llm.usage[QUICK] == 120


def test_groq_413_is_reported_as_too_large():
    class Response:
        status_code, text = 413, "Request too large"

    llm = GroqLLM("key", post=lambda *a, **k: Response(), sleep=lambda s: None)
    with pytest.raises(TooLarge):
        llm.call(QUICK, "news: x", "{}")


def test_the_inputs_are_our_own_numbers():
    days = [date(2026, 10, 1) + timedelta(days=i) for i in range(25)]
    daily = pd.DataFrame({"day": days, "open": 100.0, "high": [101.0 + i for i in range(25)],
                          "low": [99.0 + i for i in range(25)], "close": [100.0 + i for i in range(25)]})
    vix = pd.DataFrame({"day": days, "close": 16.0})
    t = technical_stats(daily, vix)
    assert t["last_close"] == 124.0 and t["change_5d_pct"] == pytest.approx(100 * (124 / 119 - 1), abs=0.01)
    assert t["vix_implied_move_pct"] == pytest.approx(16.0 / 252 ** 0.5, abs=0.01)
    eod = pd.DataFrame({"expiry": date(2026, 10, 27), "strike": [24900.0, 25000.0, 25100.0] * 2,
                        "option_type": ["CE"] * 3 + ["PE"] * 3, "oi": [10, 50, 90, 80, 40, 5]})
    o = option_stats(eod, 25000.0, 50)
    assert o["max_call_oi_strike"] == 25100.0 and o["max_put_oi_strike"] == 24900.0
    assert o["pcr"] == pytest.approx(125 / 150, abs=0.01)


def test_the_telegram_brief_says_what_it_is():
    out = run_desk(BUNDLE, FakeLLM(), date(2026, 10, 23))
    text = format_desk(out)
    assert text.startswith("DESK BRIEF") and "UP" in text and "explanation only" in text and "verified" in text
