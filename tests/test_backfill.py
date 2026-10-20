import json
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from quantdesk.broker.angel import AngelApiError
from quantdesk.clock import IST
from quantdesk.config import load_settings
from quantdesk.history.backfill import Target, default_targets, run_backfill
from quantdesk.instruments import load_master
from quantdesk.storage import Store
from tests.fakes import FakeClock

FIXTURE = Path(__file__).parent / "fixtures" / "master_small.json"
NOW = datetime(2026, 10, 20, 18, 0, tzinfo=IST)


class FakeCandleClient:
    def __init__(self, fail_on=None, empty_on=None):
        self.calls = []
        self.fail_on = fail_on or set()
        self.empty_on = empty_on or set()

    def candles(self, exchange, token, interval, start, end):
        self.calls.append((token, interval, start, end))
        index = len(self.calls) - 1
        if index in self.fail_on:
            raise AngelApiError("AB9999", "boom")
        if index in self.empty_on:
            return pd.DataFrame(columns=["ts", "open", "high", "low", "close", "volume"])
        return pd.DataFrame({"ts": [start], "open": [1.0], "high": [1.0], "low": [1.0],
                             "close": [1.0], "volume": [0]})


def small_targets():
    return [Target("NIFTY", "NSE", "99926000", "ONE_MINUTE", date(2026, 7, 1))]


def manifest(store):
    path = store.root / "raw" / "history" / "manifest.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_default_targets_cover_indices_vix_constituents_daily():
    master = load_master(FIXTURE)
    targets = default_targets(master, {"RELIANCE": "2885", "HDFCBANK": "1333", "INFY": "1594"},
                              load_settings(), date(2026, 10, 19))
    minute = [t for t in targets if t.interval == "ONE_MINUTE"]
    daily = [t for t in targets if t.interval == "ONE_DAY"]
    assert len(targets) == 11
    assert {t.name for t in daily} == {"NIFTY", "SENSEX", "INDIAVIX"}
    assert all(t.start == date(2015, 1, 1) for t in daily)
    assert {"NIFTY", "SENSEX", "INDIAVIX", "RELIANCE", "HDFCBANK", "INFY"} <= {t.name for t in minute}
    assert all(t.start == date(2019, 1, 1) for t in minute if t.name in {"NIFTY", "RELIANCE"})
    futures = [t for t in minute if t.exchange in {"NFO", "BFO"}]
    assert len(futures) == 2


def test_resume_skips_ok_chunks(tmp_path):
    store = Store(tmp_path)
    first = FakeCandleClient()
    report1 = run_backfill(small_targets(), first, store, FakeClock(NOW), load_settings())
    total = len(first.calls)
    assert report1.chunks_done == total and total >= 4
    second = FakeCandleClient()
    report2 = run_backfill(small_targets(), second, store, FakeClock(NOW), load_settings())
    assert len(second.calls) == 0
    assert report2.chunks_skipped == total


def test_error_chunk_recorded_and_run_continues(tmp_path):
    store = Store(tmp_path)
    client = FakeCandleClient(fail_on={1})
    report = run_backfill(small_targets(), client, store, FakeClock(NOW), load_settings())
    statuses = [row["status"] for row in manifest(store)]
    assert report.errors == 1
    assert statuses.count("error") == 1
    assert len(client.calls) == len(statuses)
    rerun = FakeCandleClient()
    run_backfill(small_targets(), rerun, store, FakeClock(NOW), load_settings())
    assert len(rerun.calls) == 1  # only the failed chunk is retried


def test_empty_chunk_marked_empty(tmp_path):
    store = Store(tmp_path)
    client = FakeCandleClient(empty_on={0})
    run_backfill(small_targets(), client, store, FakeClock(NOW), load_settings())
    assert manifest(store)[0]["status"] == "empty"
    rows = store.read("history_one_minute")
    assert len(rows) == len(client.calls) - 1
    assert set(rows["target"]) == {"NIFTY"}
