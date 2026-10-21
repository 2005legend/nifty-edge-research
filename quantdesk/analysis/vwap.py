"""The stock-volume VWAP proxy (spec §6.0, design §9): the index's typical price, weighted minute by minute
by the traded value of the Nifty 50 members.

The index has no volume of its own, so its members' traded value is the weight. A minute with no traded
value adds nothing. Before any value has traded, the VWAP is the first minute's typical price, so a quiet open
never divides by zero. Only cumulative sums are used: the value at minute t uses nothing after t (R4).
"""

import numpy as np
import pandas as pd


def vwap_proxy(index_bars: pd.DataFrame, tv: pd.Series) -> pd.DataFrame:
    bars = index_bars.sort_values("ts").reset_index(drop=True)
    typical = ((bars["high"] + bars["low"] + bars["close"]) / 3.0).to_numpy(dtype=float)
    weight = tv.reindex(bars["ts"]).fillna(0.0).to_numpy(dtype=float) if len(tv) else np.zeros(len(bars))
    cum_w = np.cumsum(weight)
    cum_wp = np.cumsum(weight * typical)
    cum_wp2 = np.cumsum(weight * typical * typical)
    with np.errstate(invalid="ignore", divide="ignore"):
        vwap = np.where(cum_w > 0, cum_wp / cum_w, np.nan)
        var = np.where(cum_w > 0, cum_wp2 / cum_w - vwap * vwap, np.nan)
    vwap = pd.Series(vwap).fillna(typical[0] if len(typical) else np.nan).to_numpy()
    sd = np.sqrt(np.clip(np.nan_to_num(var, nan=0.0), 0.0, None))
    return pd.DataFrame({"ts": bars["ts"], "vwap": vwap, "vwap_sd": sd})
