"""The Angel One SDK logs request headers and parameters (API key, PIN, JWT) to the console and to
logs/<date>/app.log. Our factories must silence that."""

import json
import os
from pathlib import Path

import requests

from quantdesk.broker.sdk import smart_connect_factory, websocket_factory

SENTINELS = ["APIKEY_SENTINEL", "CLIENT_SENTINEL", "PIN_SENTINEL"]


class FailedLogin:
    status_code = 200
    text = "1.2.3.4"
    content = json.dumps({"status": False, "message": "Invalid totp", "errorcode": "AB1050", "data": None}).encode()

    def json(self):
        return json.loads(self.content)


def test_failed_login_leaks_no_secrets(tmp_path, monkeypatch, capfd):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(requests, "request", lambda *a, **k: FailedLogin())
    monkeypatch.setattr(requests, "get", lambda *a, **k: FailedLogin())
    smart = smart_connect_factory("APIKEY_SENTINEL")
    smart.reqsession = requests
    smart.generateSession("CLIENT_SENTINEL", "PIN_SENTINEL", "123456")
    out, err = capfd.readouterr()
    logged = "".join(p.read_text(encoding="utf-8", errors="replace") for p in Path(tmp_path).rglob("*.log"))
    for secret in SENTINELS:
        assert secret not in out
        assert secret not in err
        assert secret not in logged


def test_websocket_factory_disables_sdk_retry(tmp_path, monkeypatch, capfd):
    monkeypatch.chdir(tmp_path)
    ws = websocket_factory("JWT_SENTINEL", "APIKEY_SENTINEL", "CLIENT_SENTINEL", "FEED_SENTINEL")
    assert ws.MAX_RETRY_ATTEMPT == 0
    out, err = capfd.readouterr()
    assert "JWT_SENTINEL" not in out + err


def test_logs_folder_is_git_ignored():
    from quantdesk.config import project_root

    ignore = (project_root() / ".gitignore").read_text(encoding="utf-8").split()
    assert "logs/" in ignore


def test_factory_closes_the_sdk_log_file(tmp_path, monkeypatch):
    """An unclosed handle keeps logs/<date>/app.log locked on Windows."""
    import gc
    import warnings

    monkeypatch.chdir(tmp_path)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        smart_connect_factory("APIKEY_SENTINEL")
        gc.collect()
    leaks = [w for w in caught if issubclass(w.category, ResourceWarning) and "app.log" in str(w.message)]
    assert leaks == []
