from datetime import date, datetime

import pytest

import quantdesk.cli as cli
from quantdesk.clock import IST
from quantdesk.config import load_settings
from quantdesk.macro.collect import MacroReport
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

    def master_fallback(self, day):
        return None

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


def test_fundamentals_backfill_can_fill_a_closed_range(app, monkeypatch):
    """--end refetches one gap without downloading every day since then again."""
    calls = []
    monkeypatch.setattr(cli, "run_macro_daily",
                        lambda day, **kw: calls.append((kw["start"], day)) or MacroReport(status={}))
    assert cli.main(["backfill", "--what", "fundamentals", "--start", "2015-01-01", "--end", "2015-06-30"]) == 0
    assert calls == [(date(2015, 1, 1), date(2015, 6, 30))]


def test_record_saves_recording_report(app, angel_env, monkeypatch):
    monkeypatch.setattr(cli, "run_recording", lambda day, **kw: RecordingSummary(status="ok", minutes_written=375))
    assert cli.main(["record"]) == 0
    assert app.store.read_report("recording", date(2026, 10, 19))["status"] == "ok"
    assert app.store.read_report("health", date(2026, 10, 19)) is not None


def test_record_keeps_the_pc_awake_while_recording(app, angel_env, monkeypatch):
    """A power cut puts a laptop on battery, which slept after 15 minutes on 21 Oct 2026 and lost 73 minutes."""
    events = []

    class Awake:
        def __enter__(self):
            events.append("awake")

        def __exit__(self, *exc):
            events.append("released")

    monkeypatch.setattr(cli, "keep_awake", Awake)
    monkeypatch.setattr(cli, "run_recording",
                        lambda day, **kw: events.append("recording") or RecordingSummary(status="ok"))
    assert cli.main(["record"]) == 0
    assert events == ["awake", "recording", "released"]


def test_record_no_session_exits_nonzero_with_reason(app, angel_env, monkeypatch, capsys):
    monkeypatch.setattr(cli, "run_recording", lambda day, **kw: RecordingSummary(
        status="no_session", errors=["ltp NIFTY (99926000): LoginError: AB1050 invalid totp"]))
    assert cli.main(["record"]) == 1
    out = capsys.readouterr().out
    assert "no_session" in out and "LoginError" in out


def test_record_second_copy_prints_notice_not_traceback(app, angel_env, monkeypatch, capsys):
    from quantdesk.recorder.live import AlreadyRunningError

    def refuse(day, **kw):
        raise AlreadyRunningError("record already running (pid 18988)")

    monkeypatch.setattr(cli, "run_recording", refuse)
    assert cli.main(["record"]) == 0
    out = capsys.readouterr().out
    assert "already running (pid 18988)" in out and "nothing to do" in out


def test_record_on_holiday_downloads_nothing(app, angel_env, monkeypatch, capsys):
    """Backlog 4: the 35 MB master and the Nifty 50 list were fetched before the holiday check."""
    monkeypatch.setattr(app, "is_trading_day", lambda day: False)
    monkeypatch.setattr(app, "master", lambda day: (_ for _ in ()).throw(AssertionError("downloaded on a holiday")))
    monkeypatch.setattr(app, "constituents", lambda day: (_ for _ in ()).throw(AssertionError("downloaded")))
    assert cli.main(["record"]) == 0
    assert "holiday" in capsys.readouterr().out
    assert app.store.read_report("recording", date(2026, 10, 19))["status"] == "holiday"


def test_record_without_nifty50_list_still_records_options(app, angel_env, monkeypatch):
    seen = {}

    def no_list(day):
        raise ConnectionError("NSE blocked the request")

    def fake_run(day, **kw):
        seen.update(kw)
        return RecordingSummary(status="ok", minutes_written=360)

    monkeypatch.setattr(app, "constituents", no_list)
    monkeypatch.setattr(cli, "run_recording", fake_run)
    assert cli.main(["record"]) == 0
    assert seen["constituents"] == {}
    warnings = app.store.read_report("recording", date(2026, 10, 19))["warnings"]
    assert any("Nifty 50 list" in w and "ConnectionError" in w for w in warnings)


def test_record_reports_master_fallback(app, angel_env, monkeypatch):
    """Backlog 7: using an older copy of the instrument master must show in the reports."""
    monkeypatch.setattr(app, "master_fallback", lambda day: "instrument master: download failed, using the 2026-10-16 copy")
    monkeypatch.setattr(cli, "run_recording", lambda day, **kw: RecordingSummary(status="ok", minutes_written=360))
    assert cli.main(["record"]) == 0
    warnings = app.store.read_report("recording", date(2026, 10, 19))["warnings"]
    assert any("2026-10-16 copy" in w for w in warnings)


def test_eod_on_holiday_does_nothing(app, angel_env, monkeypatch, capsys):
    monkeypatch.setattr(app, "is_trading_day", lambda day: False)
    monkeypatch.setattr(cli, "run_eod", lambda *a, **k: (_ for _ in ()).throw(AssertionError("ran on a holiday")))
    assert cli.main(["eod", "--day", "2026-10-20"]) == 0
    assert "holiday" in capsys.readouterr().out


def test_eod_without_angel_secrets_still_downloads_exchange_files(app, monkeypatch, capsys):
    """Backlog 5: NSE/BSE files need no Angel One login; only the VIX daily candle does."""
    for name in ANGEL:
        monkeypatch.delenv(name, raising=False)
    seen = {}

    def fake_run_eod(day, **kw):
        seen.update(kw)
        from quantdesk.eod.flows import EodReport
        return EodReport(status={"nse_fo": "ok", "vix_daily": "skipped: no Angel One credentials"})

    monkeypatch.setattr(cli, "run_eod", fake_run_eod)
    assert cli.main(["eod", "--day", "2026-10-19"]) == 0
    assert seen["client"] is None


def test_bhavcopy_backfill_bootstraps_nse_cookies(app, monkeypatch):
    class Session:
        def __init__(self):
            self.bootstrapped = []

        def bootstrap(self, url):
            self.bootstrapped.append(url)

    session = Session()
    monkeypatch.setattr(app, "session", lambda: session)
    monkeypatch.setattr(cli, "backfill_bhavcopy", lambda *a, **k: {})
    assert cli.main(["backfill", "--what", "bhavcopy", "--start", "2026-10-12"]) == 0
    assert session.bootstrapped == [app.settings["urls"]["nse_home"]]


def test_news_refuses_a_second_copy(app, monkeypatch, capsys):
    """Backlog 6: two pollers store every headline twice."""
    from quantdesk.recorder.live import run_lock

    monkeypatch.setattr(cli, "poll_once", lambda *a, **k: (_ for _ in ()).throw(AssertionError("polled")))
    with run_lock(app.store, "news"):
        assert cli.main(["news", "--once"]) == 0
    assert "already running" in capsys.readouterr().out


def test_label_sample_writes_a_sheet_for_pilot_8(app, capsys):
    import pandas as pd

    t = datetime(2026, 10, 19, 10, 0, tzinfo=IST)
    app.store.append_parquet("news", date(2026, 10, 19), pd.DataFrame([
        {"item_id": "a", "story_key": "a", "feed": "rbi_press", "title": "RBI keeps repo rate unchanged",
         "link": "x", "summary": "s", "pub_date": t, "first_seen": t, "price_restatement": False},
        {"item_id": "b", "story_key": "b", "feed": "et_markets", "title": "Sensex tanks 800 points",
         "link": "y", "summary": "s", "pub_date": t, "first_seen": t, "price_restatement": True}]))
    assert cli.main(["label-sample", "--n", "300"]) == 0
    sheet = pd.read_csv(app.store.root / "labels" / "pilot8_headlines.csv", encoding="utf-8-sig")
    assert list(sheet["title"]) == ["RBI keeps repo rate unchanged"]
    assert "1 headlines" in capsys.readouterr().out


def test_backfill_refuses_a_second_copy(app, angel_env, monkeypatch, capsys):
    """Two history backfills would fetch and store the same chunks; the nightly job must not overlap a long run."""
    from quantdesk.recorder.live import run_lock

    monkeypatch.setattr(cli, "run_backfill", lambda *a, **k: (_ for _ in ()).throw(AssertionError("ran twice")))
    monkeypatch.setattr(cli, "default_targets", lambda *a, **k: [])
    with run_lock(app.store, "backfill-history"):
        assert cli.main(["backfill", "--what", "history"]) == 0
    assert "already running" in capsys.readouterr().out
