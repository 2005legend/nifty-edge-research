"""SP4 Path B: the compact analyst desk (spec §7A.3-7A.6), chosen by the pilot's own rule on 22 Oct 2026.

Eight Groq calls each trading morning:
- four analysts on the quick model: technical, macro, options flow, news
- bull and bear on the quick model
- the risk manager and the judge on the deep model

Each prompt is built only from our computed numbers and timestamped headlines, and is kept under 5K tokens.
Each reply is JSON, validated with Pydantic and retried once when it does not match. A too-large prompt is
shrunk once and then skipped. Every number in the written text must match a number in the inputs (the
number-faithfulness check); a brief that fails is marked UNVERIFIED.

The desk explains; it never changes an alert (D7). Only public market data and our own numbers go to Groq.
Role design borrowed from TradingAgents (Apache-2.0).
"""

import hashlib
import json
import math
import re
from datetime import date, datetime, timedelta
from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field, ValidationError

QUICK, DEEP = "qwen/qwen3.8-27b", "openai/gpt-oss-120b"      # pinned for the scoring year (spec §7A.2)
URL = "https://api.groq.com/openai/v1/chat/completions"
MAX_PROMPT_TOKENS = 5000
CHARS_PER_TOKEN = 3.5
STEP = {"NIFTY": 50, "SENSEX": 100}


class DeskError(RuntimeError):
    pass


class TooLarge(DeskError):
    pass


class Flag(BaseModel):
    flag: str
    reason: str


class AnalystView(BaseModel):
    view: Literal["up", "down", "neutral"]
    confidence: float = Field(ge=0, le=1)
    points: list[str] = Field(default_factory=list, max_length=5)


class Case(BaseModel):
    points: list[str] = Field(min_length=1, max_length=5)


class RiskView(BaseModel):
    caution_flags: list[Flag] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class Judge(BaseModel):
    bias: Literal["up", "down", "neutral"]
    confidence: float = Field(ge=0, le=1)
    expected_range_pct: float = Field(gt=0, lt=10)
    summary: str
    caution_flags: list[Flag] = Field(default_factory=list)


HINTS = {
    AnalystView: '{"view": "up|down|neutral", "confidence": 0-1, "points": ["<= 4 short points"]}',
    Case: '{"points": ["<= 4 short points"]}',
    RiskView: '{"caution_flags": [{"flag": "...", "reason": "..."}], "notes": ["..."]}',
    Judge: '{"bias": "up|down|neutral", "confidence": 0-1, "expected_range_pct": <percent>, "summary": "2-3 '
           'sentences", "caution_flags": [{"flag": "...", "reason": "..."}]}',
}
ROLES = {
    "technical": ("technical analyst", "Read trend, momentum and levels for today's session."),
    "macro": ("macro analyst", "Read global cues, FII positioning and scheduled events for today."),
    "options": ("options-flow analyst", "Read the put/call ratio and the strikes with the most open interest."),
    "news": ("news analyst", "Read the headlines since yesterday's close for what can move the indices today."),
    "bull": ("bull researcher", "Make the strongest honest case for the indices rising today."),
    "bear": ("bear researcher", "Make the strongest honest case for the indices falling today."),
    "risk": ("risk manager", "Name what could go wrong for an intraday options buyer today: events, volatility, "
                             "crowded positioning. Be concrete."),
    "judge": ("judge", "Weigh the analysts, the bull and the bear and the risk manager. Give the day's bias, your "
                       "confidence (0.5 means no edge) and the expected index range in percent."),
}


def system_prompt(role: str, schema) -> str:
    title, task = ROLES[role]
    return (f"{role}: You are the {title} on an Indian index-options analyst desk (Nifty 50 and Sensex). {task} "
            "Use only the numbers in the input; never invent prices, levels, dates or statistics. This is "
            "explanation only: never give position sizes or say what to buy. Reply with one JSON object only, "
            f"matching: {HINTS[schema]}")


def extract_json(text: str) -> dict:
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise DeskError("no JSON object in the reply")
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError as exc:
        raise DeskError(f"reply is not valid JSON: {exc}") from exc


NUMBER = re.compile(r"(?<![\w.])[-+]?\d[\d,]*(?:\.\d+)?")


def numbers_in(text: str) -> list[float]:
    out = []
    for raw in NUMBER.findall(text or ""):
        clean = raw.replace(",", "").lstrip("+")
        try:
            value = float(clean)
        except ValueError:
            continue
        integer = "." not in clean
        if integer and len(clean.lstrip("-")) <= 2:              # counts and windows: "5-day", "3 flags"
            continue
        if integer and 1990 <= abs(value) <= 2100:                # years
            continue
        out.append(value)
    return out


def bundle_numbers(obj) -> list[float]:
    if isinstance(obj, bool) or obj is None:
        return []
    if isinstance(obj, (int, float)):
        return [] if isinstance(obj, float) and math.isnan(obj) else [float(obj)]
    if isinstance(obj, str):
        return numbers_in(obj)
    if isinstance(obj, dict):
        return [n for v in obj.values() for n in bundle_numbers(v)]
    if isinstance(obj, (list, tuple)):
        return [n for v in obj for n in bundle_numbers(v)]
    return []


def unverified_numbers(text: str, allowed: list[float], rel: float = 0.005, abs_tol: float = 0.051) -> list[float]:
    """Numbers in `text` that match no input value within 0.5% (or 0.05 absolute). Signs are ignored, so
    "fell 1.2%" matches an input of -1.2."""
    pool = [abs(a) for a in allowed]
    return [n for n in numbers_in(text) if not any(abs(abs(n) - a) <= max(abs_tol, rel * a) for a in pool)]


def _shrink(payload):
    """Halve every list longer than 5, recursively: the headlines first and foremost."""
    if isinstance(payload, dict):
        return {k: _shrink(v) for k, v in payload.items()}
    if isinstance(payload, list):
        kept = payload[: max(5, len(payload) // 2)] if len(payload) > 5 else payload
        return [_shrink(v) for v in kept]
    return payload


def _fit(payload, system: str):
    while len(system + json.dumps(payload, default=str)) / CHARS_PER_TOKEN > MAX_PROMPT_TOKENS:
        smaller = _shrink(payload)
        if smaller == payload:
            break
        payload = smaller
    return payload


def _ask(llm, role: str, model: str, schema, payload) -> dict:
    system = system_prompt(role, schema)
    payload, shrunk, note = _fit(payload, system), False, ""
    for _ in range(4):
        try:
            raw = llm.call(model, system + note, json.dumps(payload, default=str))
        except TooLarge:
            if shrunk:
                raise DeskError(f"{role}: too large even after shrinking") from None
            payload, shrunk = _shrink(payload), True
            continue
        try:
            return schema.model_validate(raw).model_dump()
        except ValidationError as exc:
            if note:
                raise DeskError(f"{role}: the reply did not match the schema twice") from exc
            note = (f" Your last reply did not match the schema ({str(exc).splitlines()[0][:160]}). "
                    "Reply again with JSON only.")
    raise DeskError(f"{role}: no valid reply")


def run_desk(bundle: dict, llm, day: date) -> dict:
    views, failed = {}, []
    for role in ("technical", "macro", "options", "news"):
        try:
            views[role] = _ask(llm, role, QUICK, AnalystView, bundle.get(role, {}))
        except DeskError:
            failed.append(role)
    key = {"technical": bundle.get("technical"), "options": bundle.get("options")}
    cases = {}
    for role in ("bull", "bear"):
        try:
            cases[role] = _ask(llm, role, QUICK, Case, {"analysts": views, **key})
        except DeskError:
            failed.append(role)
    risk = judge = None
    try:
        risk = _ask(llm, "risk", DEEP, RiskView, {"analysts": views, **cases, "macro": bundle.get("macro"), **key})
    except DeskError:
        failed.append("risk")
    try:
        judge = _ask(llm, "judge", DEEP, Judge, {"analysts": views, **cases, "risk": risk, **key})
    except DeskError:
        failed.append("judge")
    written = [p for v in views.values() for p in v["points"]] + [p for c in cases.values() for p in c["points"]]
    if risk:
        written += risk["notes"] + [f["reason"] for f in risk["caution_flags"]]
    if judge:
        written += [judge["summary"]] + [f["reason"] for f in judge["caution_flags"]]
    unverified = unverified_numbers("\n".join(written), bundle_numbers(bundle))
    digest = hashlib.sha256(json.dumps(bundle, sort_keys=True, default=str).encode()).hexdigest()[:16]
    return {"date": day.isoformat(), "run": "morning", "path": "B", "models": {"quick": QUICK, "deep": DEEP},
            "views": views, "bull": cases.get("bull"), "bear": cases.get("bear"), "risk": risk, "judge": judge,
            "verified": not unverified and judge is not None, "unverified": unverified, "input_hash": digest,
            "tokens": dict(getattr(llm, "usage", {})), "failed_roles": failed}


def format_desk(out: dict) -> str:
    day = date.fromisoformat(out["date"])
    lines = [f"DESK BRIEF {day:%a %d %b} (AI, explanation only - not advice)"]
    j = out.get("judge")
    if j:
        lines += [f"Bias: {j['bias'].upper()} (confidence {100 * j['confidence']:.0f}%) | expected range "
                  f"+/-{j['expected_range_pct']:.2f}%", f"Summary: {j['summary']}"]
    else:
        lines.append("Judge unavailable today; analyst views below.")
    for role in ("bull", "bear"):
        if out.get(role):
            lines.append(f"{role.title()}: " + "; ".join(out[role]["points"]))
    flags = (out.get("risk") or {}).get("caution_flags", []) + ((j or {}).get("caution_flags") or [])
    flags = list({(f["flag"], f["reason"]): f for f in flags}.values())          # risk and judge often agree
    if flags:
        lines.append("Caution: " + "; ".join(f"{f['flag']} - {f['reason']}" for f in flags[:4]))
    if out["views"]:
        lines.append("Analysts: " + ", ".join(f"{k} {v['view']} {v['confidence']:.2f}" for k, v in out["views"].items()))
    lines.append("Numbers: verified against our data" if out["verified"] else
                 "Numbers: UNVERIFIED - not in our data: " + ", ".join(f"{n:g}" for n in out["unverified"][:6]))
    if out["failed_roles"]:
        lines.append("Skipped roles: " + ", ".join(out["failed_roles"]))
    return "\n".join(lines)


class GroqLLM:
    """Groq's OpenAI-compatible endpoint with JSON replies, the per-model token bucket (pilot.TokenBucket), backoff
    on 429 and 5xx, and 413 reported as TooLarge. The key goes only in the Authorization header, never in a log."""

    def __init__(self, key: str, post=None, sleep=None, clock=None):
        import time

        import requests

        from quantdesk.desk.pilot import CLIENT_TPM, TokenBucket

        self.key, self.post = key, post or requests.post
        self.sleep = sleep or time.sleep
        clock = clock or _SystemClock()
        self.buckets: dict[str, TokenBucket] = {}
        self._bucket = lambda model: self.buckets.setdefault(model, TokenBucket(CLIENT_TPM, 60, clock=clock,
                                                                                 sleep=self.sleep))
        self.usage: dict[str, int] = {}

    def call(self, model: str, system: str, user: str, max_tokens: int = 900) -> dict:
        body = {"model": model, "temperature": 0.2, "max_tokens": max_tokens,
                "response_format": {"type": "json_object"},
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        self._bucket(model).acquire(int(len(system + user) / CHARS_PER_TOKEN) + max_tokens)
        for attempt in range(4):
            r = self.post(URL, json=body, headers={"Authorization": f"Bearer {self.key}"}, timeout=90)
            code, text = r.status_code, (getattr(r, "text", "") or "")
            if code == 200:
                data = r.json()
                usage = data.get("usage") or {}
                self.usage[model] = self.usage.get(model, 0) + int(usage.get("prompt_tokens", 0)) + \
                    int(usage.get("completion_tokens", 0))
                return extract_json(data["choices"][0]["message"].get("content") or "")
            if code == 413 or "too large" in text.lower():
                raise TooLarge(f"{model}: request too large")
            if code == 400 and "response_format" in body and "json" in text.lower():
                body.pop("response_format")                         # a model without JSON mode: ask in the prompt
                continue
            if code == 429 or code >= 500:
                self.sleep(min(60, 5 * 2 ** attempt))
                continue
            raise DeskError(f"groq HTTP {code}: {text[:200]}")
        raise DeskError(f"groq: no answer after retries ({model})")


class _SystemClock:
    def now(self):
        return datetime.now()


# --- inputs: our own numbers only ---------------------------------------------------------------------

def technical_stats(daily: pd.DataFrame, vix: pd.DataFrame) -> dict:
    d = daily.sort_values("day").reset_index(drop=True)
    c = d["close"].astype(float)
    pct = lambda n: round(100 * (c.iloc[-1] / c.iloc[-1 - n] - 1), 2) if len(c) > n else None  # noqa: E731
    moves = (c.pct_change().abs() * 100).dropna().tail(14)
    v = vix.sort_values("day")["close"].astype(float).reset_index(drop=True)
    return {"as_of": str(d["day"].iloc[-1]), "last_close": round(float(c.iloc[-1]), 2),
            "change_1d_pct": pct(1), "change_5d_pct": pct(5), "change_20d_pct": pct(20),
            "high_20d": round(float(d["high"].tail(20).max()), 2), "low_20d": round(float(d["low"].tail(20).min()), 2),
            "prev_high": round(float(d["high"].iloc[-1]), 2), "prev_low": round(float(d["low"].iloc[-1]), 2),
            "typical_move_pct": round(float(moves.mean()), 2) if len(moves) else None,
            "vix": round(float(v.iloc[-1]), 2) if len(v) else None,
            "vix_change_5d_pct": round(100 * (v.iloc[-1] / v.iloc[-6] - 1), 2) if len(v) > 5 else None,
            "vix_implied_move_pct": round(float(v.iloc[-1]) / math.sqrt(252), 2) if len(v) else None}


def option_stats(eod: pd.DataFrame, last_close: float, step: int, n_steps: int = 5) -> dict:
    from quantdesk.analysis.options_implied import pcr_oi

    expiry = min(eod["expiry"])
    near = eod[eod["expiry"] == expiry]
    calls, puts = near[near["option_type"] == "CE"], near[near["option_type"] == "PE"]
    pcr = pcr_oi(eod, expiry, last_close, step, n_steps)
    return {"expiry": str(expiry), "pcr": round(pcr, 2) if pcr is not None else None,
            "max_call_oi_strike": float(calls.loc[calls["oi"].idxmax(), "strike"]) if len(calls) else None,
            "max_put_oi_strike": float(puts.loc[puts["oi"].idxmax(), "strike"]) if len(puts) else None}


def recent_headlines(store, day: date, limit: int = 30) -> list[str]:
    """"HH:MM title" since the previous session's close, newest first, price restatements dropped."""
    since = pd.Timestamp(datetime.combine(day - timedelta(days=1), datetime.min.time())).tz_localize(
        "Asia/Kolkata") + pd.Timedelta(hours=15, minutes=30)
    rows = []
    for d in (day - timedelta(days=1), day):
        n = store.read("news", d)
        if len(n):
            if "price_restatement" in n:
                n = n[~n["price_restatement"].fillna(False).astype(bool)]
            seen = pd.to_datetime(n["first_seen"], utc=True, errors="coerce").dt.tz_convert("Asia/Kolkata")
            rows += [(s, str(t)) for s, t in zip(seen, n["title"]) if pd.notna(s) and s >= since and pd.notna(t)]
    rows = sorted({t: s for s, t in rows}.items(), key=lambda x: x[1], reverse=True)[:limit]
    return [f"{s:%H:%M} {t}" for t, s in rows]


def build_bundle(store, derived, day: date, events: list) -> dict:
    from quantdesk.live.brief import brief_extras

    extras = brief_extras(store, derived, day)
    technical, options = {}, {}
    vix = derived.read("daily", where=f"target = 'INDIAVIX' and day < DATE '{day}'", columns="day, close")
    for index in ("NIFTY", "SENSEX"):
        daily = derived.read("daily", where=f"target = '{index}' and day < DATE '{day}'",
                             columns="day, open, high, low, close").sort_values("day").tail(30)
        if len(daily) < 6:
            continue
        technical[index] = technical_stats(daily, vix.sort_values("day").tail(30))
        last = derived.read("options_eod", where=f"symbol = '{index}' and instrument = 'IDO' and day < DATE '{day}'",
                            columns="max(day) as d")["d"].iloc[0]
        if last is not None and not pd.isna(last):
            eod = derived.read("options_eod", where=f"symbol = '{index}' and instrument = 'IDO' and day = DATE '{last}'",
                               columns="expiry, strike, option_type, oi")
            eod = eod[eod["expiry"] >= day]
            if len(eod):
                options[index] = {"chain_of": str(last), **option_stats(eod, technical[index]["last_close"], STEP[index])}
    soon = [{"date": str(e.date), "time": str(e.time) if e.time else None, "title": e.title}
            for e in events if day <= e.date <= day + timedelta(days=1) and e.type != "holiday_nse"]
    fii = extras.get("fii")
    return {"technical": technical, "options": options,
            "macro": {"global": [{"name": c["name"], "change_pct": round(c["change_pct"], 2)} for c in extras["cues"]],
                      "fii_index_futures_long_pct": round(100 * fii[0], 1) if fii else None,
                      "fii_long_pct_week_ago": round(100 * fii[1], 1) if fii and fii[1] is not None else None,
                      "events_today_tomorrow": soon},
            "news": {"headlines": recent_headlines(store, day)}}
