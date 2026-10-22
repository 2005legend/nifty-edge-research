from datetime import date, datetime

import numpy as np
import pandas as pd
import pytest

from quantdesk.analysis.options_implied import options_raw, pcr_oi, rr25
from quantdesk.black76 import black76
from quantdesk.clock import IST
from quantdesk.pricing.clock import Clock

EXP = date(2024, 3, 7)


def synthetic_chain(F, sigma, T, skew=0.0):
    rows = []
    for K in np.arange(F * 0.95, F * 1.05, F * 0.005):
        vol = sigma * (1 + skew * np.log(K / F))
        for kind, side in (("call", "CE"), ("put", "PE")):
            rows.append({"expiry": EXP, "strike": float(K), "option_type": side, "instrument": "IDO", "oi": 100,
                         "close": black76(F, K, T, vol, kind=kind), "traded": True})
    return pd.DataFrame(rows)


def test_pcr_counts_strikes_within_ten_steps():
    eod = pd.DataFrame({"expiry": EXP, "strike": [22000.0, 22050.0, 23000.0] * 2, "instrument": "IDO",
                        "option_type": ["CE"] * 3 + ["PE"] * 3, "oi": [100, 100, 999, 300, 100, 999], "traded": True})
    assert pcr_oi(eod, EXP, center=22025.0, step=50, n_steps=10) == pytest.approx(400 / 200)


def test_rr25_is_zero_without_skew():
    eod = synthetic_chain(F=100.0, sigma=0.2, T=0.02)
    assert rr25(eod, EXP, F=100.0, T_bt=0.02, rr_delta=0.25) == pytest.approx(0.0, abs=1e-4)


def test_rr25_is_negative_with_a_put_skew():
    eod = synthetic_chain(F=100.0, sigma=0.2, T=0.02, skew=-2.0)     # vol rises as strikes fall
    assert rr25(eod, EXP, F=100.0, T_bt=0.02, rr_delta=0.25) < -0.002


def test_untraded_rows_do_not_enter_rr25():
    eod = synthetic_chain(F=100.0, sigma=0.2, T=0.02)
    eod["traded"] = False
    assert rr25(eod, EXP, F=100.0, T_bt=0.02, rr_delta=0.25) is None


def test_options_raw_uses_the_nearest_expiry_with_a_session_left():
    days = (date(2024, 3, 4), date(2024, 3, 5), date(2024, 3, 6), date(2024, 3, 7), date(2024, 3, 8))
    clock = Clock(np.full(375, 1 / 375), 0.5, 0.1, 0.2, days)
    eod = synthetic_chain(F=22000.0, sigma=0.01, T=3.0)
    out = options_raw(eod, {"prev_close": 22000.0, "step": 50, "at": datetime(2024, 3, 4, 15, 30, tzinfo=IST),
                            "expiries": [EXP]}, clock, {"strike_steps": 10, "rr_delta": 0.25})
    assert out["pcr"] == pytest.approx(1.0) and out["rr25"] == pytest.approx(0.0, abs=1e-4)
