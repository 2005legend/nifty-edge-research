from datetime import date, datetime, time, timedelta

import numpy as np
import pytest

from quantdesk.clock import IST
from quantdesk.pricing.clock import Clock, load_clock, save_clock

FLAT = np.full(375, 1 / 375)
FRONT = np.zeros(375)
FRONT[0] = FRONT[1] = 0.5           # a clock whose whole weight sits in the first two minutes
SESS = (date(2026, 10, 16), date(2026, 10, 19), date(2026, 10, 21))   # Fri, Mon, Wed; Tue 20 Oct a holiday
CLOCK = Clock(FLAT, theta_night=0.5, theta_weekend_day=0.1, theta_holiday=0.2, sessions=SESS)


def at(d, hh, mm):
    return datetime.combine(d, time(hh, mm), tzinfo=IST)


def test_within_a_session_business_time_is_the_weight_share():
    assert CLOCK.bt(at(SESS[0], 9, 15), at(SESS[0], 15, 30)) == pytest.approx(1.0)
    assert CLOCK.bt(at(SESS[0], 12, 22), at(SESS[0], 12, 52)) == pytest.approx(30 / 375)


def test_weekends_and_holidays_add_their_weights():
    # Fri close -> Mon close: night + 2 weekend days + Monday's session
    assert CLOCK.bt(at(SESS[0], 15, 30), at(SESS[1], 15, 30)) == pytest.approx(0.5 + 2 * 0.1 + 1.0)
    # Mon close -> Wed close: night + Tuesday holiday + Wednesday's session
    assert CLOCK.bt(at(SESS[1], 15, 30), at(SESS[2], 15, 30)) == pytest.approx(0.5 + 0.2 + 1.0)


def test_a_saved_clock_loads_back(tmp_path):
    save_clock(tmp_path / "c.yaml", CLOCK, meta={"fit_window": "test"})
    again = load_clock(tmp_path / "c.yaml", SESS)
    assert again.theta_holiday == 0.2 and np.allclose(again.minute_weights, FLAT)


def test_a_partial_span_keeps_the_sessions_in_between_and_the_part_of_today():
    """Fri close to Wed 09:15: two gaps, one whole session, and none of Wednesday."""
    assert CLOCK.bt(at(SESS[0], 15, 30), at(SESS[2], 9, 15)) == pytest.approx(0.7 + 1.0 + 0.7)
    assert CLOCK.bt(at(SESS[1], 9, 15), at(SESS[1], 12, 22)) == pytest.approx(187 / 375)


def test_w_done_interpolates_within_the_minute():
    clock = Clock(FRONT, theta_night=0.5, theta_weekend_day=0.1, theta_holiday=0.2, sessions=SESS)
    assert clock.w_done(at(SESS[0], 9, 14)) == 0.0          # before the open
    assert clock.w_done(at(SESS[0], 9, 15)) == 0.0
    assert clock.w_done(at(SESS[0], 9, 15) + timedelta(seconds=30)) == pytest.approx(0.25)
    assert clock.w_done(at(SESS[0], 9, 16)) == pytest.approx(0.5)
    assert clock.w_done(at(SESS[0], 9, 17)) == 1.0          # the weights are spent
    assert clock.w_done(at(SESS[0], 15, 30)) == 1.0
    assert clock.w_done(at(SESS[0], 16, 0)) == 1.0          # after the close


def test_a_naive_time_is_refused():
    with pytest.raises(ValueError, match="tz-aware"):
        CLOCK.w_done(datetime(2026, 10, 16, 12, 0))
    with pytest.raises(ValueError, match="tz-aware"):
        CLOCK.bt(datetime(2026, 10, 16, 12, 0), at(SESS[0], 13, 0))


def test_an_endpoint_that_is_not_a_session_is_refused():
    """sigma_bt rolls a non-session expiry back to the previous 15:30 rather than guess a weight for it."""
    with pytest.raises(ValueError, match="2026-10-20"):
        CLOCK.bt(at(date(2026, 10, 20), 10, 0), at(SESS[2], 10, 0))
    with pytest.raises(ValueError, match="before"):
        CLOCK.bt(at(SESS[2], 10, 0), at(SESS[1], 10, 0))


def test_the_weights_must_be_one_full_session_that_sums_to_one():
    with pytest.raises(ValueError, match="375"):
        Clock(np.full(374, 1 / 374), theta_night=0.5, theta_weekend_day=0.1, theta_holiday=0.2, sessions=SESS)
    with pytest.raises(ValueError, match="sum"):
        Clock(np.full(375, 1 / 375) * 2, theta_night=0.5, theta_weekend_day=0.1, theta_holiday=0.2, sessions=SESS)
