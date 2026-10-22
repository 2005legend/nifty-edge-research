"""P9: is the stock-volume VWAP proxy close to the real front-month futures VWAP? (spec §6.0)

Front-month futures days only, skipping each contract's last 2 sessions, when trading moves to the next month.
- **Side:** whether the index is above its proxy, against whether the future is above its own VWAP.
- **Gap:** |proxy - (futures VWAP - basis)|, with basis = futures close - index close at the same minute,
  scaled by the median structural stop b.

Pass: sides disagree in at most 5% of minutes, and the median gap is at most 0.1 b. If not, every VWAP rule
switches to the open-anchored average price, before any profit is seen.
"""

import numpy as np
import pandas as pd

MAX_DISAGREE = 0.05
MAX_GAP_B = 0.1


def futures_vwap(fut: pd.DataFrame) -> pd.Series:
    bars = fut.sort_values("ts")
    tp = (bars["high"] + bars["low"] + bars["close"]) / 3.0
    pv = (tp * bars["volume"]).groupby(bars["day"]).cumsum()
    v = bars["volume"].groupby(bars["day"]).cumsum()
    return (pv / v.replace(0, np.nan)).fillna(tp).set_axis(bars["ts"].to_numpy())


def vwap_agreement(index_frame: pd.DataFrame, fut_bars: pd.DataFrame, b_median: float) -> dict:
    fut = fut_bars.sort_values("ts").set_index("ts")
    fut = fut.assign(fvwap=futures_vwap(fut_bars).to_numpy())
    joined = index_frame.set_index("ts")[["close", "vwap"]].join(fut[["close", "fvwap"]], rsuffix="_fut", how="inner")
    joined = joined.dropna()
    side_index = np.sign(joined["close"] - joined["vwap"])
    side_fut = np.sign(joined["close_fut"] - joined["fvwap"])
    decided = (side_index != 0) & (side_fut != 0)
    disagree = float((side_index[decided] != side_fut[decided]).mean()) if decided.any() else float("nan")
    basis = joined["close_fut"] - joined["close"]
    gap = (joined["vwap"] - (joined["fvwap"] - basis)).abs()
    median_gap_b = float(gap.median() / b_median) if len(gap) else float("nan")
    return {"minutes": int(len(joined)), "side_disagree_share": disagree, "median_gap_points": float(gap.median()),
            "median_b_points": float(b_median), "median_gap_over_b": median_gap_b,
            "passed": bool(disagree <= MAX_DISAGREE and median_gap_b <= MAX_GAP_B)}
