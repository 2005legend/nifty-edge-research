from datetime import datetime

import pytest

from quantdesk.clock import IST
from quantdesk.net.http import PoliteSession, looks_like_html
from quantdesk.net.ratelimit import MultiWindowLimiter, retry
from tests.fakes import FakeClock, FakeHttp, FakeSleep

START = datetime(2026, 10, 20, 9, 0, tzinfo=IST)


def test_limiter_spaces_calls_below_3_per_second():
    clock = FakeClock(START)
    sleep = FakeSleep(clock)
    limiter = MultiWindowLimiter([(3, 1.0)], clock=clock, sleep=sleep)
    for _ in range(10):
        limiter.acquire()
    elapsed = (clock.now() - START).total_seconds()
    assert elapsed >= 4.0


def test_retry_backoff_sequence():
    clock = FakeClock(START)
    sleep = FakeSleep(clock)
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        if calls["n"] <= 3:
            raise ValueError("boom")
        return 7

    result = retry(fn, attempts=5, base_delay=1, max_delay=4,
                   retry_on=lambda e: isinstance(e, ValueError), sleep=sleep)
    assert result == 7
    assert sleep.calls == [1, 2, 4]


def test_retry_gives_up_and_reraises():
    clock = FakeClock(START)
    sleep = FakeSleep(clock)

    def fn():
        raise ValueError("always")

    with pytest.raises(ValueError, match="always"):
        retry(fn, attempts=3, base_delay=1, max_delay=4,
              retry_on=lambda e: True, sleep=sleep)
    assert sleep.calls == [1, 2]


def test_retry_does_not_retry_unlisted_errors():
    clock = FakeClock(START)
    sleep = FakeSleep(clock)

    def fn():
        raise KeyError("no")

    with pytest.raises(KeyError):
        retry(fn, attempts=3, base_delay=1, max_delay=4,
              retry_on=lambda e: isinstance(e, ValueError), sleep=sleep)
    assert sleep.calls == []


def test_polite_session_min_interval():
    clock = FakeClock(START)
    sleep = FakeSleep(clock)
    http = FakeHttp({"https://x/a": (200, b"a"), "https://x/b": (200, b"b")}, clock=clock)
    session = PoliteSession({"User-Agent": "test"}, min_interval_s=1.5,
                            clock=clock, sleep=sleep, http=http)
    session.get("https://x/a")
    session.get("https://x/b")
    gap = (http.request_times[1] - http.request_times[0]).total_seconds()
    assert gap >= 1.5


def test_looks_like_html_detects_block_page():
    assert looks_like_html(b"\r\n<!DOCTYPE html><html>Access Denied") is True
    assert looks_like_html(b"PK\x03\x04") is False
    assert looks_like_html(b"TradDt,BizDt") is False
