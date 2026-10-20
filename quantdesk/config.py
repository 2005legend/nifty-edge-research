"""Settings (config/settings.yaml) and secrets (.env)."""

import os
from functools import lru_cache
from pathlib import Path

import yaml
from dotenv import load_dotenv


class MissingSecretError(RuntimeError):
    """A required secret is not set. The message names the variable, never a value."""

    def __init__(self, name: str):
        self.name = name
        super().__init__(
            f"Missing secret {name}: copy .env.example to .env and fill it in."
        )


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_settings(path: Path | None = None) -> dict:
    path = path or project_root() / "config" / "settings.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def data_dir() -> Path:
    return project_root() / load_settings()["paths"]["data_dir"]


@lru_cache(maxsize=1)
def _load_env_file() -> None:
    load_dotenv(project_root() / ".env", override=False)


def get_secret(name: str) -> str:
    _load_env_file()
    value = os.environ.get(name, "").strip()
    if not value:
        raise MissingSecretError(name)
    return value
