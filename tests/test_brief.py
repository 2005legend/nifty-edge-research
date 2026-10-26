from datetime import date, datetime, timedelta

import pandas as pd
import pytest

from quantdesk.clock import IST
from quantdesk.live.brief import day_summary, global_cues, lean, morning_brief, news_sentiment, scorecard
from quantdesk.live.journal import Journal
from tests.test_journal import alert
from tests.test_pipeline import setup

AT = datetime(2026, 10, 23, 9, 20, tzinfo=IST)


def test_news_sentiment_counts_rising_and_falling_words():
    s = news_sentiment(["Sensex surges 600 points as banks rally", "Rupee falls to record low",
                        "Nifty slumps on war fears", "RBI policy today"])
    assert (s["positive"], s["negative"], s["headlines"]) == (1, 2, 4) and s["label"] == "negative"
    assert news_sentiment([])["label"] == "no news"


def test_global_cues_are_the_latest_change_of_each_series():
    rows = pd.DataFrame({"series_id": ["spx", "spx", "brent", "brent"],
                         "date": [date(2026, 10, 21), date(2026, 10, 22)] * 2, "value": [5000.0, 5050.0, 80.0, 78.0]})
    cues = {c["name"]: c for c in global_cues(rows)}
    assert cues["S&P 500"]["change_pct"] == pytest.approx(1.0) and cues["Brent"]["change_pct"] == pytest.approx(-2.5)


def test_the_lean_needs_a_clear_score_and_says_why():
    assert lean(0.6, 0.5, 0.4)[0] == "UP" and lean(-0.6, -0.5, 0.0)[0] == "DOWN"
    label, score, parts = lean(0.2, -0.1, 0.1)
    assert label == "FLAT" and set(parts) == {"options", "FII", "global"}


def test_the_morning_brief_has_the_range_levels_and_lean():
    ctx, frame, _ = setup()
    text, leans = morning_brief(AT, {"NIFTY": ctx}, {"NIFTY": frame},
                                {"cues": [{"name": "S&P 500", "value": 5050.0, "change_pct": 1.0}],
                                 "news": news_sentiment(["Nifty rallies"]), "fii": (0.42, 0.35)}, {})
    lo, hi = ctx.open * (1 - ctx.sigma_day), ctx.open * (1 + ctx.sigma_day)
    assert text.startswith("MORNING BRIEF") and "NIFTY" in text and f"{lo:,.0f}" in text and f"{hi:,.0f}" in text
    assert "S&P 500 +1.0%" in text and "FII" in text and leans["NIFTY"] in ("UP", "DOWN", "FLAT")


def _idea_trade(j, at, pnl):
    a = j.add_alert(alert(at=at, mode="idea"))
    p = j.open_paper(a, at, 100.0)
    j.close_paper(p, at + timedelta(minutes=40), 100.0 + pnl / 65, "target" if pnl > 0 else "stop", pnl)


def test_the_friday_scorecard_counts_the_week_in_rupees_per_lot(tmp_path):
    j = Journal(tmp_path / "j.sqlite")
    _idea_trade(j, datetime(2026, 10, 19, 10, 0, tzinfo=IST), 500.0)
    _idea_trade(j, datetime(2026, 10, 21, 11, 0, tzinfo=IST), -200.0)
    _idea_trade(j, datetime(2026, 10, 12, 11, 0, tzinfo=IST), -900.0)          # last week: not counted
    j.set_state("lean_2026-10-19_NIFTY", "UP")
    j.set_state("lean_result_2026-10-19_NIFTY", "right")
    text = scorecard(j, date(2026, 10, 23))
    assert "2 ideas" in text and "1 hit target" in text and "Rs +300" in text and "1 of 1" in text


def test_the_midday_update_gives_levels_and_option_prices_for_the_afternoon():
    from quantdesk.live.brief import midday_update
    from tests.test_pipeline import AT, ConvexQuotes

    ctx, frame, _ = setup()                                   # open 21980, sigma_day 1%, closes 22010
    frame = frame.assign(high=frame["close"] + 30, low=frame["close"] - 40)
    text = midday_update(AT.replace(hour=12, minute=15), {"NIFTY": ctx}, {"NIFTY": frame},
                         {"NIFTY": ConvexQuotes(frame)}, {"NIFTY": "down"}, remaining=0.36)
    assert text.startswith("MIDDAY 12:15") and "NIFTY 22,010" in text and "VWAP" in text
    assert "Expected range 21,760 - 22,200" in text                           # open +/- 1%
    assert "DOWN case: target" in text and "PE" in text and "UP case" not in text   # the morning view's side only
    assert "now" in text and "at target" in text and "at stop" in text
    both = midday_update(AT.replace(hour=12, minute=15), {"NIFTY": ctx}, {"NIFTY": frame},
                         {"NIFTY": ConvexQuotes(frame)}, {}, remaining=0.36)
    assert "UP case" in both and "DOWN case" in both                          # no morning view: both sides


def test_the_desk_bias_is_scored_daily_and_counted_on_friday(tmp_path):
    j = Journal(tmp_path / "j.sqlite")
    ctx, _, _ = setup()
    j.set_state("desk_bias_2026-10-22", "down")
    text = day_summary(date(2026, 10, 22), {"NIFTY": ctx}, {"NIFTY": (ctx.open, ctx.open * 0.99)}, j, {})
    assert "Desk bias DOWN: right" in text and j.get_state("desk_result_2026-10-22") == "right"
    assert "Desk bias right: 1 of 1" in scorecard(j, date(2026, 10, 23))


def test_the_day_summary_compares_the_move_with_the_forecast(tmp_path):
    j = Journal(tmp_path / "j.sqlite")
    _idea_trade(j, datetime(2026, 10, 23, 10, 0, tzinfo=IST), 650.0)
    ctx, _, _ = setup()
    text = day_summary(date(2026, 10, 23), {"NIFTY": ctx}, {"NIFTY": (ctx.open, ctx.open * 1.02)}, j,
                       {"NIFTY": "UP"})
    assert "NIFTY" in text and "+2.00%" in text and "outside" in text and "lean UP: right" in text
    assert "1 idea" in text and "Rs +650" in text and j.get_state("lean_result_2026-10-23_NIFTY") == "right"
