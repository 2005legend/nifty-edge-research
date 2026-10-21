import copy
from datetime import date, datetime
from pathlib import Path

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


INDEX_CLOSE = Path(__file__).parent / "fixtures" / "ind_close_all_sample.csv"
INDEX_URL = "https://nsearchives.nseindia.com/content/indices/ind_close_all_{ddmmyyyy}.csv"


def test_parse_index_close_reads_fundamentals_and_bond_index():
    from quantdesk.macro.sources import parse_index_close

    frame = parse_index_close(INDEX_CLOSE.read_bytes())
    nifty = frame[frame["index_name"] == "Nifty 50"].iloc[0]
    assert nifty["date"] == date(2026, 10, 19)
    assert (nifty["close"], nifty["pe"], nifty["pb"], nifty["div_yield"]) == (22888.95, 19.33, 2.81, 1.5)
    gsec = frame[frame["index_name"] == "Nifty 10 yr Benchmark G-Sec (Clean Price)"].iloc[0]
    assert gsec["close"] == 841.87 and pd.isna(gsec["pe"])


def _index_close_getter(days_with_files, old_name_day=None):
    """Fake http_get: an index file for each day in days_with_files, 404 otherwise."""
    from tests.fakes import FakeResponse

    body = INDEX_CLOSE.read_text()

    def get(url):
        for day in days_with_files:
            if url == INDEX_URL.format(ddmmyyyy=day.strftime("%d%m%Y")):
                text = body.replace("19-10-2026", day.strftime("%d-%m-%Y"))
                if day == old_name_day:
                    text = text.replace("Nifty 50,", "CNX Nifty,")
                return FakeResponse(200, text.encode(), url)
        return FakeResponse(404, b"<!DOCTYPE html>", url)
    return get


def test_fetch_nifty_fundamentals_over_a_range_skips_holidays():
    from quantdesk.macro.sources import fetch_nse_index_close

    spec = {"id": "nifty_fundamentals", "source": "nse_index_close", "url": INDEX_URL,
            "indices": ["Nifty 50", "CNX Nifty"], "fields": "fundamentals"}
    d1, holiday, d2 = date(2015, 3, 2), date(2015, 3, 3), date(2015, 3, 4)
    frame = fetch_nse_index_close(spec, d1, d2, http_get=_index_close_getter([d1, d2], old_name_day=d1))
    assert list(frame["date"]) == [d1, d2]
    assert set(frame["series_id"]) == {"nifty_fundamentals"}
    assert list(frame["pe"]) == [19.33, 19.33]


def test_fetch_gsec_clean_price_as_a_value_series():
    from quantdesk.macro.sources import VALUE_COLUMNS, fetch_nse_index_close

    spec = {"id": "india_gsec10y_price", "source": "nse_index_close", "url": INDEX_URL,
            "indices": ["Nifty 10 yr Benchmark G-Sec (Clean Price)"]}
    day = date(2026, 10, 19)
    frame = fetch_nse_index_close(spec, day, day, http_get=_index_close_getter([day]))
    assert list(frame.columns) == VALUE_COLUMNS
    assert frame.iloc[0].to_dict() == {"series_id": "india_gsec10y_price", "date": day, "value": 841.87}


def test_no_series_uses_fbil():
    """FBIL's terms require a paid subscription for back-testing and risk use (checked 21 Oct 2026)."""
    from quantdesk.config import load_settings

    sources = {s["source"] for s in load_settings()["macro"]["series"]}
    assert "fbil" not in sources and "nse_index_fundamentals" not in sources
    assert "nse_index_close" in sources
