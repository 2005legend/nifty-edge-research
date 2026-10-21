from datetime import date, datetime, timedelta

import pandas as pd

from quantdesk.calendar.events import Event
from quantdesk.clock import IST
from quantdesk.config import load_settings
from quantdesk.quality import build_health_report, write_health_report
from quantdesk.storage import Store

DAY = date(2026, 10, 19)
SETTINGS = load_settings()
TOKENS = {"NIFTY": "99926000", "SENSEX": "99919000", "INDIAVIX": "99926017"}


def write_bars(store, minutes_by_name, day=DAY, extra=()):
    """`minutes` consecutive bars from 09:15, plus bars at each (hour, minute) in `extra`."""
    rows = []
    start = datetime(day.year, day.month, day.day, 9, 15, tzinfo=IST)
    for name, minutes in minutes_by_name.items():
        stamps = [start + timedelta(minutes=i) for i in range(minutes)]
        stamps += [datetime(day.year, day.month, day.day, h, m, tzinfo=IST) for h, m in extra]
        for stamp in stamps:
            rows.append({"minute": stamp, "token": TOKENS[name], "open": 1.0,
                         "high": 1.0, "low": 1.0, "close": 1.0, "volume": None, "n_ticks": 5})
    store.append_parquet("bars", day, pd.DataFrame(rows))


def full_day(store):
    """A day after 3 Aug 2026: no index bars during the 15:15 closing auction, then a 15:29 close bar."""
    write_bars(store, {"NIFTY": 360, "SENSEX": 360, "INDIAVIX": 360}, extra=[(15, 29)])
    store.write_report("recording", DAY, {"status": "ok", "stale_periods": [], "recenter_events": 1,
                                          "subscription_count": 310, "reduced": False, "dropped": {},
                                          "zero_quotes": 3, "crossed": 0, "minutes_written": 361})


def test_full_day_no_problems(tmp_path):
    store = Store(tmp_path)
    full_day(store)
    report = build_health_report(DAY, store=store, events=[], settings=SETTINGS)
    assert report["trading_day"] is True
    assert report["minutes_expected"] == 360
    assert report["minutes_recorded"]["NIFTY"] == 360
    assert report["problems"] == []
    path = write_health_report(report, store)
    assert store.read_report("health", DAY)["minutes_expected"] == 360
    assert path.exists()


def test_missing_minutes_reported(tmp_path):
    store = Store(tmp_path)
    write_bars(store, {"NIFTY": 350, "SENSEX": 360, "INDIAVIX": 360}, extra=[(15, 29)])
    report = build_health_report(DAY, store=store, events=[], settings=SETTINGS)
    assert report["problems"] == ["NIFTY: 10 minutes missing"]


def test_day_before_closing_auction_expects_full_375(tmp_path):
    day = date(2026, 7, 31)
    store = Store(tmp_path)
    write_bars(store, {"NIFTY": 370, "SENSEX": 375, "INDIAVIX": 375}, day=day)
    report = build_health_report(day, store=store, events=[], settings=SETTINGS)
    assert report["minutes_expected"] == 375
    assert report["problems"] == ["NIFTY: 5 minutes missing"]


def test_holiday_report_expects_zero_minutes(tmp_path):
    holiday = Event(DAY, None, "holiday_nse", "E3", "Test holiday", "https://x")
    report = build_health_report(DAY, store=Store(tmp_path), events=[holiday], settings=SETTINGS)
    assert report["trading_day"] is False
    assert report["minutes_expected"] == 0
    assert not any("missing" in p for p in report["problems"])


def test_eod_and_macro_failures_listed(tmp_path):
    store = Store(tmp_path)
    full_day(store)
    store.write_report("eod", DAY, {"status": {"nse_fo": "ok", "participant_oi": "not_published"}})
    store.write_report("macro", DAY, {"status": {"brent": "ok", "dgs10": "failed"}})
    store.write_report("news", DAY, {"new_items": {"et_markets": 40}, "failed": [], "stale": ["bse_notices"]})
    report = build_health_report(DAY, store=store, events=[], settings=SETTINGS)
    assert "eod participant_oi: not_published" in report["problems"]
    assert "macro dgs10: failed" in report["problems"]
    assert "news feed stale: bse_notices" in report["problems"]
    assert report["news_items_per_feed"] == {"et_markets": 40}
