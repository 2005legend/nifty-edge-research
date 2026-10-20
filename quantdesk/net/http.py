"""Polite HTTP for NSE/BSE and other public sites."""

import requests

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/129.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
}


class BadDownloadError(RuntimeError):
    """The server answered, but the body is not the expected file (e.g. an HTML block page)."""


def looks_like_html(content: bytes) -> bool:
    head = content[:512].lower().strip()
    return head.startswith(b"<!doctype html") or head.startswith(b"<html") or b"<html" in head


class PoliteSession:
    """Spaces requests at least min_interval_s apart and keeps cookies from a bootstrap page."""

    def __init__(self, headers: dict | None = None, *, min_interval_s: float, clock, sleep, http=None):
        self.http = http if http is not None else requests.Session()
        self.http.headers.update(headers or BROWSER_HEADERS)
        self.min_interval_s = min_interval_s
        self.clock = clock
        self.sleep = sleep
        self._last = None

    def _space(self) -> None:
        if self._last is not None:
            gap = (self.clock.now() - self._last).total_seconds()
            if gap < self.min_interval_s:
                self.sleep(self.min_interval_s - gap)
        self._last = self.clock.now()

    def bootstrap(self, home_url: str) -> None:
        self._space()
        self.http.get(home_url, timeout=30)

    def get(self, url: str, **kwargs):
        self._space()
        kwargs.setdefault("timeout", 30)
        return self.http.get(url, **kwargs)
