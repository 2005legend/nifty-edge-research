"""P2: how far eligible setups run for and against, in stop-distances, 2019-2022 only (spec §6.3 pilot 2).

The index path only, never an option P&L. It decides D1's reversal clause: if setups peak within about 30
minutes and then give it back, a fixed target near 2b would beat the trail.
"""

from datetime import datetime

import numpy as np
import pandas as pd

from quantdesk.strategy.types import Signal


def excursions(frame: pd.DataFrame, signal: Signal, hard_exit_at: datetime) -> dict:
    path = frame[(frame["ts"] >= signal.at) & (frame["ts"] <= hard_exit_at)].sort_values("ts")
    sign = 1.0 if signal.side == "long" else -1.0
    fav = sign * (path["close"].to_numpy(dtype=float) - signal.ref_close) / signal.b
    if not len(fav):
        return {"mfe_b": np.nan, "mae_b": np.nan, "minutes_to_mfe": np.nan, "retrace_after_mfe_b": np.nan}
    peak = int(np.argmax(fav))
    return {"mfe_b": float(fav.max()), "mae_b": float(max(0.0, -fav.min())),
            "minutes_to_mfe": int((path["ts"].iloc[peak] - signal.at).total_seconds() // 60),
            "retrace_after_mfe_b": float(fav[peak] - fav[peak:].min())}
