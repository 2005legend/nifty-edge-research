from datetime import date, datetime
from pathlib import Path

import quantdesk.app as app_module
from quantdesk.app import App
from quantdesk.clock import IST
from quantdesk.config import load_settings
from quantdesk.storage import Store
from tests.fakes import FakeClock


def test_master_fallback_is_remembered(tmp_path, monkeypatch):
    """Backlog 7: App.master discarded download_master's fallback flag."""
    copy = tmp_path / "raw" / "instruments" / "2026-10-16" / "OpenAPIScripMaster.json"
    monkeypatch.setattr(app_module, "download_master", lambda store, get, day, url: (copy, True))
    monkeypatch.setattr(app_module, "load_master", lambda path: "MASTER")
    app = App(settings=load_settings(), store=Store(tmp_path), clock=FakeClock(datetime(2026, 10, 19, 9, 0, tzinfo=IST)),
              sleep=lambda s: None, events=[])
    assert app.master(date(2026, 10, 19)) == "MASTER"
    assert "2026-10-16" in app.master_fallback(date(2026, 10, 19))


def test_fresh_master_has_no_fallback_note(tmp_path, monkeypatch):
    path = tmp_path / "raw" / "instruments" / "2026-10-19" / "OpenAPIScripMaster.json"
    monkeypatch.setattr(app_module, "download_master", lambda store, get, day, url: (path, False))
    monkeypatch.setattr(app_module, "load_master", lambda path: "MASTER")
    app = App(settings=load_settings(), store=Store(tmp_path), clock=FakeClock(datetime(2026, 10, 19, 9, 0, tzinfo=IST)),
              sleep=lambda s: None, events=[])
    app.master(date(2026, 10, 19))
    assert app.master_fallback(date(2026, 10, 19)) is None
