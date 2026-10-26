"""Market-hours recorder: subscribes to the planned tokens and writes 1-minute data.

Storage kinds: bars, option_snapshots, depth, opening_ticks, option_meta, recorder_events.
"""

import contextlib
import json
import os
import threading
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

import pandas as pd

from quantdesk.clock import IST
from quantdesk.recorder.bars import MinuteAggregator
from quantdesk.recorder.plan import plan_subscriptions, recenter
from quantdesk.storage import Store

LOOP_STEP_S = 1.0
FLUSH_GRACE_S = 1.0          # flush minute M once the feed's exchange time passes M+1 by this much
PC_FALLBACK_GRACE_S = 10.0   # ...or once the PC clock passes M+1 by this much (quiet feed)
RECENTER_EVERY_S = 60.0
RECONNECT_EVERY_S = 60.0  # while the feed stays silent in session, force a fresh connection this often


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
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)  # degraded but recording, e.g. an older instrument master


LOCK_OFFSET = 4096  # the lock sits past the PID text: on Windows a locked byte cannot be read


@contextlib.contextmanager
def run_lock(store: Store, name: str = "record"):
    """One running copy per job. The OS lock dies with its process, so a crash, a reboot or a reused PID
    never blocks the next run. The file holds the owner's PID for the error message."""
    import msvcrt

    path = store.root / "run" / f"{name}.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(path, "a+b")  # "a+" never truncates a live owner's PID
    fd = handle.fileno()
    try:
        handle.seek(LOCK_OFFSET)
        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
    except OSError:
        os.lseek(fd, 0, os.SEEK_SET)
        other = os.read(fd, 32).decode("ascii", "replace").strip() or "?"  # unbuffered: stops short of the lock
        handle.close()
        raise AlreadyRunningError(f"{name} already running (pid {other})") from None
    try:
        handle.seek(0)
        handle.truncate()
        handle.write(str(os.getpid()).encode("ascii"))
        handle.flush()
        yield path
    finally:
        handle.seek(LOCK_OFFSET)
        with contextlib.suppress(OSError):
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        handle.close()
        with contextlib.suppress(OSError):
            path.unlink()


def _at(day: date, hhmm: str) -> datetime:
    hh, mm = map(int, hhmm.split(":"))
    return datetime.combine(day, time(hh, mm), tzinfo=IST)


def run_recording(day: date, *, client, stream_factory, master: pd.DataFrame, constituents: dict,
                  store: Store, clock, sleep, is_trading_day, settings: dict) -> RecordingSummary:
    if not is_trading_day(day):
        return RecordingSummary(status="holiday")

    with run_lock(store):
        rec = settings["recorder"]
        open_t = _at(day, settings["session"]["open"])
        close_t = _at(day, settings["session"]["close"])
        prestart_t = _at(day, rec.get("prestart", settings["session"]["open"]))
        opening_start, opening_end = (_at(day, t).time() for t in rec["opening_ticks"])

        if clock.now() >= close_t:
            return RecordingSummary(status="no_session", errors=["started after the session close"])
        wait = (prestart_t - clock.now()).total_seconds()
        if wait > 0:
            sleep(wait)

        # Spots for planning come from the REST last price; before the open that is the previous close.
        index_specs = settings["angel"]["index_tokens"]
        spots, errors = {}, []
        for underlying in ("NIFTY", "SENSEX"):
            spec = index_specs[underlying]
            try:
                spots[underlying] = client.ltp(spec["exchange"], spec["symbol"], spec["token"])
            except Exception as exc:  # noqa: BLE001 - recorded; the other underlying may still work
                errors.append(f"ltp {underlying} ({spec['token']}): {type(exc).__name__}: {exc}"[:300])
        if not spots:
            return RecordingSummary(status="no_session", errors=errors)
        caught_up = 0
        if clock.now() > open_t + timedelta(minutes=1):     # a late start: fetch the missed morning first
            from quantdesk.recorder.catchup import catch_up

            targets = [(s["exchange"], s["token"]) for s in index_specs.values()] + \
                [("NSE", t) for t in constituents.values()]
            caught_up = catch_up(client, store, day, targets, open_t, clock.now())
        spot_token = {index_specs[u]["token"]: u for u in ("NIFTY", "SENSEX")}

        plan = plan_subscriptions(master, spots, day, constituents, settings)
        planned_at = clock.now()
        option_tokens = set(plan.option_meta["token"])
        jump_tokens = set(spot_token)  # India VIX legitimately moves >5%: never jump-filtered
        agg = MinuteAggregator(option_tokens=option_tokens, depth_tokens=plan.depth_tokens,
                               index_tokens=jump_tokens, session_open=open_t)
        summary = RecordingSummary(status="ok", subscription_count=plan.count(), reduced=plan.reduced,
                                   errors=errors)
        lock = threading.Lock()
        opening_rows: list[dict] = []
        events: list[dict] = [{"event": "subscribed", "time": clock.now(), "count": plan.count(),
                               "reduced": plan.reduced, "width": plan.width}]
        events += [{"event": "error", "time": clock.now(), "detail": e} for e in errors]
        if caught_up:
            events.append({"event": "caught_up", "time": clock.now(), "count": caught_up})
        stale_open: dict = {"since": None, "reconnected_at": None}
        latest = {"exchange_ts": None, "received_at": None, "outside": 0}
        stale_after = timedelta(seconds=rec["stale_seconds"])

        def record_error(where: str, exc: Exception) -> None:
            message = f"{where}: {type(exc).__name__}: {exc}"[:300]
            with lock:
                summary.errors.append(message)
                events.append({"event": "error", "time": clock.now(), "detail": message})

        def on_tick(tick):
            with lock:
                if not (open_t <= tick.exchange_ts < close_t):
                    latest["outside"] += 1
                    return
                if latest["exchange_ts"] is None or tick.exchange_ts > latest["exchange_ts"]:
                    latest["exchange_ts"] = tick.exchange_ts
                latest["received_at"] = tick.received_at
                if stale_open["since"] is not None:
                    period = (stale_open["since"], tick.exchange_ts)
                    summary.stale_periods.append(period)
                    events.append({"event": "stale", "time": tick.exchange_ts,
                                   "start": period[0], "end": period[1]})
                    stale_open["since"] = None
                stale_open["reconnected_at"] = None
                if tick.token in spot_token and tick.ltp > 0:
                    spots[spot_token[tick.token]] = tick.ltp
                if agg.add(tick) is None and tick.token in option_tokens \
                        and opening_start <= tick.exchange_ts.time() < opening_end:
                    opening_rows.append({
                        "token": tick.token, "ltp": tick.ltp, "bid": tick.bid, "bid_qty": tick.bid_qty,
                        "ask": tick.ask, "ask_qty": tick.ask_qty, "volume": tick.volume, "oi": tick.oi,
                        "atp": tick.atp, "total_buy_qty": tick.total_buy_qty,
                        "total_sell_qty": tick.total_sell_qty, "last_traded_qty": tick.last_traded_qty,
                        "last_traded_ts_raw": tick.last_traded_ts_raw, "seq": tick.seq,
                        "day_open": tick.day_open, "day_high": tick.day_high, "day_low": tick.day_low,
                        "prev_close": tick.prev_close,
                        "depth": json.dumps(tick.depth) if tick.depth else None,
                        "exchange_ts": tick.exchange_ts, "received_at": tick.received_at})

        def check_stale(now):
            """Silence during the session only: no in-session tick for stale_seconds opens a period, and the
            stream is told to reconnect (a feed can freeze while its socket stays open), then every minute."""
            if now < open_t:
                return
            with lock:
                reference = latest["received_at"] or open_t
                silent = now - reference > stale_after
                if silent and stale_open["since"] is None:
                    stale_open["since"] = latest["exchange_ts"] or open_t
                last = stale_open["reconnected_at"]
                due = silent and (last is None or (now - last).total_seconds() >= RECONNECT_EVERY_S)
                if due:
                    stale_open["reconnected_at"] = now
                    events.append({"event": "reconnect", "time": now})
            if due:
                try:
                    stream.reconnect()
                except Exception as exc:  # noqa: BLE001
                    record_error("reconnect", exc)

        stream = stream_factory(on_tick, lambda since, now: None)
        stream.subscribe(plan.tokens)
        stream.start()

        def write(kind, rows_or_frame):
            frame = rows_or_frame if isinstance(rows_or_frame, pd.DataFrame) else pd.DataFrame(rows_or_frame)
            if frame.empty:
                return
            try:
                store.append_parquet(kind, day, frame)
            except Exception as exc:  # noqa: BLE001 - one failed write never ends the session
                record_error(f"write {kind}", exc)

        # NSE reuses F&O tokens, so the day's token -> contract map is stored with the data.
        write("option_meta", plan.option_meta.assign(subscribed_at=planned_at))

        def flush(minute_end):
            with lock:
                result = agg.flush(minute_end)
                opening = list(opening_rows)
                opening_rows.clear()
                pending_events = list(events)
                events.clear()
                outside, latest["outside"] = latest["outside"], 0
            write("bars", result.bars)
            write("option_snapshots", result.snapshots)
            write("depth", result.depth)
            write("opening_ticks", opening)
            write("recorder_events", pending_events)
            if not result.bars.empty:
                summary.minutes_written += result.bars["minute"].nunique()
            dropped = dict(result.dropped)
            if outside:
                dropped["outside_session"] = outside
            for reason, n in dropped.items():
                summary.dropped[reason] = summary.dropped.get(reason, 0) + n
            summary.zero_quotes += result.zero_quotes
            summary.crossed += result.crossed

        now = clock.now()
        next_minute = max(now.replace(second=0, microsecond=0), open_t) + timedelta(minutes=1)
        last_recenter = now
        try:
            while next_minute <= close_t:
                sleep(LOOP_STEP_S)
                now = clock.now()
                check_stale(now)
                if now >= open_t and (now - last_recenter).total_seconds() >= RECENTER_EVERY_S:
                    last_recenter = now
                    try:
                        plan, added = recenter(plan, dict(spots), master, settings)
                        if added:
                            new_options = set(plan.option_meta["token"]) - option_tokens
                            option_tokens |= new_options
                            meta = plan.option_meta
                            write("option_meta", meta[meta["token"].isin(new_options)].assign(subscribed_at=now))
                            with lock:
                                agg.add_tokens(option_tokens=new_options, depth_tokens=plan.depth_tokens)
                                events.append({"event": "recenter", "time": now,
                                               "count": sum(len(v) for v in added.values())})
                            summary.recenter_events += 1
                            try:
                                stream.add_tokens(added)
                            except Exception as exc:  # noqa: BLE001
                                record_error("add_tokens", exc)
                    except Exception as exc:  # noqa: BLE001
                        record_error("recenter", exc)
                with lock:
                    feed_time = latest["exchange_ts"]
                due = (feed_time is not None and feed_time >= next_minute + timedelta(seconds=FLUSH_GRACE_S)) \
                    or now >= next_minute + timedelta(seconds=PC_FALLBACK_GRACE_S)
                if due:
                    flush(next_minute)
                    next_minute += timedelta(minutes=1)
        finally:
            try:
                stream.close()
            except Exception as exc:  # noqa: BLE001
                record_error("stream close", exc)
            with lock:
                if stale_open["since"] is not None:
                    period = (stale_open["since"], clock.now())
                    summary.stale_periods.append(period)
                    events.append({"event": "stale", "time": period[1], "start": period[0], "end": period[1]})
            flush(min(next_minute, close_t))  # never write minutes at or after the close
        return summary
