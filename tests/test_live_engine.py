from datetime import date, datetime, timedelta

import pandas as pd
import pytest

from quantdesk.backtest.fills import fill
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
    assert j.open_papers().empty                            # the fill bar (T, with delay 1) is not recorded yet
    e.step(AT + timedelta(minutes=1, seconds=5))
    paper = j.open_papers()
    src = FakeLiveSource()
    d = next(d for d in decisions if d.alert)
    expected = fill(d.signal, d.alert.choice, src.frame_, src.helpers_.quotes, 1, src.ctx, H)
    assert len(paper) == 1 and paper.iloc[0]["entry_premium"] == pytest.approx(expected.premium)
    assert paper.iloc[0]["entry_at"].startswith(str(expected.at)[:16].replace(" ", "T"))


def test_shadow_setups_reach_the_phone_marked_do_not_trade(tmp_path):
    e, j, notes = engine(tmp_path, mode="shadow")
    now = AT + timedelta(seconds=5)
    while now < AT + timedelta(minutes=90):
        e.step(now)
        now += timedelta(minutes=1)
    assert j.alerts().loc[0, "mode"] == "shadow"
    assert notes.sent[0].startswith("ALERT (SHADOW - do not trade)")
    assert any(t.startswith("SHADOW EXIT") for t in notes.sent)
    assert not any(t.startswith("MOVE STOP") for t in notes.sent)        # stop moves stay on the dashboard


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
    assert j.alerts().loc[0, "mode"] == "shadow" and notes.sent[0].startswith("ALERT (SHADOW")


def test_a_second_index_alert_at_the_same_check_is_held_by_the_pending_first(tmp_path):
    class TwoIndex(FakeLiveSource):
        def context(self, index, day):
            from dataclasses import replace
            return replace(self.ctx, index=index)

    notes = Notes()
    j = Journal(tmp_path / "j.sqlite")
    e = LiveEngine(lambda now: TwoIndex(), j, notes, config_for("X1", {}), Consensus(0, 0), H, DAY, mode="live",
                   sessions=[DAY])
    e.step(AT + timedelta(seconds=5))
    modes = j.alerts()["mode"].tolist()
    assert modes == ["live", "suppressed"] and len(notes.sent) == 1


def test_idea_mode_sends_the_brief_once_and_paper_tracks_each_idea(tmp_path):
    notes = Notes()
    j = Journal(tmp_path / "j.sqlite")
    briefs = []

    def brief(now, ctxs, frames):
        briefs.append(now)
        return "MORNING BRIEF test", {"NIFTY": "UP"}

    e = LiveEngine(lambda now: FakeLiveSource(), j, notes, config_for("B0", {}), Consensus(-3.0, 0.0), H, DAY,
                   mode="shadow", sessions=[DAY], idea=True, brief=brief)
    now = AT + timedelta(seconds=5)
    while now < AT + timedelta(minutes=90):
        e.step(now)
        now += timedelta(minutes=1)
    assert len(briefs) == 1 and notes.sent[0] == "MORNING BRIEF test" and j.get_state(f"lean_{DAY}_NIFTY") == "UP"
    ideas = [t for t in notes.sent if t.startswith("IDEA ")]
    assert ideas and "Entry: buy at or below" in ideas[0] and "Target: Rs" in ideas[0]
    assert "Stop-loss: Rs" in ideas[0] and "odds" in ideas[0] and "Risk" not in ideas[0]   # no rupee amounts
    assert j.alerts().loc[0, "mode"] == "idea" and len(j.closed_trades("paper")) == 1
    assert any(t.startswith("IDEA EXIT") for t in notes.sent)


def test_a_late_start_never_alerts_on_old_checks(tmp_path):
    e, j, notes = engine(tmp_path)
    e.step(AT + timedelta(minutes=10))
    assert j.alerts().empty and notes.sent == []
    assert (j.events()["kind"] == "missed").any()


def test_a_restart_resumes_the_open_paper_trade_and_its_exit_messages(tmp_path):
    e, j, notes = engine(tmp_path)
    e.step(AT + timedelta(seconds=5))
    e.step(AT + timedelta(minutes=1, seconds=5))
    assert len(j.open_papers()) == 1
    again, _, notes2 = engine(tmp_path, journal=j)          # the process restarted, e.g. after a power cut
    now = AT + timedelta(minutes=3, seconds=5)
    while now < AT + timedelta(minutes=90):
        again.step(now)
        now += timedelta(minutes=1)
    assert len(j.alerts()) == 1 and len(j.closed_trades("paper")) == 1
    assert any(t.startswith("EXIT NOW") for t in notes2.sent) and not any(t.startswith("ALERT") for t in notes2.sent)
