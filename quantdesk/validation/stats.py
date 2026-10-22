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


def pbo(matrix, S: int = 10) -> float | None:
    """Probability of backtest overfitting by CSCV: how often the in-sample best trial ranks in the out-of-sample
    bottom half. `matrix` is periods x trials of returns. None with fewer than two trials."""
    from itertools import combinations

    m = np.asarray(matrix, dtype=float)
    if m.ndim != 2 or m.shape[1] < 2:
        return None
    blocks = np.array_split(np.arange(m.shape[0]), S)
    n = m.shape[1]

    def sharpe(rows):
        x = m[rows]
        sd = x.std(axis=0, ddof=1)
        return np.where(sd > 0, x.mean(axis=0) / np.where(sd > 0, sd, 1), 0.0)

    lambdas = []
    for chosen in combinations(range(S), S // 2):
        is_rows = np.concatenate([blocks[i] for i in chosen])
        oos_rows = np.concatenate([blocks[i] for i in range(S) if i not in chosen])
        best = int(np.argmax(sharpe(is_rows)))
        oos = sharpe(oos_rows)
        rank = 1 + int(np.sum(oos < oos[best]))              # 1 = worst ... n = best
        w = rank / (n + 1.0)
        lambdas.append(math.log(w / (1 - w)))
    return float(np.mean(np.asarray(lambdas) <= 0))


def permutation_p(actual, mirror, buckets, rounds: int, seed: int) -> float:
    """Flip each trade to its mirror (the opposite side, same moment and moneyness) at random within buckets;
    p is the share of rounds whose mean R is at least the actual mean."""
    actual, mirror, buckets = np.asarray(actual, float), np.asarray(mirror, float), np.asarray(buckets)
    rng = np.random.default_rng(seed)
    target = actual.mean()
    hits = 0
    groups = [np.flatnonzero(buckets == b) for b in np.unique(buckets)]
    for _ in range(rounds):
        flip = np.zeros(len(actual), dtype=bool)
        for idx in groups:
            chosen = rng.permutation(idx)[: len(idx) // 2 + (rng.random() < 0.5 if len(idx) % 2 else 0)]
            flip[chosen] = True
        hits += np.where(flip, mirror, actual).mean() >= target
    return (1 + hits) / (rounds + 1)


def post_publication_ratio(before_mean: float, after_mean: float) -> float:
    return float(after_mean / before_mean) if before_mean > 0 else float("nan")


def addon_gate(new: "pd.DataFrame", old: "pd.DataFrame", days, years) -> dict:
    """A regime add-on against its predecessor on identical setups (spec §6.3)."""
    import pandas as pd

    n_days = max(len(days), 1)
    per_day_new, per_day_old = new["r"].sum() / n_days, old["r"].sum() / n_days
    paired = new.merge(old, on="signal_id", suffixes=("_new", "_old"))
    diff = (paired["r_new"] - paired["r_old"]).to_numpy()
    paired_t = t_stat(diff) if len(diff) > 1 else float("nan")
    year_of = paired["day_new"].map(lambda d: d.year)
    by_year = paired.assign(year=year_of).groupby("year")[["r_new", "r_old"]].mean()
    better_years = int(sum(1 for y in years if y in by_year.index and by_year.loc[y, "r_new"] > by_year.loc[y, "r_old"]))
    passed = bool(per_day_new >= per_day_old and paired_t >= 1.0 and better_years >= 4)
    return {"per_day_new": float(per_day_new), "per_day_old": float(per_day_old), "paired_t": float(paired_t),
            "better_years": better_years, "passed": passed}
