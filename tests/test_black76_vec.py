import numpy as np
import pytest

from quantdesk.black76 import black76, greeks
from quantdesk.pricing.black76_vec import delta, price, theta_bt


def test_vector_prices_match_the_scalar_model():
    F, K = np.array([100.0, 100.0, 22800.0]), np.array([100.0, 110.0, 22900.0])
    T, s = np.array([0.5, 0.2, 0.004]), np.array([0.2, 0.3, 0.14])
    for kind in ("call", "put"):
        got = price(F, K, T, s, kind)
        want = [black76(f, k, t, v, kind=kind) for f, k, t, v in zip(F, K, T, s)]
        assert np.allclose(got, want, atol=1e-10)
        got_d = delta(F, K, T, s, kind)
        want_d = [greeks(f, k, t, v, kind=kind)["delta"] for f, k, t, v in zip(F, K, T, s)]
        assert np.allclose(got_d, want_d, atol=1e-10)


def test_theta_bt_is_the_time_derivative():
    h = 1e-6
    num = (price(100.0, 100.0, 0.2 + h, 0.2, "call") - price(100.0, 100.0, 0.2 - h, 0.2, "call")) / (2 * h)
    assert theta_bt(100.0, 100.0, 0.2, 0.2, "call") == pytest.approx(num, rel=1e-6)


def test_theta_bt_is_positive_for_both_kinds():
    """The caller applies decay as -theta_bt * dBT, so the sign convention here is d(price)/dT."""
    assert theta_bt(22800.0, 22900.0, 0.02, 0.14, "call") > 0
    put = theta_bt(22800.0, 22700.0, 0.02, 0.14, "put")
    call = theta_bt(22800.0, 22700.0, 0.02, 0.14, "call")
    assert put == pytest.approx(call, rel=1e-12)  # put-call parity with r = 0: the time value decays alike


def test_rows_with_no_time_value_use_intrinsic():
    F = np.array([23000.0, 23000.0, 22700.0])
    K = np.array([22800.0, 22800.0, 22800.0])
    T, s = np.array([0.0, 0.5, 0.0]), np.array([0.2, 0.0, 0.2])  # expired, and a zero vol
    assert np.allclose(price(F, K, T, s, "call"), [200.0, 200.0, 0.0])
    assert np.allclose(price(F, K, T, s, "put"), [0.0, 0.0, 100.0])
    assert np.allclose(delta(F, K, T, s, "call"), [1.0, 1.0, 0.0])  # the limit as sigma*sqrt(T) -> 0
    assert np.allclose(delta(F, K, T, s, "put"), [0.0, 0.0, -1.0])  # only the in-the-money put is exercised
    assert np.allclose(theta_bt(F, K, T, s, "call"), [0.0, 0.0, 0.0])  # nothing left to decay


def test_kind_can_be_an_array_and_scalars_broadcast():
    """One minute of a chain: calls and puts side by side, one VIX value for all of them."""
    kinds = np.array(["call", "put", "call"])
    got = price(22800.0, np.array([22700.0, 22700.0, 22900.0]), 0.01, 0.14, kinds)
    want = [black76(22800.0, k, 0.01, 0.14, kind=kind)
            for k, kind in zip([22700.0, 22700.0, 22900.0], kinds)]
    assert np.allclose(got, want, atol=1e-10)


def test_an_unknown_kind_is_refused():
    with pytest.raises(ValueError, match="chooser"):
        price(100.0, 100.0, 0.2, 0.2, "chooser")
    with pytest.raises(ValueError, match="chooser"):
        theta_bt(100.0, 100.0, 0.2, 0.2, np.array(["call", "chooser"]))
