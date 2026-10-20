"""Market-hours recorder: subscribes to the planned tokens and writes 1-minute data.

Storage kinds: bars, option_snapshots, depth, opening_ticks, recorder_events.
"""

import contextlib
import os
import sys
import threading
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

import pandas as pd

from quantdesk.clock import IST
from quantdesk.recorder.bars import MinuteAggregator
from quantdesk.recorder.plan import plan_subscriptions, recenter
from quantdesk.storage import Store

LOOP_STEP_S = 1.0
FLUSH_GRACE_S = 2.0
RECENTER_EVERY_S = 60.0


class AlreadyRunningError(RuntimeError):
    pass


@dataclass
class RecordingSummary:
    status: str
    minutes_written: int = 0
    dropped: dict = field(default_factory=dict)
    zero_quotes: int = 0
    crossed: int = 0
    stale_periods: list = field(default_factory=list)
    recenter_events: int = 0
    subscription_count: int = 0
    reduced: bool = False


def pid_alive(pid: int) -> bool:
    """True if a process with this PID is running. Never sends a signal on Windows."""
    if pid <= 0:
        return False
    if sys.platform == "win32":
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
            return code.value == 259  # STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


@contextlib.contextmanager
def run_lock(store: Store, name: str = "record"):
    path = store.root / "run" / f"{name}.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            other = int(path.read_text().strip() or 0)
        except ValueError:
            other = 0
        if other != os.getpid() and pid_alive(other):
            raise AlreadyRunningError(f"{name} already running (pid {other})")
        if other == os.getpid():
            raise AlreadyRunningError(f"{name} already running in this process")
        path.unlink()
    path.write_text(str(os.getpid()))
    try:
        yield path
    finally:
        with contextlib.suppress(FileNotFoundError):
            path.unlink()


def _at(day: date, hhmm: str) -> datetime:
    hh, mm = map(int, hhmm.split(":"))
    return datetime.combine(day, time(hh, mm), tzinfo=IST)


def run_recording(day: date, *, client, stream_factory, master: pd.DataFrame, constituents: dict,
                  store: Store, clock, sleep, is_trading_day, settings: dict) -> RecordingSummary:
    if not is_trading_day(day):
        return RecordingSummary(status="holiday")

    with run_lock(store):
        open_t = _at(day, settings["session"]["open"])
        close_t = _at(day, settings["session"]["close"])
        rec = settings["recorder"]
        opening_start, opening_end = (_at(day, t).time() for t in rec["opening_ticks"])

        if clock.now() >= close_t:
            return RecordingSummary(status="no_session")
        wait = (open_t + timedelta(seconds=5) - clock.now()).total_seconds()
        if wait > 0:
            sleep(wait)

        index_specs = settings["angel"]["index_tokens"]
        try:
            spots = {u: client.ltp(index_specs[u]["exchange"], index_specs[u]["symbol"], index_specs[u]["token"])
                     for u in ("NIFTY", "SENSEX")}
        except Exception:  # noqa: BLE001 - no usable session means nothing to record
            return RecordingSummary(status="no_session")
        spot_token = {index_specs[u]["token"]: u for u in ("NIFTY", "SENSEX")}

        plan = plan_subscriptions(master, spots, day, constituents, settings)
        option_tokens = set(plan.option_meta["token"])
        agg = MinuteAggregator(option_tokens=option_tokens, depth_tokens=plan.depth_tokens,
                               index_tokens=plan.index_tokens)
        summary = RecordingSummary(status="ok", subscription_count=plan.count(), reduced=plan.reduced)
        lock = threading.Lock()
        opening_rows: list[dict] = []
        events: list[dict] = [{"event": "subscribed", "time": clock.now(), "count": plan.count(),
                               "reduced": plan.reduced, "width": plan.width}]
        stale_open: dict = {"since": None}

        def on_tick(tick):
            with lock:
                if stale_open["since"] is not None:
                    period = (stale_open["since"], tick.exchange_ts)
                    summary.stale_periods.append(period)
                    events.append({"event": "stale", "time": tick.exchange_ts,
                                   "start": period[0], "end": period[1]})
                    stale_open["since"] = None
                if tick.token in spot_token and tick.ltp > 0:
                    spots[spot_token[tick.token]] = tick.ltp
                if agg.add(tick) is None and tick.token in option_tokens \
                        and opening_start <= tick.exchange_ts.time() < opening_end:
                    opening_rows.append({"token": tick.token, "ltp": tick.ltp, "bid": tick.bid,
                                         "bid_qty": tick.bid_qty, "ask": tick.ask, "ask_qty": tick.ask_qty,
                                         "volume": tick.volume, "oi": tick.oi,
                                         "exchange_ts": tick.exchange_ts, "received_at": tick.received_at})

        def on_stale(since, now):
            with lock:
                if stale_open["since"] is None:
                    stale_open["since"] = since

        stream = stream_factory(on_tick, on_stale)
        stream.subscribe(plan.tokens)
        stream.start()

        def write(kind, rows_or_frame):
            frame = rows_or_frame if isinstance(rows_or_frame, pd.DataFrame) else pd.DataFrame(rows_or_frame)
            if not frame.empty:
                store.append_parquet(kind, day, frame)

        def flush(minute_end):
            with lock:
                result = agg.flush(minute_end)
                opening = list(opening_rows)
                opening_rows.clear()
                pending_events = list(events)
                events.clear()
            write("bars", result.bars)
            write("option_snapshots", result.snapshots)
            write("depth", result.depth)
            write("opening_ticks", opening)
            write("recorder_events", pending_events)
            if not result.bars.empty:
                summary.minutes_written += result.bars["minute"].nunique()
            for reason, n in result.dropped.items():
                summary.dropped[reason] = summary.dropped.get(reason, 0) + n
            summary.zero_quotes += result.zero_quotes
            summary.crossed += result.crossed

        now = clock.now()
        next_minute = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
        last_recenter = now
        try:
            while next_minute <= close_t:
                sleep(LOOP_STEP_S)
                stream.check_stale()
                now = clock.now()
                if (now - last_recenter).total_seconds() >= RECENTER_EVERY_S:
                    last_recenter = now
                    plan, added = recenter(plan, dict(spots), master, settings)
                    if added:
                        new_options = set(plan.option_meta["token"]) - option_tokens
                        option_tokens |= new_options
                        with lock:
                            agg.add_tokens(option_tokens=new_options, depth_tokens=plan.depth_tokens)
                            events.append({"event": "recenter", "time": now,
                                           "count": sum(len(v) for v in added.values())})
                        stream.add_tokens(added)
                        summary.recenter_events += 1
                if now >= next_minute + timedelta(seconds=FLUSH_GRACE_S):
                    flush(next_minute)
                    next_minute += timedelta(minutes=1)
        finally:
            stream.close()
            with lock:
                if stale_open["since"] is not None:
                    period = (stale_open["since"], clock.now())
                    summary.stale_periods.append(period)
                    events.append({"event": "stale", "time": period[1], "start": period[0], "end": period[1]})
            flush(min(next_minute, close_t))  # never write minutes at or after the close
        return summary
