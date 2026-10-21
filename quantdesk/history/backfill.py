"""Resumable historical candle backfill from Angel One.

Writes kind `history_<interval>` (e.g. history_one_minute) with a `target` column, and a
manifest of JSON lines at data/state/history_manifest.jsonl recording every chunk's status
(older runs wrote data/raw/history/manifest.jsonl, which is still read).
Consumers de-duplicate on (target, ts): a re-run re-fetches the open-ended last chunk.
"""

import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

import pandas as pd

from quantdesk.broker.angel import chunk_ranges
from quantdesk.clock import IST
from quantdesk.instruments import UNDERLYING_SEGMENTS, current_future
from quantdesk.storage import Store

FUTURES_LOOKBACK_DAYS = 95
# getCandleData returns at most 8,000 candles and drops the oldest beyond that: a 30-day one-minute chunk with
# 22 trading days (8,250 minutes) lost its first 250 (150 of the first 1,329 chunks, found 21 Oct 2026).
MAX_CANDLES = 8000


@dataclass(frozen=True)
class Target:
    name: str
    exchange: str
    token: str
    interval: str
    start: date


@dataclass
class BackfillReport:
    chunks_done: int = 0
    chunks_skipped: int = 0
    errors: int = 0
    rows: int = 0


def default_targets(master, constituents: dict[str, str], settings: dict, today: date) -> list[Target]:
    minute_start = date.fromisoformat(settings["backfill"]["minute_start"])
    daily_start = date.fromisoformat(settings["backfill"]["daily_start"])
    indices = settings["angel"]["index_tokens"]
    targets = [Target(name, spec["exchange"], spec["token"], "ONE_MINUTE", minute_start)
               for name, spec in indices.items()]
    targets += [Target(symbol, "NSE", token, "ONE_MINUTE", minute_start) for symbol, token in constituents.items()]
    targets += [Target(name, spec["exchange"], spec["token"], "ONE_DAY", daily_start)
                for name, spec in indices.items()]
    for underlying, (segment, _) in UNDERLYING_SEGMENTS.items():
        future = current_future(master, underlying, today)
        targets.append(Target(future["symbol"], segment, future["token"], "ONE_MINUTE",
                              today - timedelta(days=FUTURES_LOOKBACK_DAYS)))
    return targets


def _manifest_path(store: Store):
    return store.root / "state" / "history_manifest.jsonl"  # data/raw is never edited


def _legacy_manifest_path(store: Store):
    return store.root / "raw" / "history" / "manifest.jsonl"  # read-only, written by versions before 21 Oct 2026


def _load_done(store: Store) -> dict[tuple, str]:
    """(target, interval, chunk_start) -> latest chunk_end iso for chunks with status ok/empty."""
    done: dict[tuple, str] = {}
    lines: list[str] = []
    for path in (_legacy_manifest_path(store), _manifest_path(store)):  # oldest first, so newer rows win
        if path.exists():
            lines += path.read_text(encoding="utf-8").splitlines()
    for line in lines:
        row = json.loads(line)
        key = (row["target"], row["interval"], row["chunk_start"])
        cut = row.get("rows", 0) >= MAX_CANDLES and "pieces" not in row  # stored by a run before the split
        if row["status"] in ("ok", "empty") and not cut:
            done[key] = max(done.get(key, ""), row["chunk_end"])
        else:
            done.pop(key, None)
    return done


def _append_manifest(store: Store, row: dict) -> None:
    path = _manifest_path(store)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def _fetch(client, target: Target, start: datetime, end: datetime) -> tuple[pd.DataFrame | None, int]:
    """Candles for [start, end] and the number of requests that made them; a reply at the cap is split in two."""
    frame = client.candles(target.exchange, target.token, target.interval, start, end)
    if frame is None or len(frame) < MAX_CANDLES or start.date() == end.date():
        return frame, 1
    middle = start.date() + (end.date() - start.date()) // 2
    first, n1 = _fetch(client, target, start, datetime.combine(middle, time(23, 59), tzinfo=start.tzinfo))
    second, n2 = _fetch(client, target, datetime.combine(middle + timedelta(days=1), time(0, 0), tzinfo=start.tzinfo), end)
    parts = [f for f in (first, second) if f is not None and not f.empty]
    return (pd.concat(parts, ignore_index=True) if parts else first), n1 + n2


def run_backfill(targets: list[Target], client, store: Store, clock, settings: dict) -> BackfillReport:
    report = BackfillReport()
    done = _load_done(store)
    end = clock.now()
    for target in targets:
        start = datetime.combine(target.start, time(0, 0), tzinfo=IST)
        max_days = settings["angel"]["candle_max_days"][target.interval]
        kind = f"history_{target.interval.lower()}"
        for chunk_start, chunk_end in chunk_ranges(start, end, max_days):
            key = (target.name, target.interval, chunk_start.isoformat())
            if done.get(key, "") >= chunk_end.isoformat():
                report.chunks_skipped += 1
                continue
            row = {"target": target.name, "interval": target.interval,
                   "chunk_start": chunk_start.isoformat(), "chunk_end": chunk_end.isoformat()}
            try:
                frame, pieces = _fetch(client, target, chunk_start, chunk_end)
            except Exception as exc:  # noqa: BLE001 - recorded, run continues
                _append_manifest(store, {**row, "rows": 0, "status": "error", "error": str(exc)[:200]})
                report.errors += 1
                continue
            if frame is None or frame.empty:
                _append_manifest(store, {**row, "rows": 0, "status": "empty", "pieces": pieces})
            else:
                frame = frame.assign(target=target.name)
                store.append_parquet(kind, chunk_start.date(), frame)
                _append_manifest(store, {**row, "rows": len(frame), "status": "ok", "pieces": pieces})
                report.rows += len(frame)
            report.chunks_done += 1
    return report
