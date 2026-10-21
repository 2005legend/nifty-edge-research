from datetime import date, datetime, time, timedelta

import numpy as np
import pandas as pd
import pytest

from quantdesk.black76 import black76
from quantdesk.clock import IST
from quantdesk.pricing.clock import Clock
from quantdesk.pricing.surface import (Surface, fifteen_minute_windows, fit_surface, future_sessions,
                                       load_surface, roll_to_session, save_surface, sigma_bt)

FLAT = np.full(375, 1 / 375)


def test_sigma_bt_inverts_a_flat_calendar():
    days = tuple(date(2026, 1, 1) + timedelta(d) for d in range(60))       # every day a session
    clock = Clock(FLAT, 0.0, 0.0, 0.0, days)
    # 30 calendar days = 30 sessions with zero night weight: sigma_bt^2 = 0.15^2 * 30/365 / 30
    assert sigma_bt(15.0, datetime(2026, 1, 2, 15, 30, tzinfo=IST), clock) == pytest.approx(0.15 * np.sqrt(1 / 365))


def test_the_30_day_point_rolls_back_to_a_session_close():
    sessions = (date(2026, 1, 30), date(2026, 2, 2))                       # Fri, Mon
    rolled = roll_to_session(datetime(2026, 2, 1, 11, 0, tzinfo=IST), sessions)   # a Sunday
    assert rolled == datetime(2026, 1, 30, 15, 30, tzinfo=IST)


def test_future_sessions_skip_weekends_and_listed_holidays():
    past = (date(2026, 10, 19), date(2026, 10, 21))
    out = future_sessions(past, holidays={date(2026, 10, 23)}, until=date(2026, 10, 27))
    assert out == past + (date(2026, 10, 22), date(2026, 10, 26), date(2026, 10, 27))


def test_skew_floor_and_atm_level():
    s = Surface(r_dte={d: 1.1 for d in range(7)}, b1=-0.5, b2=0.0, floor=0.5, gamma_dn=-3.0, gamma_up=-1.5)
    # z = ln(K/F) / (sigma_atm * sqrt(T)) = 0.02 / 0.01 = 2  ->  1 - 0.5 * 2 = 0, floored at 0.5
    out = s.sigma_from_atm(0.01, F=100.0, K=np.array([100.0, 100.0 * np.exp(0.02)]), T=1.0)
    assert out[0] == pytest.approx(0.01) and out[1] == pytest.approx(0.005)


def test_spot_vol_beta_raises_vol_on_a_fall():
    s = Surface(r_dte={d: 1.0 for d in range(7)}, b1=0, b2=0, floor=0.5, gamma_dn=-3.0, gamma_up=-1.5)
    assert s.shifted(0.01, move=-0.01) == pytest.approx(0.01 * np.exp(0.03))
    assert s.shifted(0.01, move=0.02) == pytest.approx(0.01 * np.exp(-0.03))


def test_a_saved_surface_loads_back(tmp_path):
    s = Surface(r_dte={d: 1.0 + d / 10 for d in range(7)}, b1=-0.2, b2=0.1, floor=0.5, gamma_dn=-3.0, gamma_up=-1.5)
    save_surface(tmp_path / "s.yaml", s, meta={"fit_window": "test"})
    again = load_surface(tmp_path / "s.yaml")
    assert again.r_dte == s.r_dte and (again.b1, again.gamma_up) == (-0.2, -1.5)


def _planted_chain(days, clock, vix, r, b1, b2):
    """Black-76 closes on a strike grid, priced with sigma = r * sigma_bt * (1 + b1 z + b2 z^2)."""
    rows = []
    for day, ahead in ((d, a) for d in days[:-8] for a in (1, 3)):         # 1 and 3 sessions left
        at = datetime.combine(day, time(15, 30), tzinfo=IST)
        expiry = days[days.index(day) + ahead]
        T = clock.bt(at, datetime.combine(expiry, time(15, 30), tzinfo=IST))
        atm = r * sigma_bt(vix, at, clock)
        F = 22000.0
        for K in np.arange(21500.0, 22550.0, 50.0):
            z = np.log(K / F) / (atm * np.sqrt(T))
            sigma = atm * (1 + b1 * z + b2 * z * z)
            for kind, side in (("call", "CE"), ("put", "PE")):
                rows.append({"day": day, "expiry": expiry, "strike": K, "option_type": side, "instrument": "IDO",
                             "close": black76(F, K, T, sigma, kind=kind), "traded": True})
    return pd.DataFrame(rows)


def test_fit_surface_recovers_planted_level_and_skew():
    days = tuple(date(2026, 1, 1) + timedelta(d) for d in range(80))
    clock = Clock(FLAT, 0.0, 0.0, 0.0, days)
    eod = _planted_chain(list(days), clock, vix=15.0, r=1.2, b1=-0.10, b2=0.05)
    vix = pd.Series(15.0, index=list(days))
    windows = pd.DataFrame({"r": [-0.01, -0.02, 0.01, 0.02], "dlnvix": [0.03, 0.06, -0.015, -0.03]})
    surface, report = fit_surface(eod, vix, clock, windows, dte=[1, 2, 3, 4, 5, 6], max_abs_z=3.0, floor=0.5)
    assert surface.r_dte[3] == pytest.approx(1.2, rel=1e-3)
    assert surface.r_dte[0] == surface.r_dte[1]
    assert (surface.b1, surface.b2) == (pytest.approx(-0.10, abs=2e-3), pytest.approx(0.05, abs=2e-3))
    assert (surface.gamma_dn, surface.gamma_up) == (pytest.approx(-3.0), pytest.approx(-1.5))
    assert report["n_atm"][3] > 0


def test_fifteen_minute_windows_pair_index_and_vix_returns():
    ts = [datetime(2024, 3, 4, 9, 15, tzinfo=IST) + timedelta(minutes=i) for i in range(375)]
    index = pd.DataFrame({"ts": ts, "day": date(2024, 3, 4), "close": np.linspace(100.0, 110.0, 375)})
    vix = pd.DataFrame({"ts": ts, "day": date(2024, 3, 4), "close": np.linspace(15.0, 14.0, 375)})
    w = fifteen_minute_windows(index, vix)
    assert len(w) == 23                                                   # closes at slots 15, 30, .., 360: 23 windows
    first = w.iloc[0]
    assert first["r"] == pytest.approx(np.log(index.close[30] / index.close[15]))
