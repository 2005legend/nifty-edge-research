from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from quantdesk.analysis.breadth import breadth_agrees
from quantdesk.analysis.levels import multi_touch, nearest_opposing_distance, opposing_levels, round_levels
from quantdesk.clock import IST
from quantdesk.strategy.types import Signal
from quantdesk.validation.hypotheses import load_hypotheses
from tests.test_bands import make_ctx

H = load_hypotheses()


def minute_frame_from(closes):
    ts = [datetime(2024, 3, 4, 9, 15, tzinfo=IST) + timedelta(minutes=i) for i in range(len(closes))]
    return pd.DataFrame({"ts": ts, "high": closes, "low": closes, "close": closes})


def test_round_levels_and_opposing_levels():
    assert round_levels(22_850.0, 23_120.0, 100) == [22_900.0, 23_000.0, 23_100.0]


def test_a_session_high_touched_twice_three_minutes_apart_is_resistance():
    frame = minute_frame_from([99.9, 100.5, 100.2, 100.1, 100.0, 100.49])   # 100.5 at 09:16 and 100.49 at 09:20
    res, sup = multi_touch(frame, upto=frame.ts.iloc[-1], tol=0.0005, min_touches=2, min_gap_min=3)
    assert res == pytest.approx(100.5) and sup is None


def test_touches_closer_than_the_gap_count_once():
    frame = minute_frame_from([99.9, 100.5, 100.49, 100.2])                 # 1 minute apart: one touch
    assert multi_touch(frame, upto=frame.ts.iloc[-1], tol=0.0005, min_touches=2, min_gap_min=3) == (None, None)


def test_opposing_levels_lie_between_the_close_and_the_target():
    ctx = make_ctx(np.full(375, 0.002), open_=22_950.0, prev_close=22_940.0,
                   prev_day=(23_010.0, 22_800.0, 22_940.0), prev_week=(23_300.0, 22_500.0, 22_900.0))
    sig = Signal("NIFTY", datetime(2024, 3, 4, 10, 0, tzinfo=IST), "long", 22_960.0, 22_955.0, 22_900.0, 22_950.0,
                 22_955.0, 5.0, 22_971.5)
    frame = minute_frame_from([22_950.0, 22_960.0])
    assert opposing_levels(ctx, frame, sig, H) == []                        # nothing in (22960, 22971.5)
    wide = Signal(**{**sig.__dict__, "b": 20.0, "target_level": 23_006.0})
    assert opposing_levels(ctx, frame, wide, H) == [23_000.0]
    assert nearest_opposing_distance(ctx, frame, wide, H) == pytest.approx(40.0)
    assert nearest_opposing_distance(ctx, frame, sig, H) == np.inf          # nothing within 3b = 15 points


def test_breadth_needs_two_of_three():
    row = pd.Series({"adv_share": 0.2, "above_share": 0.6, "top5_ret": -0.001})
    assert breadth_agrees(row, "long", 2) and not breadth_agrees(row, "short", 2)
    assert not breadth_agrees(pd.Series({"adv_share": 0.2, "above_share": 0.4, "top5_ret": np.nan}), "long", 2)
