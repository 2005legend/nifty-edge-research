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
    path = store.root / "state" / "history_manifest.jsonl"  # data/raw is never edited (backlog 12)
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


def test_progress_in_the_old_raw_location_is_still_honoured(tmp_path):
    """Backlog 12: the manifest moved to data/state; chunks a run recorded under data/raw stay done."""
    store = Store(tmp_path)
    first = FakeCandleClient()
    run_backfill(small_targets(), first, store, FakeClock(NOW), load_settings())
    new_path = tmp_path / "state" / "history_manifest.jsonl"
    old_path = tmp_path / "raw" / "history" / "manifest.jsonl"
    old_path.parent.mkdir(parents=True, exist_ok=True)
    new_path.replace(old_path)  # as if an older version had written it
    second = FakeCandleClient()
    report = run_backfill(small_targets(), second, store, FakeClock(NOW), load_settings())
    assert second.calls == []
    assert report.chunks_skipped == len(first.calls)


class CappedCandleClient:
    """Angel One's getCandleData: 375 one-minute candles per weekday, and at most 8,000 per reply,
    keeping the newest (seen on 150 of the first 1,329 chunks, 21 Oct 2026)."""

    def __init__(self):
        self.calls = []

    def candles(self, exchange, token, interval, start, end):
        self.calls.append((start, end))
        days = pd.bdate_range(start.date(), end.date())
        ts = [datetime.combine(d.date(), datetime.min.time(), tzinfo=IST) + timedelta(minutes=555 + m)
              for d in days for m in range(375)]
        ts = [t for t in ts if start <= t <= end][-8000:]
        return pd.DataFrame({"ts": ts, "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 0})


CAPPED_NOW = datetime(2025, 1, 28, 23, 59, tzinfo=IST)  # 30 Dec 2024 - 28 Jan 2025: 22 weekdays, 8,250 minutes


def capped_target():
    return [Target("CIPLA", "NSE", "694", "ONE_MINUTE", date(2024, 12, 30))]


def test_a_reply_at_the_candle_cap_is_split_until_nothing_is_cut(tmp_path):
    store = Store(tmp_path)
    run_backfill(capped_target(), CappedCandleClient(), store, FakeClock(CAPPED_NOW), load_settings())
    stored = store.read("history_one_minute")
    assert stored["ts"].nunique() == 22 * 375
    assert (stored["ts"].dt.date == date(2024, 12, 30)).sum() == 375  # the day Angel drops first
    row = manifest(store)[-1]
    assert (row["rows"], row["status"], row["pieces"]) == (8250, "ok", 2)


def test_chunks_cut_at_the_cap_by_an_older_run_are_fetched_again(tmp_path):
    store = Store(tmp_path)
    path = store.root / "state" / "history_manifest.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"target": "CIPLA", "interval": "ONE_MINUTE",
                                "chunk_start": "2024-12-30T00:00:00+05:30", "chunk_end": "2025-01-28T23:59:00+05:30",
                                "rows": 8000, "status": "ok"}) + "\n")
    client = CappedCandleClient()
    report = run_backfill(capped_target(), client, store, FakeClock(CAPPED_NOW), load_settings())
    assert report.chunks_skipped == 0 and len(client.calls) == 3  # the full chunk, then its two halves
    second = run_backfill(capped_target(), CappedCandleClient(), store, FakeClock(CAPPED_NOW), load_settings())
    assert second.chunks_skipped == 1
