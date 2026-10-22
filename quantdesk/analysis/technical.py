"""The technical family score (spec §5A.1, design §9): location and confirmation, sign-aligned to the trade.

Location is how far the close sits from VWAP and how much room there is to the nearest opposing level, both
in stop-distances. Confirmation is the three breadth signals. Each raw feature is scaled by its causal z
(R10). The score is the mean of the two halves, clipped at ±3. If any z is undefined, so is the score: a
missing input is not a neutral one.
"""

import math

import pandas as pd

from quantdesk.analysis.levels import NEAR_MULTIPLE
from quantdesk.analysis.zscore import causal_z
from quantdesk.strategy.types import Signal
from quantdesk.validation.hypotheses import param

LOCATION = ("loc_vwap", "loc_level")
CONFIRMATION = ("adv_share", "above_share", "top5_ret")


def technical_raw(row: pd.Series, signal: Signal, nearest_dist: float) -> dict[str, float]:
    sign = 1.0 if signal.side == "long" else -1.0
    level = NEAR_MULTIPLE if math.isinf(nearest_dist) else min(nearest_dist / signal.b, NEAR_MULTIPLE)
    return {"loc_vwap": sign * (float(row["close"]) - float(row["vwap"])) / signal.b,
            "loc_level": level,
            "adv_share": sign * float(row["adv_share"]),
            "above_share": sign * (float(row["above_share"]) - 0.5),
            "top5_ret": sign * float(row["top5_ret"])}


def technical_score(raw: dict, z_refs: dict, check: str, h: dict) -> float | None:
    min_n, winsor = param(h, "meta.zscore_min_sessions"), param(h, "meta.winsor")
    # breadth is referenced at its own check time; signal-only features against earlier signals pooled (R40)
    z = {name: causal_z(raw[name], z_refs.get((name, check)) or z_refs.get((name, "*")), min_n, winsor)
         for name in LOCATION + CONFIRMATION}
    if any(v is None for v in z.values()):
        return None
    location = sum(z[n] for n in LOCATION) / len(LOCATION)
    confirmation = sum(z[n] for n in CONFIRMATION) / len(CONFIRMATION)
    return max(-winsor, min(winsor, (location + confirmation) / 2.0))
