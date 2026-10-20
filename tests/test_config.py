import re
from datetime import datetime

import pytest

from quantdesk.clock import IST
from quantdesk.config import MissingSecretError, get_secret, load_settings, project_root
from tests.fakes import FakeClock

SECRET_NAMES = {
    "ANGEL_API_KEY",
    "ANGEL_CLIENT_CODE",
    "ANGEL_PIN",
    "ANGEL_TOTP_SECRET",
    "FRED_API_KEY",
    "GROQ_API_KEY",
}


def test_load_settings_reads_session_minutes():
    assert load_settings()["session"]["minutes"] == 375


def test_get_secret_missing_raises_with_name_only(monkeypatch):
    monkeypatch.delenv("ANGEL_PIN", raising=False)
    with pytest.raises(MissingSecretError, match="ANGEL_PIN"):
        get_secret("ANGEL_PIN")
    monkeypatch.setenv("ANGEL_PIN", "9999")
    assert "9999" not in str(MissingSecretError("ANGEL_PIN"))


def test_env_example_lists_all_secret_names_without_values():
    lines = [
        line.strip()
        for line in (project_root() / ".env.example").read_text().splitlines()
        if line.strip()
    ]
    assert all(re.fullmatch(r"[A-Z_]+=", line) for line in lines)
    assert {line[:-1] for line in lines} == SECRET_NAMES


def test_fake_clock_is_ist():
    clock = FakeClock(datetime(2026, 10, 20, 9, 15, tzinfo=IST))
    clock.advance(60)
    assert clock.now().minute == 16
    assert clock.now().tzinfo == IST
