"""Validation statistics (spec §6.3, design §14). The deflated Sharpe ratio comes first: pilot P10 needs it.

DSR (Bailey and Lopez de Prado): the probability that the true Sharpe exceeds the best one would expect from N
unskilled trials, corrected for skew and kurtosis. N counts the 46 earlier looks as well as the trials (R33).
"""

import math

import numpy as np
from scipy.stats import norm

EULER = 0.5772156649015329


def expected_max_sr(n_trials: int, var_sr: float) -> float:
    n = max(int(n_trials), 2)
    return math.sqrt(var_sr) * ((1 - EULER) * norm.ppf(1 - 1 / n) + EULER * norm.ppf(1 - 1 / (n * math.e)))


def deflated_sharpe(sr: float, T: int, skew: float, kurt: float, n_trials: int, var_sr: float) -> float:
    """`kurt` is plain kurtosis (3 for a normal), not excess."""
    sr0 = expected_max_sr(n_trials, var_sr)
    denom = 1 - skew * sr + (kurt - 1) / 4.0 * sr * sr
    if T < 2 or denom <= 0:
        return float("nan")
    return float(norm.cdf((sr - sr0) * math.sqrt(T - 1) / math.sqrt(denom)))


def sharpe_stats(x) -> tuple[float, float, float]:
    """(per-period Sharpe, skew, plain kurtosis) of a return series."""
    x = np.asarray(x, dtype=float)
    if len(x) < 3 or x.std(ddof=1) == 0:
        return float("nan"), 0.0, 3.0
    z = (x - x.mean()) / x.std(ddof=0)
    return float(x.mean() / x.std(ddof=1)), float(np.mean(z ** 3)), float(np.mean(z ** 4))


def t_stat(x) -> float:
    x = np.asarray(x, dtype=float)
    if len(x) < 2 or x.std(ddof=1) == 0:
        return float("nan")
    return float(x.mean() / x.std(ddof=1) * math.sqrt(len(x)))
