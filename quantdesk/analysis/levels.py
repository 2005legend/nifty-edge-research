"""The level map behind the room-to-run gate (spec §6.1 step 4.4, R24).

Levels are:
- round numbers (100s for Nifty, 500s for Sensex)
- the previous session's and the previous week's high, low and close
- session extremes touched at least twice, at least 3 minutes apart, within 0.05%

A level is opposing when it sits between the entry close and the planning target. Extremes count only up to
the moment of the decision.
"""

import math
from datetime import datetime, timedelta

import pandas as pd

from quantdesk.strategy.types import DayContext, Signal
from quantdesk.validation.hypotheses import param

NEAR_MULTIPLE = 3.0   # the location feature looks for a level within 3 stop-distances


def round_levels(lo: float, hi: float, step: int) -> list[float]:
    first = math.ceil(lo / step) * step
    return [float(x) for x in range(int(first), int(hi) + 1, step) if lo <= x <= hi]


def _touches(frame: pd.DataFrame, hit: pd.Series, min_gap_min: int) -> int:
    count, last = 0, None
    for ts in frame.loc[hit, "ts"]:
        if last is None or ts - last >= timedelta(minutes=min_gap_min):
            count, last = count + 1, ts
    return count


def multi_touch(frame: pd.DataFrame, upto: datetime, tol: float, min_touches: int,
                min_gap_min: int) -> tuple[float | None, float | None]:
    """(resistance, support): the session high/low if touched `min_touches` times, `min_gap_min` apart."""
    seen = frame[frame["ts"] <= upto]
    if seen.empty:
        return None, None
    high, low = float(seen["high"].max()), float(seen["low"].min())
    res = high if _touches(seen, seen["high"] >= high * (1 - tol), min_gap_min) >= min_touches else None
    sup = low if _touches(seen, seen["low"] <= low * (1 + tol), min_gap_min) >= min_touches else None
    return res, sup


def _candidates(ctx: DayContext, frame: pd.DataFrame, signal: Signal, h: dict, lo: float, hi: float) -> list[float]:
    step = param(h, "gate.round_step_sensex") if ctx.index == "SENSEX" else param(h, "gate.round_step_nifty")
    levels = round_levels(lo, hi, step) + list(ctx.prev_day) + list(ctx.prev_week)
    res, sup = multi_touch(frame, signal.at - timedelta(minutes=1), param(h, "gate.multi_touch_tolerance"),
                           param(h, "gate.multi_touch_min_touches"), param(h, "gate.multi_touch_min_gap_min"))
    extreme = res if signal.side == "long" else sup
    if extreme is not None:
        levels.append(extreme)
    return levels


def opposing_levels(ctx: DayContext, frame: pd.DataFrame, signal: Signal, h: dict) -> list[float]:
    lo, hi = sorted((signal.ref_close, signal.target_level))
    return sorted({lvl for lvl in _candidates(ctx, frame, signal, h, lo, hi) if lo < lvl < hi})


def nearest_opposing_distance(ctx: DayContext, frame: pd.DataFrame, signal: Signal, h: dict) -> float:
    reach = NEAR_MULTIPLE * signal.b
    if signal.side == "long":
        lo, hi = signal.ref_close, signal.ref_close + reach
    else:
        lo, hi = signal.ref_close - reach, signal.ref_close
    near = [abs(lvl - signal.ref_close) for lvl in _candidates(ctx, frame, signal, h, lo, hi) if lo < lvl < hi]
    return min(near) if near else math.inf
