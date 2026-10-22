from dataclasses import replace
from datetime import date, datetime, time, timedelta

import numpy as np
import pandas as pd
import pytest

from quantdesk.calendar.events import Event
from quantdesk.clock import IST
from quantdesk.strategy.gates import GATES, Helpers, first_failed_gate
from quantdesk.strategy.timeline import check_times, timeline_block
from quantdesk.strategy.types import Signal
from quantdesk.validation.hypotheses import load_hypotheses
from tests.derived_fixture import clock_for, flat_surface, session_days
from tests.test_bands import make_ctx

H = load_hypotheses()
DAY = date(2024, 3, 5)
AT = datetime(2024, 3, 5, 10, 0, tzinfo=IST)
HELP = Helpers(clock=clock_for(session_days(60)), surface=flat_surface(), quotes=None)


def passing():
    ctx = make_ctx(np.full(375, 0.0002), open_=22000.0, prev_close=22000.0, day=DAY,
                   prev_day=(22300.0, 21700.0, 22000.0), prev_week=(22400.0, 21600.0, 21900.0),
                   expiry_1=date(2024, 3, 7), expiry_2=date(2024, 3, 14), dte_1=2, sigma_day=0.01,
                   vix_prev_close=14.0, vol_rich_threshold=10.0, spike_ref=np.full(375, 0.5))
    ts = [AT - timedelta(minutes=k) for k in range(10, 0, -1)]
    frame = pd.DataFrame({"ts": ts, "close": 22010.0, "high": 22010.0, "low": 22005.0, "vwap": 21995.0, "vix": 14.0,
                          "adv_share": 0.2, "above_share": 0.6, "top5_ret": 0.001, "atm_premium": 120.0})
    sig = Signal("NIFTY", AT, "long", 22010.0, 21990.0, 21960.0, 21995.0, 21990.0, 20.0, 22056.0)
    return sig, ctx, frame


def test_a_clean_setup_passes_every_gate():
    sig, ctx, frame = passing()
    assert first_failed_gate(sig, ctx, frame, HELP, H) is None
    assert [name for name, _ in GATES] == ["event_shock", "stop_fit", "room_in_time", "room_to_run", "volatility",
                                           "confirmation", "spike_guard"]


def test_event_shock_fails_on_a_vix_jump():
    sig, ctx, frame = passing()
    frame["vix"] = 15.5
    assert first_failed_gate(sig, ctx, frame, HELP, H) == "event_shock"


def test_stop_fit_fails_when_the_stop_is_wider_than_half_a_day():
    sig, ctx, frame = passing()
    wide = replace(sig, b=200.0, stop_level=21810.0, target_level=22470.0)
    assert first_failed_gate(wide, ctx, frame, HELP, H) == "stop_fit"


def test_room_in_time_fails_late_in_a_quiet_day():
    sig, ctx, frame = passing()
    late = replace(ctx, sigma_day=0.0008)
    assert first_failed_gate(sig, late, frame, HELP, H) == "room_in_time"


def test_room_to_run_fails_with_a_level_before_the_target():
    sig, ctx, frame = passing()
    blocked = replace(ctx, prev_day=(22030.0, 21700.0, 22000.0))
    assert first_failed_gate(sig, blocked, frame, HELP, H) == "room_to_run"


def test_volatility_fails_when_implied_is_rich_against_har():
    sig, ctx, frame = passing()
    assert first_failed_gate(sig, replace(ctx, vol_rich_threshold=0.1), frame, HELP, H) == "volatility"


def test_confirmation_needs_breadth():
    sig, ctx, frame = passing()
    frame["adv_share"], frame["above_share"] = -0.2, 0.4
    assert first_failed_gate(sig, ctx, frame, HELP, H) == "confirmation"


def test_spike_guard_blocks_after_a_premium_jump():
    sig, ctx, frame = passing()
    frame.loc[frame.index[-3], "atm_premium"] = 125.0           # a 5-rupee minute against a 0.5 median
    assert first_failed_gate(sig, ctx, frame, HELP, H) == "spike_guard"


def test_check_times_end_earlier_on_expiry_day():
    normal = check_times(date(2024, 3, 5), False, H)
    expiry = check_times(date(2024, 3, 7), True, H)
    assert normal[0].time() == time(9, 45) and normal[-1].time() == time(14, 0) and len(normal) == 18
    assert expiry[-1].time() == time(13, 30)


def test_timeline_blocks():
    ctx = make_ctx(np.full(375, 0.002), day=DAY)
    assert timeline_block(replace(ctx, session_kind="irregular"), AT, H) == "irregular_session"
    assert timeline_block(ctx, AT + timedelta(minutes=5), H) == "not_a_check_time"
    assert timeline_block(ctx, datetime(2024, 3, 5, 14, 15, tzinfo=IST), H) == "after_last_entry"
    rbi = Event(DAY, time(10, 0), "rbi_mpc", "E2", "RBI", "https://x")
    assert timeline_block(replace(ctx, events=(rbi,)), datetime(2024, 3, 5, 10, 30, tzinfo=IST), H) == "rbi_wait"
    assert timeline_block(ctx, AT, H) is None
