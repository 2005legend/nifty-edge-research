import math

import pytest

from quantdesk.black76 import black76, greeks, implied_vol


def test_hull_atm_futures_option_example():
    """Hull, Options, Futures and Other Derivatives: F = K = 20, r = 9%, T = 4 months, sigma = 25% -> 1.12."""
    put = black76(20, 20, 4 / 12, 0.25, r=0.09, kind="put")
    call = black76(20, 20, 4 / 12, 0.25, r=0.09, kind="call")
    assert put == pytest.approx(1.12, abs=0.005)
    assert call == pytest.approx(put, abs=1e-12)  # at the money forward, call = put


@pytest.mark.parametrize("F, K", [(22888.95, 22800), (22888.95, 23100), (73400, 73000)])
def test_put_call_parity(F, K):
    T, sigma, r = 3 / 365, 0.13, 0.065
    call, put = black76(F, K, T, sigma, r, "call"), black76(F, K, T, sigma, r, "put")
    assert call - put == pytest.approx(math.exp(-r * T) * (F - K), abs=1e-6)


def test_implied_vol_round_trip():
    price = black76(22888.95, 23000, 2 / 365, 0.142, 0.065, "call")
    assert implied_vol(price, 22888.95, 23000, 2 / 365, 0.065, "call") == pytest.approx(0.142, abs=1e-6)


def test_implied_vol_below_intrinsic_is_rejected():
    with pytest.raises(ValueError):
        implied_vol(50.0, 23000, 22800, 2 / 365, 0.065, "call")  # intrinsic is about 200


def test_expiry_gives_discounted_intrinsic():
    assert black76(23000, 22800, 0.0, 0.2, kind="call") == pytest.approx(200.0)
    assert black76(23000, 22800, 0.0, 0.2, kind="put") == 0.0


def test_greeks_match_finite_differences():
    F, K, T, s, r = 22888.95, 23000, 3 / 365, 0.13, 0.065
    g = greeks(F, K, T, s, r, "call")
    h = 0.01
    assert g["delta"] == pytest.approx((black76(F + h, K, T, s, r) - black76(F - h, K, T, s, r)) / (2 * h), rel=1e-4)
    assert g["gamma"] == pytest.approx(
        (black76(F + 1, K, T, s, r) - 2 * black76(F, K, T, s, r) + black76(F - 1, K, T, s, r)), rel=1e-3)
    assert g["vega"] == pytest.approx((black76(F, K, T, s + 1e-4, r) - black76(F, K, T, s - 1e-4, r)) / 2e-4, rel=1e-4)
    dt = 1e-6
    assert g["theta"] == pytest.approx(-(black76(F, K, T + dt, s, r) - black76(F, K, T - dt, s, r)) / (2 * dt), rel=1e-3)
    put = greeks(F, K, T, s, r, "put")
    assert g["delta"] - put["delta"] == pytest.approx(math.exp(-r * T), rel=1e-9)
