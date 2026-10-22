from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from quantdesk.analysis.frame import FEATURES, build_minute_frame
from quantdesk.clock import IST
from quantdesk.validation.hypotheses import load_hypotheses
from tests.test_bands import make_ctx

H = load_hypotheses()


def synthetic_day(seed):
    rng = np.random.default_rng(seed)
    ts = [datetime(2024, 3, 4, 9, 15, tzinfo=IST) + timedelta(minutes=i) for i in range(375)]
    close = 22000.0 * np.exp(np.cumsum(rng.normal(0, 0.0004, 375)))
    index_bars = pd.DataFrame({"ts": ts, "open": close, "high": close * 1.0002, "low": close * 0.9998, "close": close})
    keep = rng.random(375) > 0.05                                   # a few minutes with no member bars
    members = pd.DataFrame({"ts": np.array(ts)[keep], "members_total": 50, "members_present": 48,
                            "tv": rng.uniform(1e7, 5e7, keep.sum()), "adv": rng.integers(0, 50, keep.sum()),
                            "dec": rng.integers(0, 50, keep.sum()), "above_vwap": rng.integers(0, 50, keep.sum()),
                            "top5_ret": rng.normal(0, 0.002, keep.sum())})
    vix_bars = pd.DataFrame({"ts": ts, "close": 14.0 + np.cumsum(rng.normal(0, 0.01, 375))})
    ctx = make_ctx(np.full(375, 0.002), open_=float(close[0]), prev_close=float(close[0]) * 0.999)
    return index_bars, members, vix_bars, ctx


@pytest.mark.parametrize("cut_minute", [5, 47, 120, 300])
def test_no_feature_changes_when_the_future_is_removed(cut_minute):
    index_bars, members, vix_bars, ctx = synthetic_day(seed=cut_minute)
    atm = lambda ts, close, vix: close * vix / 1000.0                 # any per-row function
    full = build_minute_frame(index_bars, members, vix_bars, ctx, H, atm)
    cut_ts = index_bars.ts.iloc[cut_minute]
    part = build_minute_frame(index_bars[index_bars.ts <= cut_ts], members[members.ts <= cut_ts],
                              vix_bars[vix_bars.ts <= cut_ts], ctx, H, atm)
    assert set(FEATURES) >= {"vwap", "upper", "lower", "adv_share", "above_share", "top5_ret", "atm_premium"}
    for name, column in FEATURES.items():
        pd.testing.assert_series_equal(column(full[full.ts <= cut_ts]).reset_index(drop=True),
                                       column(part).reset_index(drop=True), check_names=False)


def test_frame_columns_and_stamps():
    index_bars, members, vix_bars, ctx = synthetic_day(seed=1)
    frame = build_minute_frame(index_bars, members, vix_bars, ctx, H)
    assert (frame["available_at"] - frame["ts"] == pd.Timedelta(minutes=1)).all()
    assert frame["session_high"].is_monotonic_increasing and frame["atm_premium"].isna().all()
    assert frame["upper"].iloc[0] == pytest.approx(max(ctx.open, ctx.prev_close) * 1.002)
