"""H1, the noise-band breakout (spec §6.1 step 3): a close outside the band on the same side as VWAP.

The check at T reads the bar stamped T - 1 minute, the last one closed (R4). The structural stop is the
tighter of the band edge and VWAP on the protective side (R19), and the planning target is 2.3 stop-distances
beyond the close (spec §2).
"""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from quantdesk.analysis.bands import band_edges, slot
from quantdesk.strategy.types import DayContext, Signal
from quantdesk.validation.hypotheses import param


def h1(frame: pd.DataFrame, at: datetime, ctx: DayContext, h: dict) -> Signal | None:
    bar_ts = at - timedelta(minutes=1)
    rows = frame[frame["ts"] == bar_ts]
    if rows.empty:
        return None
    s = slot(bar_ts)
    if not 0 <= s < len(ctx.band_sigma) or np.isnan(ctx.band_sigma[s]):
        return None
    row = rows.iloc[-1]
    upper, lower = band_edges(ctx.open, ctx.prev_close, float(ctx.band_sigma[s]), param(h, "h1.band_v"))
    close, vwap = float(row["close"]), float(row["vwap"])
    multiple = param(h, "stop.planning_target_multiple")
    if close > upper and close > vwap:
        stop = max(upper, vwap)
        b = close - stop
        return Signal(ctx.index, at, "long", close, upper, lower, vwap, stop, b, close + multiple * b)
    if close < lower and close < vwap:
        stop = min(lower, vwap)
        b = stop - close
        return Signal(ctx.index, at, "short", close, upper, lower, vwap, stop, b, close - multiple * b)
    return None
