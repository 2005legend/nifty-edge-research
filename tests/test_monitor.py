from datetime import date, datetime

import numpy as np
import pytest

from quantdesk.clock import IST
from quantdesk.live.journal import Journal
from quantdesk.live.monitor import cusum_alarm, kill_switches, locks, sprt
from quantdesk.validation.hypotheses import load_hypotheses
from tests.test_journal import alert

H = load_hypotheses()
SESSIONS = [date(2026, 10, d) for d in (19, 21, 22, 23, 26, 27, 28, 29, 30)]


def trade(j, day, pnl, hour=10):
    at = datetime(day.year, day.month, day.day, hour, 0, tzinfo=IST)
    a = j.add_alert(alert(at=at))
    p = j.open_paper(a, at, 60.0)
    j.close_paper(p, at.replace(hour=hour + 1), 60.0 + pnl / 65, "stop", pnl)


def test_one_trade_a_day_and_the_day_loss_lock(tmp_path):
    j = Journal(tmp_path / "j.sqlite")
    day = date(2026, 10, 22)
    assert locks(j, day, SESSIONS, H) == []
    trade(j, day, -420.0)
    assert set(locks(j, day, SESSIONS, H)) == {"per_day", "day_loss"}


def test_week_cap_and_week_loss(tmp_path):
    j = Journal(tmp_path / "j.sqlite")
    for d, pnl in ((date(2026, 10, 26), -300.0), (date(2026, 10, 27), -300.0), (date(2026, 10, 28), -450.0)):
        trade(j, d, pnl)
    out = locks(j, date(2026, 10, 29), SESSIONS, H)
    assert "per_week" in out and "week_loss" in out


def test_an_unlock_needs_a_typed_reason(tmp_path):
    j = Journal(tmp_path / "j.sqlite")
    day = date(2026, 10, 22)
    trade(j, day, -420.0)
    j.log_event("unlock", "day_loss|2026-10-22|data error, the loss was a bad tick")
    assert "day_loss" not in locks(j, day, SESSIONS, H)


def test_sprt_stops_when_the_edge_is_gone_and_continues_otherwise():
    rng = np.random.default_rng(0)
    assert sprt(rng.normal(-0.1, 1.0, 400), mu0=0.25, mu1=0.0, sigma=1.0, alpha=0.10, beta=0.20) == "stop"
    assert sprt(rng.normal(0.25, 1.0, 400), mu0=0.25, mu1=0.0, sigma=1.0, alpha=0.10, beta=0.20) == "go"
    assert sprt(np.array([0.1]), mu0=0.25, mu1=0.0, sigma=1.0, alpha=0.10, beta=0.20) == "continue"


def test_cusum_alarms_on_a_drop_in_mean_r():
    rng = np.random.default_rng(1)
    assert not cusum_alarm(rng.normal(0.25, 1.0, 100), target=0.15, k=0.075, h=5.0)
    assert cusum_alarm(np.r_[rng.normal(0.25, 1.0, 50), rng.normal(-0.5, 1.0, 60)], target=0.15, k=0.075, h=5.0)


def test_kill_switches_include_the_capital_floor(tmp_path):
    j = Journal(tmp_path / "j.sqlite")
    for i in range(8):
        trade(j, SESSIONS[i], -400.0)
    reasons = kill_switches(j, {"mu0": 0.25, "breakeven": 0.0, "sigma": 1.0, "cusum_h": 5.0}, H)
    assert "capital_floor" in reasons
