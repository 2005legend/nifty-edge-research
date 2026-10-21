"""Vectorised Black-76 (design §8): the scalar model in quantdesk/black76.py, over whole frames of strikes.

The backtest prices thousands of candidate strikes per minute, so the scalar loop is too slow there; the two
must agree to 1e-10, or a backtest would not reproduce what the desk would have paid. r = 0 throughout, so
F is the index level and the call and the put carry the same time value (put-call parity).

`theta_bt` is d(price)/dT, positive, per unit of T. Once the clock is fitted, T is business time and the
caller applies decay over a step as -theta_bt * dBT, which is why the sign is the opposite of the usual
calendar theta.

Rows with no time value (T <= 0 or sigma <= 0) get intrinsic value, the intrinsic delta, and zero theta,
so a frame that spans an expiry needs no masking by the caller.
"""

import numpy as np
from scipy.special import ndtr

SQRT_2PI = np.sqrt(2.0 * np.pi)


def _inputs(F, K, T, sigma):
    """Broadcast the four inputs and split off the rows that have no time value, using safe stand-ins."""
    F, K, T, sigma = (np.asarray(value, dtype=float) for value in (F, K, T, sigma))
    live = (T > 0) & (sigma > 0)
    return F, K, live, np.where(live, T, 1.0), np.where(live, sigma, 1.0)


def _sign(kind) -> np.ndarray:
    """+1 on call rows, -1 on put rows, so one formula serves both kinds."""
    kinds = np.asarray(kind).astype(str)
    unknown = sorted(set(kinds.ravel().tolist()) - {"call", "put"})
    if unknown:
        raise ValueError(f"kind must be 'call' or 'put', not {', '.join(repr(k) for k in unknown)}")
    return np.where(kinds == "call", 1.0, -1.0)


def _d1(F, K, vol_t) -> np.ndarray:
    return (np.log(F / K) + 0.5 * vol_t * vol_t) / vol_t


def price(F, K, T, sigma, kind) -> np.ndarray:
    F, K, live, T, sigma = _inputs(F, K, T, sigma)
    s = _sign(kind)
    vol_t = sigma * np.sqrt(T)
    d1 = _d1(F, K, vol_t)
    time_value = s * (F * ndtr(s * d1) - K * ndtr(s * (d1 - vol_t)))
    return np.where(live, time_value, np.maximum(s * (F - K), 0.0))


def delta(F, K, T, sigma, kind) -> np.ndarray:
    """d(price)/dF: N(d1) on a call, N(d1) - 1 on a put; on a row with no time value, the exercise decision."""
    F, K, live, T, sigma = _inputs(F, K, T, sigma)
    s = _sign(kind)
    d1 = _d1(F, K, sigma * np.sqrt(T))
    return np.where(live, s * ndtr(s * d1), np.where(s * (F - K) > 0, s, 0.0))


def theta_bt(F, K, T, sigma, kind) -> np.ndarray:
    """d(price)/dT = F * phi(d1) * sigma / (2 * sqrt(T)), the same for both kinds."""
    F, K, live, T, sigma = _inputs(F, K, T, sigma)
    _sign(kind)  # validated, so a bad kind fails here as loudly as it does in price
    d1 = _d1(F, K, sigma * np.sqrt(T))
    return np.where(live, F * np.exp(-0.5 * d1 * d1) / SQRT_2PI * sigma / (2.0 * np.sqrt(T)), 0.0)
