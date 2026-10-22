from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from quantdesk.clock import IST
from quantdesk.validation.pilots.p4_autocorr import ar1_mac5, newey_west
from quantdesk.validation.pilots.p9_vwap import futures_vwap, vwap_agreement
from quantdesk.validation.pilots.report import write_report


def day_frames(offset_vwap=0.0, basis=20.0, flip=False):
    ts = [datetime(2026, 10, 5, 9, 15, tzinfo=IST) + timedelta(minutes=i) for i in range(100)]
    close = 22000 + 10 * np.sin(np.arange(100) / 10)
    index = pd.DataFrame({"ts": ts, "day": date(2026, 10, 5), "close": close, "vwap": 22000.0})
    fut_close = close + basis if not flip else 2 * 22000 - close + basis
    fut = pd.DataFrame({"ts": ts, "day": date(2026, 10, 5), "high": fut_close, "low": fut_close, "close": fut_close,
                        "volume": 100})
    return index, fut


def test_futures_vwap_is_cumulative_per_day():
    _, fut = day_frames()
    v = futures_vwap(fut)
    assert v.iloc[0] == pytest.approx(fut.close.iloc[0]) and v.iloc[-1] == pytest.approx(fut.close.mean())


def test_identical_vwaps_agree_fully():
    index, fut = day_frames()
    index["vwap"] = futures_vwap(fut).to_numpy() - 20.0             # the proxy equals futures VWAP less the basis
    out = vwap_agreement(index, fut, b_median=10.0)
    assert out["side_disagree_share"] == 0.0 and out["median_gap_over_b"] == pytest.approx(0.0, abs=1e-9)
    assert out["passed"]


def test_opposite_sides_count_as_disagreement():
    index, fut = day_frames(flip=True)
    index["vwap"] = 22000.0
    out = vwap_agreement(index, fut, b_median=10.0)
    assert out["side_disagree_share"] > 0.5 and not out["passed"]


def test_newey_west_matches_ols_slope():
    rng = np.random.default_rng(0)
    x = rng.normal(size=500)
    y = 0.3 * x + rng.normal(size=500)
    beta, se = newey_west(x, y, lags=5)
    assert beta == pytest.approx(np.polyfit(x, y, 1)[0]) and 0.02 < se < 0.08


def test_ar1_of_an_ar_process():
    rng = np.random.default_rng(1)
    r = np.zeros(3000)
    for t in range(1, 3000):
        r[t] = -0.1 * r[t - 1] + rng.normal(0, 0.01)
    close = pd.Series(22000 * np.exp(np.cumsum(r)), index=pd.bdate_range("2014-01-01", periods=3000).date)
    out = ar1_mac5(close, after=date(2016, 1, 1))
    assert out["ar1"] == pytest.approx(-0.1, abs=0.04) and out["ar1_t"] < -2
    assert set(out) >= {"mac5", "mac5_t", "mac5_after", "mac5_after_t", "ctx_runs"}


def test_report_is_markdown_with_the_data_hash(tmp_path):
    path = write_report("P4", {"ar1": -0.05, "ctx_runs": False}, tmp_path / "P4.md", data_hash="abc123")
    text = path.read_text()
    assert text.startswith("# P4") and "abc123" in text and "| ar1 | -0.05 |" in text
