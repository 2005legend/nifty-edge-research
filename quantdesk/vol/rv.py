"""Realised variance from the official daily bar (design §6, R13).

Garman-Klass uses the whole session range instead of close to close, which for an index is several times
more efficient per session, so a 750-session fit window carries far less estimator noise. It is an
open-to-close variance: the overnight gap is a separate HAR term, never part of RV.
"""

import numpy as np

CLOSE_WEIGHT = 2.0 * np.log(2.0) - 1.0


def garman_klass(o, h, l, c) -> np.ndarray:
    """Session variance in fraction squared: 0.5 * ln(H/L)^2 - (2*ln2 - 1) * ln(C/O)^2."""
    o, h, l, c = (np.asarray(value, dtype=float) for value in (o, h, l, c))
    return 0.5 * np.log(h / l) ** 2 - CLOSE_WEIGHT * np.log(c / o) ** 2
