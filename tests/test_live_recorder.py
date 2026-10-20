import copy
import os
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from quantdesk.broker.ws import Tick
from quantdesk.clock import IST
from quantdesk.config import load_settings
from quantdesk.instruments import load_master
from quantdesk.recorder.live import AlreadyRunningError, run_lock, run_recording
from quantdesk.storage import Store
from tests.fakes import FakeClock, FakeSmartConnect, ScriptedSleep, ScriptedStream

FIXTURE = Path(__file__).parent / "fixtures" / "master_small.json"
DAY = date(2026, 10, 19)  # a Monday; fixture's nearest expiries are after this day
CONSTITUENTS = {"RELIANCE": "2885"}


class FakeLtpClient:
    def __init__(self):
        self.calls = []

    def ltp(self, exchange, tradingsymbol, token):
        self.calls.append(token)
        return {"99926000": 22550.0, "99919000": 73400.0}.get(token, 100.0)


def at(h, m, s=0):
    return datetime(2026, 10, 19, h, m, s, tzinfo=IST)


def option_token(master):
    row = master[(master["symbol"] == "NIFTY20OCT2622550CE")].iloc[0]
    return row["token"]


def make_ticks(master, start, end, every=10, gap=None):
    opt = option_token(master)
    ticks = []
    t = start
    while t < end:
        if not (gap and gap[0] <= t < gap[1]):
            ticks.append(Tick("99926000", 1, 22550.0, t, t))
            ticks.append(Tick(opt, 2, 100.0, t, t, volume=10, oi=5, bid=99.9, ask=100.1, bid_qty=65, ask_qty=65))
        t += timedelta(seconds=every)
    return ticks


def run(tmp_path, ticks, *, start, close="09:18", trading=True, store=None):
    master = load_master(FIXTURE)
    settings = copy.deepcopy(load_settings())
    settings["session"]["close"] = close
    clock = FakeClock(start)
    holder = {}
    sleep = ScriptedSleep(clock, holder)

    def stream_factory(on_tick, on_stale):
        stream = ScriptedStream(ticks, clock).bind(on_tick, on_stale)
        holder["stream"] = stream
        return stream

    store = store or Store(tmp_path)
    summary = run_recording(DAY, client=FakeLtpClient(), stream_factory=stream_factory, master=master,
                            constituents=CONSTITUENTS, store=store, clock=clock, sleep=sleep,
                            is_trading_day=lambda d: trading, settings=settings)
    return summary, store


def test_holiday_exits_cleanly_without_writing(tmp_path):
    summary, store = run(tmp_path, [], start=at(9, 0), trading=False)
    assert summary.status == "holiday"
    assert store.read("bars").empty


def test_second_instance_refuses(tmp_path):
    store = Store(tmp_path)
    with run_lock(store):
        with pytest.raises(AlreadyRunningError):
            with run_lock(store):
                pass


def test_stale_lock_from_dead_pid_is_cleared(tmp_path):
    store = Store(tmp_path)
    lock = tmp_path / "run" / "record.lock"
    lock.parent.mkdir(parents=True)
    lock.write_text("999999")
    with run_lock(store):
        assert lock.read_text() == str(os.getpid())
    assert not lock.exists()


def test_records_minutes_and_flushes_each_minute(tmp_path):
    master = load_master(FIXTURE)
    ticks = make_ticks(master, at(9, 15), at(9, 17, 30))
    summary, store = run(tmp_path, ticks, start=at(9, 14))
    assert summary.status == "ok"
    assert summary.minutes_written == 3
    bars = store.read("bars", DAY)
    assert sorted(bars["minute"].unique()) == [at(9, 15), at(9, 16), at(9, 17)]
    assert len(store.read("option_snapshots", DAY)) == 3
    opening = store.read("opening_ticks", DAY)
    assert len(opening) == len([t for t in ticks if t.token != "99926000"])


def test_ticks_after_close_not_written(tmp_path):
    master = load_master(FIXTURE)
    ticks = make_ticks(master, at(9, 15), at(9, 18, 30))
    summary, store = run(tmp_path, ticks, start=at(9, 14))
    assert at(9, 18) not in set(store.read("bars", DAY)["minute"])


def test_restart_same_day_appends(tmp_path):
    master = load_master(FIXTURE)
    store = Store(tmp_path)
    run(tmp_path, make_ticks(master, at(9, 15), at(9, 16, 30)), start=at(9, 14), close="09:17", store=store)
    parts_first = len(list((tmp_path / "raw" / "bars").rglob("*.parquet")))
    run(tmp_path, make_ticks(master, at(9, 17), at(9, 18, 30)), start=at(9, 17), close="09:19", store=store)
    bars = store.read("bars", DAY)
    assert {at(9, 15), at(9, 16), at(9, 17), at(9, 18)} <= set(bars["minute"])
    assert len(list((tmp_path / "raw" / "bars").rglob("*.parquet"))) > parts_first


def test_stale_period_recorded(tmp_path):
    master = load_master(FIXTURE)
    ticks = make_ticks(master, at(9, 15), at(9, 18, 5), gap=(at(9, 16, 0), at(9, 16, 40)))
    summary, store = run(tmp_path, ticks, start=at(9, 14))
    assert len(summary.stale_periods) == 1
    start, end = summary.stale_periods[0]
    assert start == at(9, 15, 50)
    assert end == at(9, 16, 40)
    events = store.read("recorder_events", DAY)
    assert "stale" in set(events["event"])
