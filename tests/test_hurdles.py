from datetime import date

import numpy as np
import pandas as pd
import pytest

from quantdesk.analysis.hurdles import calibrate_cusum_h, cusum_alarms, shock_days, shock_delta


def test_cusum_alarms_on_a_variance_jump_and_not_before():
    rng = np.random.default_rng(0)
    r = pd.Series(np.r_[rng.normal(0, 0.01, 300), rng.normal(0, 0.03, 40)])
    alarms = cusum_alarms(r, sigma_window=250, h=5.0)
    assert not alarms.iloc[:300].any() and alarms.iloc[300:340].any()


def test_calibrated_h_gives_about_one_alarm_per_250_sessions():
    rng = np.random.default_rng(1)
    r = pd.Series(rng.standard_t(4, 1500) * 0.01)
    h = calibrate_cusum_h(r, sigma_window=250, block=20, resamples=200, target_rate=1 / 250, seed=1)
    rate = cusum_alarms(r, 250, h).iloc[250:].mean()
    assert 0.25 / 250 <= rate <= 3.0 / 250


def test_shock_lasts_five_sessions():
    days = pd.date_range("2024-01-01", periods=8).date
    shock = pd.Series([False, True] + [False] * 6, index=days)
    assert shock_delta(shock, days[5], sessions=5, delta=0.04) == 0.04
    assert shock_delta(shock, days[6], sessions=5, delta=0.04) == 0.0


def test_shock_triggers_on_a_vix_jump_a_big_gap_or_a_recent_alarm():
    days = list(pd.bdate_range("2024-01-01", periods=30).date)
    daily = pd.DataFrame({"day": days, "open": 100.0, "close": 100.0})
    vix = pd.Series(12.0, index=days)
    vix.iloc[10] = 12.0 * np.exp(0.25)                       # 5-day log jump >= 0.20, read the next session
    daily.loc[20, "open"] = 101.0                            # a 1% gap
    sigma_gap = pd.Series(0.005, index=days)                 # 1.5 x 0.5% = 0.75% < 1%
    alarms = pd.Series(False, index=days)
    alarms.iloc[25] = True                                   # an alarm after the close of day 25
    out = shock_days(daily, vix, sigma_gap, alarms, vix_log5=0.20, gap_sigma=1.5)
    assert out.iloc[11] and not out.iloc[10]
    assert out.iloc[20]
    assert not out.iloc[25] and out.iloc[26]
