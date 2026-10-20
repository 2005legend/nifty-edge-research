"""Dated market events and trading days. Every event must cite an https source_url."""

from dataclasses import dataclass
from datetime import date, time, timedelta
from pathlib import Path

import yaml

EVENT_TYPES = {"rbi_mpc", "budget", "election_results", "us_fomc", "us_cpi", "us_nfp",
               "index_rebalance", "results", "holiday_nse", "holiday_bse"}
GATES = {"E0", "E1", "E2", "E3"}


class EventValidationError(ValueError):
    pass


@dataclass(frozen=True)
class Event:
    date: date
    time: time | None
    type: str
    gate: str
    title: str
    source_url: str


def load_events(path: Path) -> list[Event]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    events, errors = [], []
    for i, entry in enumerate(raw.get("events") or []):
        label = f"entry {i + 1} '{entry.get('title', '?')}'"
        problems = []
        try:
            day = date.fromisoformat(str(entry.get("date")))
        except ValueError:
            problems.append(f"bad date {entry.get('date')!r}")
            day = None
        if entry.get("type") not in EVENT_TYPES:
            problems.append(f"unknown type {entry.get('type')!r}")
        if entry.get("gate") not in GATES:
            problems.append(f"unknown gate {entry.get('gate')!r}")
        url = str(entry.get("source_url") or "")
        if not url.startswith("https://"):
            problems.append("missing or non-https source_url")
        at = None
        if entry.get("time"):
            try:
                at = time.fromisoformat(str(entry["time"]))
            except ValueError:
                problems.append(f"bad time {entry.get('time')!r}")
        if problems:
            errors.append(f"{label}: " + "; ".join(problems))
            continue
        events.append(Event(day, at, entry["type"], entry["gate"], entry.get("title", ""), url))
    if errors:
        raise EventValidationError("Invalid events:\n" + "\n".join(errors))
    return events


def _holidays(events: list[Event], exchange: str, year: int) -> set[date]:
    nse = {e.date for e in events if e.type == "holiday_nse"}
    if exchange == "NSE":
        return nse
    bse = {e.date for e in events if e.type == "holiday_bse"}
    # BSE and NSE follow the same exchange holiday list; use NSE's when BSE has none for the year.
    return bse if any(d.year == year for d in bse) else nse


def is_trading_day(day: date, events: list[Event], exchange: str = "NSE") -> bool:
    return day.weekday() < 5 and day not in _holidays(events, exchange, day.year)


def trading_days(start: date, end: date, events: list[Event],
                 history_days: set[date] | None = None, exchange: str = "NSE") -> list[date]:
    days, cursor = [], start
    while cursor <= end:
        if history_days is not None and cursor <= max(history_days, default=cursor):
            if cursor in history_days:
                days.append(cursor)
        elif is_trading_day(cursor, events, exchange):
            days.append(cursor)
        cursor += timedelta(days=1)
    return days


def events_on(day: date, events: list[Event]) -> list[Event]:
    return [e for e in events if e.date == day]
