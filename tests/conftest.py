import pytest

import quantdesk.config as config


@pytest.fixture(autouse=True)
def _no_real_env_file(monkeypatch):
    """Tests must never read the owner's real .env secrets."""
    monkeypatch.setattr(config, "_load_env_file", lambda: None)
