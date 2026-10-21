"""Breadth agreement, the confirmation gate (spec §6.1 step 4.6, R20).

Three signals from `members_minute`: advances minus declines from the open, the share of members above their
own VWAP, and the return of the five heaviest members since the open. At least 2 of the 3 must lean the
trade's way. A missing value never agrees.
"""

import math

import pandas as pd


def breadth_agrees(row: pd.Series, side: str, min_agree: int) -> bool:
    sign = 1.0 if side == "long" else -1.0
    values = (row["adv_share"], row["above_share"] - 0.5, row["top5_ret"])
    votes = sum(1 for v in values if v is not None and not math.isnan(v) and sign * v > 0)
    return votes >= min_agree
