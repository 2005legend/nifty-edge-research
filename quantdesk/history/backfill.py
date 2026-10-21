"""Resumable historical candle backfill from Angel One.

Writes kind `history_<interval>` (e.g. history_one_minute) with a `target` column, and a
manifest of JSON lines at data/state/history_manifest.jsonl recording every chunk's status
(older runs wrote data/raw/history/manifest.jsonl, which is still read).
Consumers de-duplicate on (target, ts): a re-run re-fetches the open-ended last chunk.
"""

import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from quantdesk.broker.angel import chunk_ranges
from quantdesk.clock import IST
from quantdesk.instruments import UNDERLYING_SEGMENTS, current_future
from quantdesk.storage import Store

FUTURES_LOOKBACK_DAYS = 95


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
        if row["status"] in ("ok", "empty"):
            done[key] = max(done.get(key, ""), row["chunk_end"])
        else:
            done.pop(key, None)
    return done


def _append_manifest(store: Store, row: dict) -> None:
    path = _manifest_path(store)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


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
                frame = client.candles(target.exchange, target.token, target.interval, chunk_start, chunk_end)
            except Exception as exc:  # noqa: BLE001 - recorded, run continues
                _append_manifest(store, {**row, "rows": 0, "status": "error", "error": str(exc)[:200]})
                report.errors += 1
                continue
            if frame is None or frame.empty:
                _append_manifest(store, {**row, "rows": 0, "status": "empty"})
            else:
                frame = frame.assign(target=target.name)
                store.append_parquet(kind, chunk_start.date(), frame)
                _append_manifest(store, {**row, "rows": len(frame), "status": "ok"})
                report.rows += len(frame)
            report.chunks_done += 1
    return report
