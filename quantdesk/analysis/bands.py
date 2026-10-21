"""The noise band of the H1 trigger (spec §6.1 step 3, design §9; Zarattini's intraday momentum band).

sigma(tau) is the average absolute move from the open at minute tau over the previous 14 sessions of the same
type: expiry sessions for an expiry day, non-expiry sessions otherwise. The band is centred on the open, and
stretched to the previous close after a gap. A slot with fewer than 14 sessions behind it has no band, and so
no signal (R12): an undefined band is never read as a band of zero.
"""

from datetime import datetime

import numpy as np
import pandas as pd

from quantdesk.clock import IST

MINUTES = 375


def slot(ts: datetime) -> int:
    local = ts.astimezone(IST)
    return (local.hour * 60 + local.minute) - (9 * 60 + 15)


def band_sigma(history: list[pd.DataFrame], opens: list[float], lookback: int) -> np.ndarray:
    """Mean |close/open - 1| per slot over the last `lookback` sessions; NaN where fewer sessions have that slot."""
    moves = np.full((len(history), MINUTES), np.nan)
    for i, (frame, open_) in enumerate(zip(history, opens)):
        slots = np.array([slot(ts) for ts in frame["ts"]], dtype=int)
        keep = (slots >= 0) & (slots < MINUTES)
        moves[i, slots[keep]] = np.abs(frame["close"].to_numpy(dtype=float)[keep] / open_ - 1.0)
    recent = moves[-lookback:]
    counts = np.sum(~np.isnan(recent), axis=0)
    sums = np.nansum(recent, axis=0)
    return np.where(counts >= lookback, sums / np.maximum(counts, 1), np.nan)


def band_edges(open_: float, prev_close: float, sigma: float, v: float) -> tuple[float, float]:
    return max(open_, prev_close) * (1.0 + v * sigma), min(open_, prev_close) * (1.0 - v * sigma)
