"""Causal z-scores (R10): a feature is scaled by its own history at the same check time in earlier sessions.

Never by a fold's training set. The live engine can compute exactly the same number on the day, and a CV
fold cannot see its test period through the scaling.
"""

import math

import pandas as pd

from quantdesk.strategy.types import ZRef


def causal_z(value: float, ref: ZRef | None, min_n: int, winsor: float) -> float | None:
    if ref is None or ref.n < min_n or not ref.sd > 0 or value is None or math.isnan(value):
        return None
    return max(-winsor, min(winsor, (value - ref.mean) / ref.sd))


def z_refs_for(history: pd.DataFrame, window: int) -> dict[tuple[str, str], ZRef]:
    """`history` holds rows (day, check, feature, value) from sessions before the day being scored."""
    refs = {}
    for (feature, check), rows in history.groupby(["feature", "check"], sort=False):
        values = rows.sort_values("day")["value"].dropna().iloc[-window:]
        if len(values):
            refs[(feature, check)] = ZRef(float(values.mean()), float(values.std(ddof=1)) if len(values) > 1 else 0.0,
                                          int(len(values)))
    return refs
