import inspect
import re
from datetime import datetime, timedelta

import pandas as pd
import pyotp
import pytest

import quantdesk.broker.angel as angel_module
from quantdesk.broker.angel import AngelApiError, AngelClient, LoginError, chunk_ranges
from quantdesk.clock import IST
from quantdesk.config import load_settings
from quantdesk.net.ratelimit import MultiWindowLimiter
from tests.fakes import FakeClock, FakeSleep, FakeSmartConnect

SECRET = "JBSWY3DPEHPK3PXP"
START = datetime(2026, 10, 20, 8, 50, tzinfo=IST)


def make_client(fake: FakeSmartConnect):
    clock = FakeClock(START)
    sleep = FakeSleep(clock)
    settings = load_settings()
    limiter = MultiWindowLimiter(settings["angel"]["rate_limits"], clock=clock, sleep=sleep)
    client = AngelClient("key", "C123", "1111", SECRET, smart_factory=lambda api_key: fake,
                         limiter=limiter, clock=clock, sleep=sleep, settings=settings)
    return client, clock, sleep


def candle_rows(params):
    start = datetime.strptime(params["fromdate"], "%Y-%m-%d %H:%M")
    rows = []
    for i in range(3):
        ts = (start + timedelta(minutes=i)).strftime("%Y-%m-%dT%H:%M:%S+05:30")
        rows.append([ts, 100 + i, 101 + i, 99 + i, 100.5 + i, 10 * i])
    return {"status": True, "data": rows}


def test_chunk_ranges_30_day_minute_chunks():
    chunks = chunk_ranges(datetime(2026, 1, 1, 0, 0), datetime(2026, 3, 15, 23, 59), 30)
    assert len(chunks) == 3
    assert chunks[0][0] == datetime(2026, 1, 1, 0, 0)
    assert chunks[0][1] == datetime(2026, 1, 30, 23, 59)
    assert chunks[1][0] == datetime(2026, 1, 31, 0, 0)
    assert chunks[-1][1] == datetime(2026, 3, 15, 23, 59)
    for (a_start, a_end), (b_start, _) in zip(chunks, chunks[1:]):
        assert a_end < b_start


def test_login_uses_totp_and_stores_tokens():
    fake = FakeSmartConnect()
    client, clock, _ = make_client(fake)
    client.login()
    client_code, pin, totp = fake.login_calls[0]
    assert (client_code, pin) == ("C123", "1111")
    assert totp == pyotp.TOTP(SECRET).at(clock.now())
    assert client.feed_token == "feed-1"
    assert client.jwt_token == "jwt-1"


def test_login_retries_three_times_then_raises():
    fake = FakeSmartConnect(login_responses=[{"status": False, "message": "bad", "errorcode": "AB1007"}] * 3)
    client, _, _ = make_client(fake)
    with pytest.raises(LoginError):
        client.login()
    assert len(fake.login_calls) == 3


def test_candles_chunked_rate_limited_and_concatenated():
    fake = FakeSmartConnect(candle_responses=[candle_rows] * 3)
    client, _, _ = make_client(fake)
    client.login()
    frame = client.candles("NSE", "99926000", "ONE_MINUTE",
                           datetime(2026, 1, 1, 9, 15, tzinfo=IST), datetime(2026, 3, 6, 15, 30, tzinfo=IST))
    assert len(fake.candle_calls) == 3
    assert list(frame.columns) == ["ts", "open", "high", "low", "close", "volume"]
    assert frame["ts"].is_monotonic_increasing
    assert not frame["ts"].duplicated().any()
    assert str(frame["ts"].dt.tz) == "Asia/Kolkata"
    assert len(frame) == 9


def test_candles_retries_on_rate_error():
    fake = FakeSmartConnect(candle_responses=[
        {"status": False, "message": "exceeding access rate", "errorcode": "AB1004"},
        candle_rows,
    ])
    client, _, sleep = make_client(fake)
    client.login()
    sleeps_before = len(sleep.calls)
    frame = client.candles("NSE", "99926000", "ONE_MINUTE",
                           datetime(2026, 10, 19, 9, 15, tzinfo=IST), datetime(2026, 10, 19, 15, 30, tzinfo=IST))
    assert len(frame) == 3
    assert len(fake.candle_calls) == 2
    assert len(sleep.calls) > sleeps_before


def test_ltp_returns_float():
    fake = FakeSmartConnect(ltp_value=22601.5)
    client, _, _ = make_client(fake)
    client.login()
    assert client.ltp("NSE", "Nifty 50", "99926000") == 22601.5


def test_no_order_methods_exist():
    pattern = re.compile(r"order|place|modify|cancel|gtt", re.I)
    public = [name for name in dir(AngelClient) if not name.startswith("_")]
    assert not [name for name in public if pattern.search(name)]
    source = inspect.getsource(angel_module)
    assert "placeOrder" not in source
    assert "modifyOrder" not in source
    assert "cancelOrder" not in source
