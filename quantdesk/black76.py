"""Black-76 prices, greeks and implied volatility for European options on a forward (spec §6.1 step 7, §8).

Nifty and Sensex options are European and cash-settled, so they are priced off the forward F (the futures
price, or the synthetic forward from put-call parity). T is in years. How T is measured, calendar time or
"business time" with the India VIX expiry rule (spec §9 item 4), is decided by the caller in SP2.
Theta is per year of T; divide by the caller's year length for a per-day figure.
"""

import math

SQRT_2PI = math.sqrt(2 * math.pi)


def _cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / SQRT_2PI


def _d1_d2(F: float, K: float, T: float, sigma: float) -> tuple[float, float]:
    vol_t = sigma * math.sqrt(T)
    d1 = (math.log(F / K) + 0.5 * vol_t * vol_t) / vol_t
    return d1, d1 - vol_t


def black76(F: float, K: float, T: float, sigma: float, r: float = 0.0, kind: str = "call") -> float:
    """Discounted Black-76 price. At or after expiry (T <= 0) it is the intrinsic value."""
    discount = math.exp(-r * max(T, 0.0))
    if T <= 0 or sigma <= 0:
        intrinsic = max(F - K, 0.0) if kind == "call" else max(K - F, 0.0)
        return discount * intrinsic
    d1, d2 = _d1_d2(F, K, T, sigma)
    if kind == "call":
        return discount * (F * _cdf(d1) - K * _cdf(d2))
    if kind == "put":
        return discount * (K * _cdf(-d2) - F * _cdf(-d1))
    raise ValueError(f"kind must be 'call' or 'put', not {kind!r}")


def greeks(F: float, K: float, T: float, sigma: float, r: float = 0.0, kind: str = "call") -> dict:
    """Delta and gamma with respect to F, vega per unit of sigma, theta per year of T (negative = decay)."""
    if T <= 0 or sigma <= 0:
        raise ValueError("greeks need T > 0 and sigma > 0")
    discount = math.exp(-r * T)
    d1, d2 = _d1_d2(F, K, T, sigma)
    sqrt_t = math.sqrt(T)
    gamma = discount * _pdf(d1) / (F * sigma * sqrt_t)
    vega = discount * F * _pdf(d1) * sqrt_t
    price = black76(F, K, T, sigma, r, kind)
    if kind == "call":
        delta = discount * _cdf(d1)
    else:
        delta = -discount * _cdf(-d1)
    theta = -discount * F * _pdf(d1) * sigma / (2 * sqrt_t) + r * price
    return {"delta": delta, "gamma": gamma, "vega": vega, "theta": theta}


def implied_vol(price: float, F: float, K: float, T: float, r: float = 0.0, kind: str = "call",
                low: float = 1e-4, high: float = 5.0, tol: float = 1e-10) -> float:
    """Volatility that reproduces `price`, by bisection (robust for deep wings and 0-DTE options)."""
    floor = black76(F, K, T, low, r, kind)
    ceiling = black76(F, K, T, high, r, kind)
    if not floor - 1e-12 <= price <= ceiling + 1e-12:
        raise ValueError(f"price {price} is outside the range [{floor:.4f}, {ceiling:.4f}] for these inputs")
    for _ in range(200):
        mid = 0.5 * (low + high)
        if black76(F, K, T, mid, r, kind) < price:
            low = mid
        else:
            high = mid
        if high - low < tol:
            break
    return 0.5 * (low + high)
