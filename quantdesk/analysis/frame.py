"""The per-minute frame every gate reads (design §9), and the registry of features the truncation test covers.

One row per index minute. Row ts uses only data stamped at or before ts:
- cumulative sums for VWAP
- running max and min for the session extremes
- last-known values carried forward for breadth and VIX

Every column a gate reads must be listed in FEATURES. `tests/test_truncation.py` then proves that no feature
changes when the future is cut away (R4).
"""

from collections.abc import Callable
from datetime import timedelta

import numpy as np
import pandas as pd

from quantdesk.analysis.bands import band_edges, slot
from quantdesk.analysis.vwap import vwap_proxy
from quantdesk.strategy.types import DayContext
from quantdesk.validation.hypotheses import param

BREADTH = ["adv", "dec", "above_vwap", "top5_ret", "members_total"]


def build_minute_frame(index_bars: pd.DataFrame, members: pd.DataFrame, vix_bars: pd.DataFrame, ctx: DayContext,
                       h: dict, atm_premium: Callable[[object, float, float], float] | None = None) -> pd.DataFrame:
    bars = index_bars.sort_values("ts").reset_index(drop=True)
    tv = members.set_index("ts")["tv"] if len(members) else pd.Series(dtype=float)
    frame = bars[["ts", "open", "high", "low", "close"]].copy()
    frame = frame.merge(vwap_proxy(bars, tv), on="ts", how="left")
    v = param(h, "h1.band_v")
    edges = [band_edges(ctx.open, ctx.prev_close, float(ctx.band_sigma[s]), v)
             if 0 <= (s := slot(ts)) < len(ctx.band_sigma) and not np.isnan(ctx.band_sigma[s]) else (np.nan, np.nan)
             for ts in frame["ts"]]
    frame["upper"] = [e[0] for e in edges]
    frame["lower"] = [e[1] for e in edges]
    vix = vix_bars.set_index("ts")["close"].rename("vix") if len(vix_bars) else pd.Series(dtype=float, name="vix")
    frame = frame.merge(vix, left_on="ts", right_index=True, how="left")
    frame["vix"] = frame["vix"].ffill()
    breadth = members.set_index("ts")[BREADTH] if len(members) else pd.DataFrame(columns=BREADTH)
    frame = frame.merge(breadth, left_on="ts", right_index=True, how="left")
    frame[BREADTH] = frame[BREADTH].ffill()
    total = frame["members_total"]
    frame["adv_share"] = (frame["adv"] - frame["dec"]) / total
    frame["above_share"] = frame["above_vwap"] / total
    frame["session_high"] = frame["high"].cummax()
    frame["session_low"] = frame["low"].cummin()
    if atm_premium is None:
        frame["atm_premium"] = np.nan
    else:
        frame["atm_premium"] = [atm_premium(ts, c, x) if not np.isnan(x) else np.nan
                                for ts, c, x in zip(frame["ts"], frame["close"], frame["vix"])]
    frame["available_at"] = frame["ts"] + timedelta(minutes=1)
    return frame.drop(columns=["adv", "dec", "above_vwap", "members_total"])


def _column(name: str) -> Callable[[pd.DataFrame], pd.Series]:
    return lambda frame: frame[name]


FEATURES: dict[str, Callable[[pd.DataFrame], pd.Series]] = {
    name: _column(name) for name in ("vwap", "vwap_sd", "upper", "lower", "vix", "adv_share", "above_share",
                                     "top5_ret", "session_high", "session_low", "atm_premium")}
