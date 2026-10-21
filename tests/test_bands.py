from datetime import date, datetime, time

import numpy as np
import pandas as pd
import pytest

from quantdesk.analysis.bands import band_edges, band_sigma, slot
from quantdesk.clock import IST
from quantdesk.strategy.trigger import h1
from quantdesk.strategy.types import DayContext
from quantdesk.validation.hypotheses import load_hypotheses

H = load_hypotheses()


def make_ctx(band_sigma, open_=100.0, prev_close=100.0, **kw):
    base = dict(index="NIFTY", day=date(2024, 3, 4), session_kind="regular", open=open_, prev_close=prev_close,
                prev_day=(101.0, 99.0, prev_close), prev_week=(102.0, 98.0, prev_close), is_expiry_day=False,
                expiry_1=date(2024, 3, 7), expiry_2=date(2024, 3, 14), lot_1=50, lot_2=50, dte_1=3,
                sigma_day=0.008, sigma_gap=0.003, har_pct=0.5, vix_prev_close=14.0, band_sigma=band_sigma,
                events=(), delta_parts={}, options_raw=None, macro_raw=0.0, vol_rich_threshold=None,
                z_refs={}, hard_exit=time(15, 10))
    base.update(kw)
    return DayContext(**base)


def make_frame(close_at_0944, vwap_at_0944):
    ts = [datetime(2024, 3, 4, 9, 43, tzinfo=IST), datetime(2024, 3, 4, 9, 44, tzinfo=IST)]
    return pd.DataFrame({"ts": ts, "close": [100.0, close_at_0944], "vwap": [100.0, vwap_at_0944]})


def test_slots_count_minutes_from_the_open():
    assert slot(datetime(2024, 3, 4, 9, 15, tzinfo=IST)) == 0 and slot(datetime(2024, 3, 4, 15, 29, tzinfo=IST)) == 374


def test_band_hand_example():
    # 14 sessions; at slot 30 each closed 0.2% above its open
    hist = [pd.DataFrame({"ts": [datetime(2024, 1, d, 9, 45, tzinfo=IST)], "close": [100.2]}) for d in range(1, 15)]
    sigma = band_sigma(hist, [100.0] * 14, lookback=14)
    assert sigma[30] == pytest.approx(0.002) and np.isnan(sigma[31])
    upper, lower = band_edges(open_=101.0, prev_close=100.0, sigma=0.002, v=1.0)  # gap up
    assert (upper, lower) == pytest.approx((101.0 * 1.002, 100.0 * 0.998))


def test_thirteen_sessions_give_no_band_and_no_signal():
    hist = [pd.DataFrame({"ts": [datetime(2024, 1, d, 9, 45, tzinfo=IST)], "close": [100.2]}) for d in range(1, 14)]
    sigma = band_sigma(hist, [100.0] * 13, lookback=14)
    assert np.isnan(sigma[30])
    ctx = make_ctx(sigma)
    assert h1(make_frame(101.0, 100.1), datetime(2024, 3, 4, 9, 45, tzinfo=IST), ctx, H) is None


def test_band_uses_only_the_last_lookback_sessions():
    hist = [pd.DataFrame({"ts": [datetime(2024, 1, d, 9, 45, tzinfo=IST)], "close": [100.0 + (1.0 if d == 1 else 0.2)]})
            for d in range(1, 16)]                       # 15 sessions; the oldest one is wild and drops out
    assert band_sigma(hist, [100.0] * 15, lookback=14)[30] == pytest.approx(0.002)


def test_h1_long_needs_close_above_band_and_vwap():
    ctx = make_ctx(np.full(375, 0.002))
    sig = h1(make_frame(100.5, 100.1), datetime(2024, 3, 4, 9, 45, tzinfo=IST), ctx, H)
    assert sig.side == "long" and sig.stop_level == pytest.approx(100.2) and sig.b == pytest.approx(0.3)
    assert sig.target_level == pytest.approx(100.5 + 2.3 * 0.3)


def test_h1_needs_the_vwap_side_too():
    ctx = make_ctx(np.full(375, 0.002))
    assert h1(make_frame(100.5, 100.6), datetime(2024, 3, 4, 9, 45, tzinfo=IST), ctx, H) is None


def test_h1_short_uses_the_lower_band_and_vwap():
    ctx = make_ctx(np.full(375, 0.002))
    sig = h1(make_frame(99.5, 99.7), datetime(2024, 3, 4, 9, 45, tzinfo=IST), ctx, H)
    assert sig.side == "short" and sig.stop_level == pytest.approx(99.7) and sig.b == pytest.approx(0.2)
    assert sig.target_level == pytest.approx(99.5 - 2.3 * 0.2)
