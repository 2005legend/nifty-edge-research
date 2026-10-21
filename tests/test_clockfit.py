"""Task 12: fitting the business-time clock (design §7).

The three fits are measured separately, so each is planted with a known answer: minute returns whose
variance doubles for the first quarter hour, overnight and session returns whose ratio is theta_n, and a
variance-decay series whose drops are exactly beta0 + beta1*W + beta2*H.
"""

import math
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from quantdesk.black76 import black76
from quantdesk.clock import IST
from quantdesk.pricing.clock import MINUTES, OPEN
from quantdesk.pricing.clockfit import (atm_implied_variance, fit_minute_weights, fit_theta_night,
                                       fit_weekend_holiday)
from quantdesk.validation.hypotheses import load_hypotheses, param

H = load_hypotheses()
Q = param(H, "clock.weight_winsor_q")
DTE = param(H, "clock.atm_dte")

FORWARD, SIGMA, VIX = 22060.0, 0.20, 15.0
DAY, EXPIRY = date(2019, 1, 8), date(2019, 1, 10)          # two trading days left
SESSIONS = tuple(day for day in pd.date_range("2019-01-07", "2019-01-25").date if day.weekday() < 5)
T = (EXPIRY - DAY).days / 365

BETA0, BETA1, BETA2 = 1.5, 0.15, 0.3
THETA_N = 0.5
WEEKS = tuple(day for day in pd.date_range("2019-01-07", "2019-02-01").date
              if day.weekday() < 5 and day != date(2019, 1, 15))       # Tuesday 15 January a holiday


def _planted(days, seed=7, scale=1e-3, loud=2.0, loud_slots=15):
    """Closes whose minute returns have sd `scale`, `loud` times bigger for the first `loud_slots` minutes."""
    rng = np.random.default_rng(seed)
    sd = np.where(np.arange(MINUTES) < loud_slots, loud, 1.0) * scale
    r = rng.normal(size=(len(days), MINUTES)) * sd
    opens = 22000.0 * np.exp(rng.normal(scale=0.002, size=len(days)))
    return opens, opens[:, None] * np.exp(np.cumsum(r, axis=1))


def _bars(closes, days) -> pd.DataFrame:
    stamps = [datetime.combine(day, OPEN, tzinfo=IST) + timedelta(minutes=m) for day in days for m in range(MINUTES)]
    return pd.DataFrame({"day": np.repeat(list(days), MINUTES), "ts": stamps,
                         "close": np.asarray(closes, dtype=float).ravel()})


def _chain(day, expiry, strikes, sigma=SIGMA, forward=FORWARD, symbol="NIFTY", instrument="IDO"):
    """A chain priced off `forward` at `sigma`, so the parity forward and the implied vol are both known."""
    rows = []
    for strike in strikes:
        vol = sigma[strike] if isinstance(sigma, dict) else sigma
        for side, kind in (("CE", "call"), ("PE", "put")):
            rows.append({"day": day, "expiry": expiry, "strike": float(strike), "option_type": side,
                         "symbol": symbol, "instrument": instrument, "traded": True, "volume": 100,
                         "close": black76(forward, float(strike), (expiry - day).days / 365, vol, 0.0, kind)})
    return pd.DataFrame(rows)


def _daily(days, gaps, session=0.02, start=100.0):
    """Official OHLC whose night returns are `gaps` and whose session returns are all `session`."""
    rows, previous = [], start
    for i, day in enumerate(days):
        open_ = start if i == 0 else previous * math.exp(gaps[i])
        close = open_ * math.exp(session)
        rows.append({"day": day, "target": "NIFTY", "open": open_, "high": close, "low": open_, "close": close})
        previous = close
    return pd.DataFrame(rows)


def _gap_counts(sessions):
    """(weekend days, weekday holidays) strictly between each pair of consecutive sessions."""
    counts = []
    for a, b in zip(sessions, sessions[1:]):
        between = [a + timedelta(days=i) for i in range(1, (b - a).days)]
        counts.append((sum(1 for day in between if day.weekday() >= 5),
                       sum(1 for day in between if day.weekday() < 5)))
    return counts


def _v_tilde(sessions, expiry, beta=(BETA0, BETA1, BETA2), start=500.0):
    """A decay series whose consecutive-session drops are exactly beta0 + beta1*W + beta2*H."""
    levels = [start]
    for weekend, holiday in _gap_counts(sessions):
        levels.append(levels[-1] - (beta[0] + beta[1] * weekend + beta[2] * holiday))
    return pd.DataFrame({"day": list(sessions), "expiry": expiry, "v_tilde": levels})


def test_minute_weights_follow_planted_variance():
    days = [date(2019, 1, 1) + timedelta(days=i) for i in range(200)]
    opens, closes = _planted(days)
    w = fit_minute_weights(_bars(closes, days), pd.Series(opens, index=days), Q)
    assert w.shape == (MINUTES,) and w.sum() == pytest.approx(1.0)
    assert w[:15].sum() / w[15:30].sum() == pytest.approx(4.0, rel=0.10)


def test_slot_zero_is_measured_from_the_official_open():
    days = [date(2019, 1, 1) + timedelta(days=i) for i in range(60)]
    _, closes = _planted(days, seed=3, scale=1e-4)
    level = fit_minute_weights(_bars(closes, days), pd.Series(closes[:, 0], index=days), Q)
    gapped = fit_minute_weights(_bars(closes, days), pd.Series(closes[:, 0] * math.exp(-0.005), index=days), Q)
    assert level[0] == pytest.approx(0.0, abs=1e-18)          # the first bar closed at the official open
    assert gapped[0] > 100 * gapped[20]                        # a 0.5% gap dwarfs a minute's variance


def test_a_hole_in_one_day_touches_only_its_own_slot_and_the_next():
    days = [date(2019, 1, 1) + timedelta(days=i) for i in range(40)]
    opens, closes = _planted(days, seed=5)
    holed = closes.copy()
    holed[0, 100] = np.nan                                     # one missing bar, one day only
    w = fit_minute_weights(_bars(holed, days), pd.Series(opens, index=days), Q)
    whole = fit_minute_weights(_bars(closes, days), pd.Series(opens, index=days), Q)
    scale = w[0] / whole[0]
    assert w.sum() == pytest.approx(1.0)
    assert np.allclose(w[1:100], whole[1:100] * scale)         # nothing shifted along the day
    assert np.allclose(w[102:], whole[102:] * scale)
    assert w[100] != pytest.approx(whole[100] * scale)         # the hole is not filled in
    assert w[101] != pytest.approx(whole[101] * scale)         # and it spoils the return that spans it


def test_one_absurd_minute_is_winsorised_away():
    days = [date(2019, 1, 1) + timedelta(days=i) for i in range(6)]
    opens, closes = _planted(days, seed=11)
    wild = closes.copy()
    wild[3, 200] *= math.exp(0.9)                              # one 90% print on one day
    at = lambda frame: fit_minute_weights(_bars(frame, days), pd.Series(opens, index=days), 0.5)
    assert at(wild)[200] < 3 * at(closes)[200]                 # the median cap bites; unclipped it is 1e5 times


def test_theta_night_is_overnight_variance_over_session_variance():
    days = [date(2019, 1, 7), date(2019, 1, 8), date(2019, 1, 9)]       # Monday to Wednesday
    assert fit_theta_night(_daily(days, gaps=[0.0, 0.01, 0.01]), days) == pytest.approx((0.01 / 0.02) ** 2)


def test_only_back_to_back_nights_are_measured():
    days = [date(2019, 1, 7), date(2019, 1, 8), date(2019, 1, 11), date(2019, 1, 14)]
    daily = _daily(days, gaps=[0.0, 0.01, 0.50, 0.50])         # the weekend nights are wild
    assert fit_theta_night(daily, days) == pytest.approx((0.01 / 0.02) ** 2)


def test_a_pair_whose_day_is_missing_from_daily_is_skipped():
    days = [date(2019, 1, 7), date(2019, 1, 8), date(2019, 1, 9)]
    daily = _daily(days, gaps=[0.0, 0.01, 0.30]).iloc[:2]      # the 9th has no official OHLC yet
    assert fit_theta_night(daily, days) == pytest.approx((0.01 / 0.02) ** 2)


def test_theta_night_needs_one_back_to_back_pair():
    days = [date(2019, 1, 11), date(2019, 1, 14)]              # Friday and Monday only
    with pytest.raises(ValueError, match="back-to-back"):
        fit_theta_night(_daily(days, gaps=[0.0, 0.01]), days)


def test_v_tilde_is_implied_variance_times_t_over_vix_squared():
    eod = _chain(DAY, EXPIRY, [22000.0, 22050.0, 22100.0])     # 22050 is nearest the parity forward
    vt = atm_implied_variance(eod, pd.Series({DAY: VIX}), DTE, SESSIONS)
    assert list(vt.columns) == ["day", "expiry", "v_tilde"] and len(vt) == 1
    assert vt.iloc[0]["day"] == DAY and vt.iloc[0]["expiry"] == EXPIRY
    assert vt.iloc[0]["v_tilde"] == pytest.approx(SIGMA ** 2 * T / (VIX / 100) ** 2)


def test_untraded_strikes_are_ignored():
    eod = _chain(DAY, EXPIRY, [22000.0, 22050.0, 22100.0], sigma={22000.0: SIGMA, 22050.0: SIGMA, 22100.0: 0.30})
    at_the_money = (eod["strike"] == 22050.0) & (eod["option_type"] == "CE")
    eod.loc[at_the_money, "close"] = 1e-6                      # an absurd print on a row that never dealt
    eod.loc[at_the_money, "traded"] = False
    vt = atm_implied_variance(eod, pd.Series({DAY: VIX}), DTE, SESSIONS)
    assert len(vt) == 1                                        # not dropped: it fell back a strike
    assert vt.iloc[0]["v_tilde"] == pytest.approx(0.30 ** 2 * T / (VIX / 100) ** 2)


def test_a_strike_with_one_leg_untraded_is_not_a_candidate():
    eod = _chain(DAY, EXPIRY, [22050.0])
    eod.loc[eod["option_type"] == "PE", "traded"] = False
    assert atm_implied_variance(eod, pd.Series({DAY: VIX}), DTE, SESSIONS).empty


def test_the_dte_window_is_the_pre_registered_one():
    near, far = date(2019, 1, 9), date(2019, 1, 25)           # one trading day left, and thirteen
    eod = pd.concat([_chain(DAY, expiry, [22050.0]) for expiry in (EXPIRY, near, far)], ignore_index=True)
    vt = atm_implied_variance(eod, pd.Series({DAY: VIX}), DTE, SESSIONS)
    assert vt["expiry"].tolist() == [EXPIRY]


def test_a_day_without_a_vix_close_is_dropped():
    eod = _chain(DAY, EXPIRY, [22050.0])
    assert atm_implied_variance(eod, pd.Series(dtype=float), DTE, SESSIONS).empty


def test_futures_rows_are_ignored():
    eod = pd.concat([_chain(DAY, EXPIRY, [22050.0]),
                     _chain(DAY, EXPIRY, [22060.0], sigma=0.9, instrument="IDF")], ignore_index=True)
    vt = atm_implied_variance(eod, pd.Series({DAY: VIX}), DTE, SESSIONS)
    assert len(vt) == 1 and vt.iloc[0]["v_tilde"] == pytest.approx(SIGMA ** 2 * T / (VIX / 100) ** 2)


def test_weekend_weight_is_recovered():
    out = fit_weekend_holiday(_v_tilde(WEEKS, date(2019, 2, 7)), WEEKS, THETA_N)
    assert out["theta_weekend_day"] == pytest.approx(0.15 / 1.5 * 1.5)
    assert out["theta_holiday"] == pytest.approx(0.3)
    assert out["n"] == len(WEEKS) - 1
    assert out["se_weekend"] == pytest.approx(0.0, abs=1e-9)   # the planted drops have no residual


def test_only_consecutive_sessions_of_one_expiry_are_paired():
    vt = _v_tilde(WEEKS, date(2019, 2, 7))
    holed = vt[vt["day"] != WEEKS[9]]
    out = fit_weekend_holiday(holed, WEEKS, THETA_N)
    assert out["n"] == len(WEEKS) - 3                          # the two pairs across the hole are gone
    assert out["theta_weekend_day"] == pytest.approx(0.15)     # the rest still carry the planted answer


def test_the_thetas_are_clipped_to_their_range():
    out = fit_weekend_holiday(_v_tilde(WEEKS, date(2019, 2, 7), beta=(1.5, -5.0, 9.0)), WEEKS, THETA_N)
    assert out["theta_weekend_day"] == 0.0                     # variance that rises over a weekend
    assert out["theta_holiday"] == 1 + THETA_N                 # and a holiday weight above a whole night


def test_a_fit_on_too_few_pairs_is_refused():
    vt = _v_tilde(WEEKS[:2], date(2019, 2, 7))
    with pytest.raises(ValueError, match="pairs"):
        fit_weekend_holiday(vt, WEEKS[:2], THETA_N)
