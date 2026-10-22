"""P4: Nifty's daily autocorrelation, AR(1) and MAC(5) (spec §6.3 pilot 4).

MAC(5) is the slope of today's return on the mean of the previous five: a negative value means stretches
revert. The CTX trial runs only if that slope is significantly negative after 2015 (HAC t below -1.96).
"""

from datetime import date

import numpy as np
import pandas as pd

LAGS = 5


def newey_west(x: np.ndarray, y: np.ndarray, lags: int) -> tuple[float, float]:
    """OLS slope of y on x (with an intercept) and its Newey-West standard error."""
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    X = np.column_stack([np.ones(len(x)), x])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    u = y - X @ beta
    xu = X * u[:, None]
    S = xu.T @ xu
    for lag in range(1, lags + 1):
        w = 1.0 - lag / (lags + 1.0)
        G = xu[lag:].T @ xu[:-lag]
        S += w * (G + G.T)
    inv = np.linalg.inv(X.T @ X)
    cov = inv @ S @ inv
    return float(beta[1]), float(np.sqrt(cov[1, 1]))


def _slope_t(r: pd.Series, regressor: pd.Series) -> tuple[float, float]:
    both = pd.concat([r, regressor], axis=1).dropna()
    beta, se = newey_west(both.iloc[:, 1].to_numpy(), both.iloc[:, 0].to_numpy(), LAGS)
    return beta, beta / se


def ar1_mac5(close: pd.Series, after: date) -> dict:
    r = np.log(close.sort_index()).diff()
    lag1 = r.shift(1)
    mean5 = r.shift(1).rolling(LAGS).mean()
    ar1, ar1_t = _slope_t(r, lag1)
    mac5, mac5_t = _slope_t(r, mean5)
    later = r.index >= after
    mac5_after, mac5_after_t = _slope_t(r[later], mean5[later])
    return {"ar1": ar1, "ar1_t": ar1_t, "mac5": mac5, "mac5_t": mac5_t, "mac5_after": mac5_after,
            "mac5_after_t": mac5_after_t, "ctx_runs": bool(mac5_after < 0 and mac5_after_t < -1.96),
            "n_days": int(r.notna().sum())}
