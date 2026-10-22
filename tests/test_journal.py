from datetime import datetime

import pytest

from quantdesk.clock import IST
from quantdesk.live.journal import Journal

AT = datetime(2026, 10, 22, 10, 0, tzinfo=IST)


def alert(**kw):
    base = {"at": AT, "index": "NIFTY", "side": "long", "mode": "live", "expiry": "2026-10-27", "strike": 22000.0,
            "kind": "CE", "lot": 65, "entry_limit": 60.1, "index_stop": 21980.0, "index_target": 22046.0,
            "backstop_trigger": 53.9, "backstop_limit": 48.5, "p": 0.45, "ev": 120.0, "delta": 0.0,
            "reasons_for": "technical +1.20", "reasons_against": "", "signal_id": "NIFTY-202610221000"}
    return {**base, **kw}


def test_alerts_are_stored_and_the_owner_marks_them(tmp_path):
    j = Journal(tmp_path / "j.sqlite")
    a = j.add_alert(alert())
    assert j.alerts().loc[0, "status"] == "new"
    j.set_alert_status(a, "took")
    j.add_real_fill(a, 60.0, AT)
    assert j.alerts().loc[0, "status"] == "took" and j.real_trades().loc[0, "fill_premium"] == 60.0


def test_paper_trades_open_and_close_with_r(tmp_path):
    j = Journal(tmp_path / "j.sqlite")
    a = j.add_alert(alert())
    p = j.open_paper(a, AT, 60.15)
    j.close_paper(p, AT.replace(hour=11), 70.0, "stop", 580.0)
    closed = j.closed_trades("paper")
    assert len(closed) == 1 and closed.loc[0, "r"] == pytest.approx(580.0 / 400)
    assert j.open_papers().empty


def test_events_and_state(tmp_path):
    j = Journal(tmp_path / "j.sqlite")
    j.log_event("unlock", "day lock lifted: data error, not a real loss")
    j.set_state("mode", "shadow")
    assert j.get_state("mode") == "shadow" and j.get_state("missing", "x") == "x"
    assert j.events().loc[0, "kind"] == "unlock"
