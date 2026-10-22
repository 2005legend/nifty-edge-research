"""The macro engine (spec §5A.2, design §9): event gates, the intraday VIX block, the stress score and the
macro family score.

Only scheduled events act through the calendar. An off-cycle RBI move was not known in advance (R9), so it
can reach a decision only through the shock or headline paths.
"""

import math
from datetime import date, datetime, time, timedelta

import pandas as pd

from quantdesk.validation.hypotheses import param

REBALANCE_EXIT = time(15, 0)


def _hhmm(text: str) -> time:
    return time.fromisoformat(text)


def _today(events, day: date):
    return [e for e in events if e.date == day and e.scheduled]


def event_block(events, at: datetime, h: dict) -> str | None:
    """Why no entry is allowed at `at`, or None."""
    for event in _today(events, at.date()):
        if event.gate == "E3":
            return "E3"
        moment = at.timetz().replace(tzinfo=None)
        if event.type == "rbi_mpc" and event.time is not None:
            ready = (datetime.combine(at.date(), event.time) + timedelta(minutes=param(h, "event.rbi_wait_min"))).time()
            if moment < ready:
                return "rbi_wait"
        if event.type == "budget" and moment < _hhmm(param(h, "event.budget_no_entry_before")):
            return "budget_wait"
    return None


def event_delta(events, h: dict) -> float:
    """The extra hurdle on a Budget day (R27); the day of `events` is the one being traded."""
    return param(h, "event.budget_delta") if any(e.type == "budget" and e.scheduled for e in events) else 0.0


def hard_exit(day: date, is_expiry_day: bool, events, h: dict) -> time:
    if is_expiry_day:
        return _hhmm(param(h, "time.hard_exit_expiry"))
    if any(e.type == "index_rebalance" for e in _today(events, day)):
        return _hhmm(param(h, "event.rebalance_hard_exit"))
    return _hhmm(param(h, "time.hard_exit"))


def timed_event_exits(events, day: date) -> list[datetime]:
    """Five minutes before each scheduled event with a time: a position is closed before the news."""
    from quantdesk.clock import IST
    return sorted(datetime.combine(day, e.time, tzinfo=IST) - timedelta(minutes=5)
                  for e in _today(events, day) if e.time is not None)


def vix_block(vix_now: float, vix_prev_close: float, band: float) -> bool:
    return abs(vix_now / vix_prev_close - 1.0) > band


def _series(macro: pd.DataFrame, sid: str) -> pd.Series:
    rows = macro[macro["series_id"] == sid].sort_values("date")
    return rows.set_index("date")["value"].astype(float)


def _change(values: pd.Series, lag: int = 5) -> float | None:
    if len(values) <= lag:
        return None
    return float(values.iloc[-1] / values.iloc[-1 - lag] - 1.0)


def stress_score(macro: pd.DataFrame, day: date) -> int:
    """0-8 points from oil, the rupee, US and Indian yields, and the dollar (R25). `macro` is already as of 09:05."""
    known = macro                  # availability is the caller's AsOf read (design §4), not a date cut here
    score = 0
    brent = _series(known, "brent")
    if len(brent) and brent.iloc[-1] >= 95:
        score += 1
    change = _change(brent)
    if change is not None:
        score += 2 if change >= 0.10 else 1 if change >= 0.05 else 0
    change = _change(_series(known, "usdinr"))
    if change is not None:
        score += 2 if change >= 0.015 else 1 if change >= 0.0075 else 0
    us10y = _series(known, "dgs10")
    if len(us10y) > 5 and us10y.iloc[-1] - us10y.iloc[-6] >= 0.15:          # percent: +15 bp
        score += 1
    change = _change(_series(known, "india_gsec10y_price"))
    if change is not None and -change / 7.0 >= 0.0015:                        # dy ~ -(dP/P) / duration 7
        score += 1
    change = _change(_series(known, "dxy"))
    if change is not None and change >= 0.015:
        score += 1
    return score


def stress_delta(score: int, full: bool, h: dict) -> float:
    """Tiers 0 / +0.02 / +0.04; capped at +0.02 unless RV-1 has been accepted (spec §5A.2)."""
    tier = 0.04 if score >= 5 else 0.02 if score >= 3 else 0.0
    return tier if full else min(tier, param(h, "hurdle.stress_cap_without_rv1"))


def macro_raw(holiday_before: bool, r_on: float, fii_ratios: pd.Series, window: int) -> float:
    """Long-aligned macro score in [-2, 2]: fade a post-holiday gap, follow a recent FII flip (R39)."""
    fade = -math.copysign(1.0, r_on) if holiday_before and r_on != 0 else 0.0
    recent = fii_ratios.dropna().iloc[-window:]
    flip = 0.0
    if len(recent) >= 2:
        sides = (recent > 0.5).astype(int)
        if sides.diff().abs().iloc[1:].any():
            flip = 1.0 if recent.iloc[-1] > 0.5 else -1.0
    return fade + flip
