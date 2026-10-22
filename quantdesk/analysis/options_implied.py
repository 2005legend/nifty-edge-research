"""The options-implied family inputs, from the previous session's bhavcopy only (R26, design §9).

- PCR_OI: put open interest over call open interest near the money, nearest weekly.
- RR25: the 25-delta risk reversal, the call's implied vol minus the put's, from traded closes only.

Both are known on the morning of the day they are used, in the backtest and live alike. A positive value
supports a long (high PCR read contrarian, calls richer than puts). The meta-model learns the actual weights.
"""

import math
from datetime import date, datetime, time

import numpy as np
import pandas as pd

from quantdesk.black76 import greeks, implied_vol
from quantdesk.clock import IST
from quantdesk.pricing.clock import Clock
from quantdesk.pricing.quotes import sessions_left

KINDS = {"CE": "call", "PE": "put"}


def pcr_oi(eod: pd.DataFrame, expiry: date, center: float, step: int, n_steps: int) -> float | None:
    near = eod[(eod["expiry"] == expiry) & ((eod["strike"] - center).abs() <= n_steps * step)]
    calls = near.loc[near["option_type"] == "CE", "oi"].sum()
    puts = near.loc[near["option_type"] == "PE", "oi"].sum()
    return float(puts / calls) if calls > 0 else None


def _iv_by_delta(rows: pd.DataFrame, F: float, T: float, kind: str) -> pd.DataFrame:
    out = []
    for r in rows.itertuples():
        try:
            iv = implied_vol(float(r.close), F, float(r.strike), T, kind=kind)
        except ValueError:
            continue
        if iv <= 1e-4:
            continue
        out.append((greeks(F, float(r.strike), T, iv, kind=kind)["delta"], iv))
    return pd.DataFrame(out, columns=["delta", "iv"]).sort_values("delta")


def rr25(eod: pd.DataFrame, expiry: date, F: float, T_bt: float, rr_delta: float) -> float | None:
    rows = eod[(eod["expiry"] == expiry) & eod["traded"].fillna(False).astype(bool)]
    calls = _iv_by_delta(rows[rows["option_type"] == "CE"], F, T_bt, "call")
    puts = _iv_by_delta(rows[rows["option_type"] == "PE"], F, T_bt, "put")
    if len(calls) < 2 or len(puts) < 2:
        return None
    if not (calls["delta"].min() <= rr_delta <= calls["delta"].max()
            and puts["delta"].min() <= -rr_delta <= puts["delta"].max()):
        return None
    call_iv = float(np.interp(rr_delta, calls["delta"], calls["iv"]))
    put_iv = float(np.interp(-rr_delta, puts["delta"], puts["iv"]))
    return call_iv - put_iv


def options_raw(eod_prev: pd.DataFrame, ctx_like: dict, clock: Clock, params: dict) -> dict | None:
    """`ctx_like`: prev_close, step, at (the previous close), expiries (nearest first)."""
    at: datetime = ctx_like["at"]
    ahead = [e for e in ctx_like["expiries"] if e is not None and sessions_left(clock, at.date(), e) >= 1]
    if not ahead or eod_prev.empty:
        return None
    expiry = ahead[0]
    T = clock.bt(at, datetime.combine(expiry, time(15, 30), tzinfo=IST))
    pcr = pcr_oi(eod_prev, expiry, ctx_like["prev_close"], ctx_like["step"], params["strike_steps"])
    rr = rr25(eod_prev, expiry, ctx_like["prev_close"], T, params["rr_delta"])
    if pcr is None and rr is None:
        return None
    return {"pcr": pcr if pcr is not None else math.nan, "rr25": rr if rr is not None else math.nan}
