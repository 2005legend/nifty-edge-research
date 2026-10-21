"""Daily data health report, written to data/reports/health/<date>.json."""

from datetime import date, datetime
from pathlib import Path

import pandas as pd

from quantdesk.calendar.events import continuous_session, is_trading_day
from quantdesk.clock import IST
from quantdesk.storage import Store

OK_STATUSES = {"ok", "empty"}


def build_health_report(day: date, *, store: Store, events: list, settings: dict) -> dict:
    trading = is_trading_day(day, events)
    start, end = continuous_session(day, settings["session"])
    span = datetime.combine(day, end) - datetime.combine(day, start)
    expected = int(span.total_seconds() // 60) if trading else 0
    problems: list[str] = []

    bars = store.read("bars", day)
    minutes = {}
    for name, spec in settings["angel"]["index_tokens"].items():
        recorded = _minutes_in_window(bars, spec["token"], start, end)
        minutes[name] = recorded
        if trading and recorded < expected:
            problems.append(f"{name}: {expected - recorded} minutes missing")

    snapshots = store.read("option_snapshots", day)
    recording = store.read_report("recording", day) or {}
    stale_periods = recording.get("stale_periods", [])
    if stale_periods:
        problems.append(f"feed stale periods: {len(stale_periods)}")
    if recording.get("reduced"):
        problems.append("recorder used the reduced strike window")
    problems += [f"recorder: {w}" for w in recording.get("warnings", [])]
    recorder_errors = recording.get("errors", [])
    if recorder_errors:
        problems.append(f"recorder errors: {len(recorder_errors)} (first: {recorder_errors[0]})")

    eod = (store.read_report("eod", day) or {}).get("status", {})
    problems += [f"eod {item}: {status}" for item, status in eod.items() if status not in OK_STATUSES]
    macro = (store.read_report("macro", day) or {}).get("status", {})
    problems += [f"macro {sid}: {status}" for sid, status in macro.items() if status not in OK_STATUSES]
    news = store.read_report("news", day) or {}
    problems += [f"news feed failed: {name}" for name in news.get("failed", [])]
    problems += [f"news feed stale: {name}" for name in news.get("stale", [])]
    backfill = store.read_report("backfill", day) or {}
    if backfill.get("errors"):
        problems.append(f"backfill errors: {backfill['errors']}")

    return {
        "date": day.isoformat(),
        "trading_day": trading,
        "minutes_expected": expected,
        "minutes_recorded": minutes,
        "option_tokens_recorded": int(snapshots["token"].nunique()) if not snapshots.empty else 0,
        "zero_quotes": recording.get("zero_quotes", 0),
        "crossed_quotes": recording.get("crossed", 0),
        "dropped_ticks": recording.get("dropped", {}),
        "stale_periods": stale_periods,
        "recenter_events": recording.get("recenter_events", 0),
        "subscription_count": recording.get("subscription_count", 0),
        "reduced_window": bool(recording.get("reduced", False)),
        "news_items_per_feed": news.get("new_items", {}),
        "stale_feeds": news.get("stale", []),
        "macro_status": macro,
        "eod_status": eod,
        "backfill_progress": {"done": backfill.get("chunks_done", 0), "errors": backfill.get("errors", 0)},
        "problems": problems,
    }


def _minutes_in_window(bars: pd.DataFrame, token: str, start, end) -> int:
    """Distinct bar minutes for `token` within [start, end) IST; bars outside it (the 15:29 close) don't count."""
    if bars.empty:
        return 0
    stamps = pd.to_datetime(bars.loc[bars["token"] == token, "minute"])
    stamps = stamps.dt.tz_localize(IST) if stamps.dt.tz is None else stamps.dt.tz_convert(IST)
    times = stamps.dt.time
    return int(stamps[(times >= start) & (times < end)].nunique())


def write_health_report(report: dict, store: Store) -> Path:
    return store.write_report("health", date.fromisoformat(report["date"]), report)
