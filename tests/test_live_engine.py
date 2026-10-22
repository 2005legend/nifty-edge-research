from datetime import date, datetime, timedelta

import pandas as pd
import pytest

from quantdesk.clock import IST
from quantdesk.live.engine import LiveEngine
from quantdesk.live.journal import Journal
from quantdesk.strategy.configs import config_for
from quantdesk.strategy.meta import Consensus
from quantdesk.validation.hypotheses import load_hypotheses
from tests.test_journal import alert as alert_row
from tests.test_pipeline import AT, DAY, setup

H = load_hypotheses()


class Notes:
    def __init__(self):
        self.sent = []

    def send(self, text):
        self.sent.append(text)
        return True


class FakeLiveSource:
    """The pipeline test's passing setup, extended into a trade that runs up and then reverses."""

    def __init__(self):
        self.ctx, base, self.helpers_ = setup()
        later = [AT + timedelta(minutes=k) for k in range(5, 90)]
        path = [22010.0 + min(k, 40) * 1.5 - max(0, k - 40) * 2.5 for k in range(5, 90)]
        extra = base.iloc[[-1] * len(later)].copy()
        extra["ts"], extra["close"], extra["high"], extra["low"] = later, path, path, path
        self.frame_ = pd.concat([base, extra], ignore_index=True)
        self.helpers_.quotes.frame = self.frame_.set_index("ts")

    def context(self, index, day):
        if index != "NIFTY":
            raise KeyError(index)
        return self.ctx

    def frame(self, ctx):
        return self.frame_

    def helpers(self, ctx, frame):
        return self.helpers_


def engine(tmp_path, mode="live", journal=None):
    notes = Notes()
    j = journal or Journal(tmp_path / "j.sqlite")
    e = LiveEngine(lambda now: FakeLiveSource(), j, notes, config_for("X1", {}), Consensus(0, 0), H, DAY, mode=mode,
                   sessions=[DAY])
    return e, j, notes


def test_a_live_alert_is_journalled_pushed_and_paper_traded(tmp_path):
    e, j, notes = engine(tmp_path)
    decisions = e.step(AT + timedelta(seconds=5))
    assert any(d.alert for d in decisions)
    alerts = j.alerts()
    assert len(alerts) == 1 and alerts.loc[0, "mode"] == "live" and notes.sent[0].startswith("ALERT")
    paper = j.open_papers()
    assert len(paper) == 1 and paper.iloc[0]["entry_premium"] == pytest.approx(alerts.loc[0, "entry_limit"] - 0.05)


def test_shadow_mode_logs_but_never_pushes(tmp_path):
    e, j, notes = engine(tmp_path, mode="shadow")
    e.step(AT + timedelta(seconds=5))
    assert j.alerts().loc[0, "mode"] == "shadow" and notes.sent == []


def test_a_lock_holds_the_alert_back(tmp_path):
    j = Journal(tmp_path / "j.sqlite")
    earlier = j.add_alert(alert_row(at=AT.replace(hour=9, minute=50)))
    j.open_paper(earlier, AT.replace(hour=9, minute=50), 50.0)
    e, j, notes = engine(tmp_path, journal=j)
    e.step(AT + timedelta(seconds=5))
    assert j.alerts().iloc[-1]["mode"] == "suppressed" and notes.sent == []
    assert "held back" in j.events().iloc[-1]["detail"]


def test_the_paper_trade_ratchets_and_exits_with_messages(tmp_path):
    e, j, notes = engine(tmp_path)
    now = AT + timedelta(seconds=5)
    while now < AT + timedelta(minutes=90):
        e.step(now)
        now += timedelta(minutes=1)
    assert any(t.startswith("MOVE STOP") for t in notes.sent)
    assert any(t.startswith("EXIT NOW") for t in notes.sent)
    closed = j.closed_trades("paper")
    assert len(closed) == 1 and closed.loc[0, "reason"] == "stop" and closed.loc[0, "pnl"] > 0


def test_a_kill_switch_after_a_close_turns_alerts_to_shadow(tmp_path):
    e, j, notes = engine(tmp_path)
    e.kill_params = {"mu0": 20.0, "breakeven": 0.0, "sigma": 100.0, "cusum_h": 0.1}
    now = AT + timedelta(seconds=5)
    while now < AT + timedelta(minutes=90):
        e.step(now)
        now += timedelta(minutes=1)
    assert j.get_state("kill_switch") == "cusum"
    assert any(t.startswith("KILL SWITCH") for t in notes.sent)
    assert (j.events()["kind"] == "kill_switch").any()


def test_a_fired_kill_switch_keeps_new_alerts_in_shadow(tmp_path):
    e, j, notes = engine(tmp_path)
    j.set_state("kill_switch", "sprt")
    e.step(AT + timedelta(seconds=5))
    assert j.alerts().loc[0, "mode"] == "shadow" and notes.sent == []
