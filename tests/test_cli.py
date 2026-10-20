from datetime import date, datetime

import pytest

import quantdesk.cli as cli
from quantdesk.clock import IST
from quantdesk.config import load_settings
from quantdesk.recorder.live import RecordingSummary
from quantdesk.storage import Store
from tests.fakes import FakeClock

ANGEL = ["ANGEL_API_KEY", "ANGEL_CLIENT_CODE", "ANGEL_PIN", "ANGEL_TOTP_SECRET"]
NOW = datetime(2026, 10, 19, 16, 0, tzinfo=IST)


class FakeApp:
    def __init__(self, store):
        self.settings = load_settings()
        self.store = store
        self.clock = FakeClock(NOW)
        self.sleep = lambda s: None
        self.events = []

    def client(self):
        return object()

    def master(self, day):
        return "MASTER"

    def constituents(self, day):
        return {"RELIANCE": "2885"}

    def session(self):
        return object()

    def is_trading_day(self, day):
        return True

    def stream_factory(self, on_tick, on_stale):
        raise AssertionError("not used in tests")


@pytest.fixture
def app(tmp_path, monkeypatch):
    fake = FakeApp(Store(tmp_path))
    monkeypatch.setattr(cli, "build_app", lambda settings=None: fake)
    return fake


@pytest.fixture
def angel_env(monkeypatch):
    for name in ANGEL:
        monkeypatch.setenv(name, "x")


def test_unknown_command_exits_nonzero(app):
    with pytest.raises(SystemExit) as err:
        cli.main(["bogus"])
    assert err.value.code != 0


def test_missing_secrets_message_lists_names_not_values(app, monkeypatch, capsys):
    for name in ANGEL:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("ANGEL_PIN", "1234")
    assert cli.main(["login-check"]) == 2
    out = capsys.readouterr().out
    assert "ANGEL_API_KEY" in out and "ANGEL_CLIENT_CODE" in out and "ANGEL_TOTP_SECRET" in out
    assert "1234" not in out
    assert "ANGEL_PIN" not in out


def test_status_prints_health_summary(app, capsys):
    app.store.write_report("health", date(2026, 10, 19), {"date": "2026-10-19", "minutes_recorded": {"NIFTY": 375},
                                                         "problems": []})
    assert cli.main(["status", "--day", "2026-10-19"]) == 0
    out = capsys.readouterr().out
    assert "minutes_recorded" in out and "problems" in out


def test_backfill_dispatches_what(app, angel_env, monkeypatch):
    called = []
    monkeypatch.setattr(cli, "backfill_bhavcopy", lambda *a, **k: called.append("bhavcopy") or {})
    monkeypatch.setattr(cli, "run_backfill", lambda *a, **k: called.append("history"))
    assert cli.main(["backfill", "--what", "bhavcopy", "--start", "2026-10-12"]) == 0
    assert called == ["bhavcopy", "bhavcopy"]  # NSE and BSE


def test_record_saves_recording_report(app, angel_env, monkeypatch):
    monkeypatch.setattr(cli, "run_recording", lambda day, **kw: RecordingSummary(status="ok", minutes_written=375))
    assert cli.main(["record"]) == 0
    assert app.store.read_report("recording", date(2026, 10, 19))["status"] == "ok"
    assert app.store.read_report("health", date(2026, 10, 19)) is not None


def test_record_no_session_exits_nonzero_with_reason(app, angel_env, monkeypatch, capsys):
    monkeypatch.setattr(cli, "run_recording", lambda day, **kw: RecordingSummary(
        status="no_session", errors=["ltp NIFTY (99926000): LoginError: AB1050 invalid totp"]))
    assert cli.main(["record"]) == 1
    out = capsys.readouterr().out
    assert "no_session" in out and "LoginError" in out
