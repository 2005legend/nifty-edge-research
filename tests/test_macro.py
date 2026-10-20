import copy
from datetime import date, datetime

import pandas as pd

from quantdesk.clock import IST
from quantdesk.config import load_settings
from quantdesk.macro.collect import run_macro_daily, run_macro_intraday
from quantdesk.macro.sources import normalize_yf
from quantdesk.storage import Store

DAY = date(2026, 10, 19)


def settings_with(series):
    settings = copy.deepcopy(load_settings())
    settings["macro"]["series"] = series
    return settings


def fake_frame(spec, start, end):
    return pd.DataFrame({"series_id": [spec["id"]] * 2, "date": [date(2026, 10, 16), DAY], "value": [1.0, 2.0]})


def test_daily_run_writes_rows_and_status_ok(tmp_path):
    series = [{"id": f"s{i}", "source": "fake"} for i in range(3)]
    store = Store(tmp_path)
    report = run_macro_daily(DAY, store=store, fetchers={"fake": fake_frame}, settings=settings_with(series),
                             sleep=lambda s: None)
    assert report.status == {"s0": "ok", "s1": "ok", "s2": "ok"}
    assert set(store.read("macro_daily")["series_id"]) == {"s0", "s1", "s2"}


def test_failing_series_retried_twice_then_failed_others_continue(tmp_path):
    calls = {"n": 0}

    def broken(spec, start, end):
        calls["n"] += 1
        raise ConnectionError("down")

    series = [{"id": "bad", "source": "broken"}, {"id": "good", "source": "fake"}]
    report = run_macro_daily(DAY, store=Store(tmp_path), fetchers={"broken": broken, "fake": fake_frame},
                             settings=settings_with(series), sleep=lambda s: None)
    assert report.status == {"bad": "failed", "good": "ok"}
    assert calls["n"] == 3


def test_fred_series_missing_key_marked(tmp_path, monkeypatch):
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    called = []

    def fred(spec, start, end):
        called.append(spec)
        return fake_frame(spec, start, end)

    series = [{"id": "dgs10", "source": "openbb_fred", "symbol": "DGS10"}]
    report = run_macro_daily(DAY, store=Store(tmp_path), fetchers={"openbb_fred": fred},
                             settings=settings_with(series), sleep=lambda s: None)
    assert report.status == {"dgs10": "missing_key"}
    assert called == []


def test_calendar_and_fundamentals_go_to_their_own_kinds(tmp_path):
    def calendar(spec, start, end):
        return pd.DataFrame({"series_id": ["econ_calendar"], "date": [DAY], "event": ["CPI"]})

    series = [{"id": "econ_calendar", "source": "cal"}, {"id": "nifty_fundamentals", "source": "fake"}]
    store = Store(tmp_path)
    run_macro_daily(DAY, store=store, fetchers={"cal": calendar, "fake": fake_frame},
                    settings=settings_with(series), sleep=lambda s: None)
    assert len(store.read("econ_calendar")) == 1
    assert len(store.read("index_fundamentals")) == 2
    assert store.read("macro_daily").empty


def test_series_lookback_overrides_default(tmp_path):
    starts = {}

    def record(spec, start, end):
        starts[spec["id"]] = start
        return fake_frame(spec, start, end)

    series = [{"id": "daily", "source": "rec"}, {"id": "monthly", "source": "rec", "lookback_days": 400}]
    run_macro_daily(DAY, store=Store(tmp_path), fetchers={"rec": record}, settings=settings_with(series),
                    sleep=lambda s: None)
    assert starts["daily"] == date(2026, 10, 9)
    assert starts["monthly"] == date(2025, 9, 14)


def test_yfinance_normaliser_converts_index_to_ist_date():
    index = pd.DatetimeIndex([datetime(2026, 10, 18, 20, 0), datetime(2026, 10, 19, 20, 0)], tz="UTC")
    frame = pd.DataFrame({"Close": [100.0, 101.0], "Open": [99.0, 100.0]}, index=index)
    out = normalize_yf(frame, "brent")
    assert list(out.columns) == ["series_id", "date", "value"]
    assert list(out["date"]) == [date(2026, 10, 19), date(2026, 10, 20)]
    assert list(out["value"]) == [100.0, 101.0]


def test_intraday_writes_only_configured_tickers(tmp_path):
    seen = {}

    def fetch_intraday(tickers, now):
        seen["tickers"] = list(tickers)
        rows = [{"ticker": t, "ts": now, "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 0}
                for t in tickers]
        return pd.DataFrame(rows)

    settings = load_settings()
    store = Store(tmp_path)
    report = run_macro_intraday(datetime(2026, 10, 19, 10, 0, tzinfo=IST), store=store,
                                fetch_intraday=fetch_intraday, settings=settings)
    assert seen["tickers"] == settings["macro"]["intraday_tickers"]
    assert set(store.read("macro_intraday")["ticker"]) == set(settings["macro"]["intraday_tickers"])
    assert all(v == "ok" for v in report.status.values())
