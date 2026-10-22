"""The shock hurdle (RV-2; spec §6.1 step 1, design §9): +0.04 on the probability needed, for 5 sessions.

A session is a shock day when, by its open, any of these holds:
- India VIX rose 20% in log terms over the last 5 closes
- the opening gap is at least 1.5 pre-gap HAR sigmas
- a variance CUSUM raised an alarm in the previous 20 sessions

The CUSUM's threshold h is calibrated once, on 2019-2022, by a moving-block bootstrap. The target is one false
alarm per 250 sessions on fat-tailed returns, which a Gaussian h would badly overshoot. h is frozen in
config/frozen/shock_v1.yaml.
"""

import math
from datetime import date

import numpy as np
import pandas as pd

RATIO = 1.5            # sigma1 = 1.5 x sigma0, the shift the CUSUM looks for
ALARM_LOOKBACK = 20


def _increments(r: np.ndarray, sigma_window: int) -> np.ndarray:
    """Log-likelihood-ratio steps; NaN until sigma0 has a full window behind it."""
    s = pd.Series(r)
    sigma0 = s.rolling(sigma_window).std(ddof=1).shift(1).to_numpy()
    sigma1 = RATIO * sigma0
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.log(sigma0 / sigma1) + r * r / 2.0 * (1.0 / sigma0 ** 2 - 1.0 / sigma1 ** 2)


def _run(steps: np.ndarray, h: float) -> np.ndarray:
    """CUSUM over the last axis of `steps` (one row per series): alarm when S > h, then restart at 0."""
    steps = np.atleast_2d(steps)
    total = np.zeros(steps.shape[0])
    alarms = np.zeros(steps.shape, dtype=bool)
    for t in range(steps.shape[1]):
        step = steps[:, t]
        total = np.where(np.isnan(step), 0.0, np.maximum(0.0, total + np.nan_to_num(step)))
        hit = total > h
        alarms[:, t] = hit
        total[hit] = 0.0
    return alarms


def cusum_alarms(returns: pd.Series, sigma_window: int, h: float) -> pd.Series:
    steps = _increments(returns.to_numpy(dtype=float), sigma_window)
    return pd.Series(_run(steps, h)[0], index=returns.index)


def calibrate_cusum_h(returns: pd.Series, sigma_window: int, block: int, resamples: int, target_rate: float,
                      seed: int) -> float:
    """h such that bootstrap series raise `target_rate` alarms per session (bisection on h)."""
    r = returns.dropna().to_numpy(dtype=float)
    rng = np.random.default_rng(seed)
    n = len(r)
    starts = rng.integers(0, n - block + 1, size=(resamples, math.ceil(n / block)))
    series = np.stack([np.concatenate([r[s:s + block] for s in row])[:n] for row in starts])
    steps = np.stack([_increments(x, sigma_window) for x in series])

    def rate(h: float) -> float:
        return float(_run(steps, h)[:, sigma_window:].mean())

    lo, hi = 0.01, 50.0
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if rate(mid) > target_rate:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def shock_days(daily: pd.DataFrame, vix_close: pd.Series, sigma_gap: pd.Series, alarms: pd.Series,
               vix_log5: float, gap_sigma: float) -> pd.Series:
    frame = daily.set_index("day").sort_index()
    days = frame.index
    vix = vix_close.reindex(days)
    jump = np.log(vix.shift(1) / vix.shift(6)) >= vix_log5
    gap = np.log(frame["open"] / frame["close"].shift(1)).abs() >= gap_sigma * sigma_gap.reindex(days)
    recent = alarms.reindex(days).fillna(False).astype(int).shift(1).rolling(ALARM_LOOKBACK, min_periods=1).max() > 0
    return (jump.fillna(False) | gap.fillna(False) | recent.fillna(False)).astype(bool)


def shock_delta(shock: pd.Series, day: date, sessions: int, delta: float) -> float:
    days = list(shock.index)
    if day not in days:
        return 0.0
    i = days.index(day)
    return delta if bool(shock.iloc[max(0, i - sessions + 1):i + 1].any()) else 0.0
