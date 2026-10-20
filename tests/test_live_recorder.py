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


def run(tmp_path, ticks, *, start, close="09:18", trading=True, store=None, client=None,
        skew_s=0.0, fail_add_tokens=False, holder=None):
    master = load_master(FIXTURE)
    settings = copy.deepcopy(load_settings())
    settings["session"]["close"] = close
    clock = FakeClock(start)
    holder = holder if holder is not None else {}
    sleep = ScriptedSleep(clock, holder)

    def stream_factory(on_tick, on_stale):
        stream = ScriptedStream(ticks, clock, skew_s=skew_s, fail_add_tokens=fail_add_tokens).bind(on_tick, on_stale)
        holder["stream"] = stream
        return stream

    store = store or Store(tmp_path)
    summary = run_recording(DAY, client=client or FakeLtpClient(), stream_factory=stream_factory, master=master,
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


class FailingLtpClient:
    def __init__(self, failing):
        self.failing = set(failing)

    def ltp(self, exchange, tradingsymbol, token):
        if token in self.failing:
            raise RuntimeError(f"ltp failed for {token}")
        return {"99926000": 22550.0, "99919000": 73400.0}[token]


def test_vix_moves_over_5_percent_are_recorded(tmp_path):
    prices = [12.0] + [12.9 + 0.2 * i for i in range(14)]  # a genuine 7.5% gap, then a steady climb
    ticks = [Tick("99926017", 1, p, at(9, 15, 0) + timedelta(seconds=10 * i),
                  at(9, 15, 0) + timedelta(seconds=10 * i)) for i, p in enumerate(prices)]
    summary, store = run(tmp_path, ticks, start=at(9, 14))
    vix = store.read("bars", DAY)
    vix = vix[vix["token"] == "99926017"]
    assert len(vix) == 3
    assert summary.dropped.get("index_jump", 0) == 0


def test_pc_clock_ahead_gives_one_row_per_minute(tmp_path):
    master = load_master(FIXTURE)
    ticks = make_ticks(master, at(9, 15), at(9, 17, 0), every=1)
    summary, store = run(tmp_path, ticks, start=at(9, 14), close="09:18", skew_s=5)
    bars = store.read("bars", DAY)
    nifty = bars[bars["token"] == "99926000"]
    assert not nifty.duplicated(["minute", "token"]).any()
    assert int(nifty[nifty["minute"] == at(9, 15)]["n_ticks"].iloc[0]) == 60


def test_subscribes_before_open_and_keeps_first_tick(tmp_path):
    master = load_master(FIXTURE)
    pre_open = [Tick("99926000", 1, 22400.0, at(9, 12), at(9, 12))]
    ticks = pre_open + make_ticks(master, at(9, 15), at(9, 16, 30))
    holder = {}
    summary, store = run(tmp_path, ticks, start=at(9, 5), holder=holder)
    assert holder["stream"].subscribed_at <= at(9, 15)
    bars = store.read("bars", DAY)
    first = bars[(bars["token"] == "99926000")].sort_values("minute").iloc[0]
    assert first["minute"] == at(9, 15)
    assert first["open"] == 22550.0
    assert at(9, 12) not in set(bars["minute"])


def test_one_underlying_ltp_failure_still_records(tmp_path):
    master = load_master(FIXTURE)
    summary, store = run(tmp_path, make_ticks(master, at(9, 15), at(9, 16, 30)), start=at(9, 14),
                         client=FailingLtpClient({"99919000"}))
    assert summary.status == "ok"
    assert summary.errors and "99919000" in summary.errors[0]


def test_no_session_reports_error(tmp_path):
    summary, _ = run(tmp_path, [], start=at(9, 14), client=FailingLtpClient({"99926000", "99919000"}))
    assert summary.status == "no_session"
    assert any("RuntimeError" in e for e in summary.errors)


def test_recorder_survives_add_tokens_failure(tmp_path):
    master = load_master(FIXTURE)
    moved = [Tick("99926000", 1, 22550.0 + 6 * 50, at(9, 15, s), at(9, 15, s)) for s in range(0, 60, 10)]
    ticks = moved + make_ticks(master, at(9, 16), at(9, 17, 30))
    summary, store = run(tmp_path, ticks, start=at(9, 14), fail_add_tokens=True)
    assert summary.status == "ok"
    assert summary.minutes_written >= 2
    assert any("add_tokens" in e for e in summary.errors)
    assert "error" in set(store.read("recorder_events", DAY)["event"])


class FlakyStore(Store):
    def __init__(self, root):
        super().__init__(root)
        self.failed = False

    def append_parquet(self, kind, day, df):
        if kind == "bars" and not self.failed:
            self.failed = True
            raise OSError("disk hiccup")
        return super().append_parquet(kind, day, df)


def test_recorder_survives_write_failure(tmp_path):
    master = load_master(FIXTURE)
    store = FlakyStore(tmp_path)
    summary, _ = run(tmp_path, make_ticks(master, at(9, 15), at(9, 17, 30)), start=at(9, 14), store=store)
    assert summary.status == "ok"
    assert any("bars" in e for e in summary.errors)
    assert len(store.read("bars", DAY)["minute"].unique()) == 2


def test_opening_ticks_keep_raw_feed_fields(tmp_path):
    """Opening-window option ticks keep the fields that cannot be rebuilt later (review I8)."""
    master = load_master(FIXTURE)
    opt = option_token(master)
    depth = (("buy", 1, 99.9, 65), ("sell", 1, 100.1, 130))
    rich = Tick(opt, 2, 100.0, at(9, 15, 1), at(9, 15, 1), volume=10, oi=5, bid=99.9, ask=100.1, bid_qty=65,
                ask_qty=130, depth=depth, atp=99.5, total_buy_qty=6500, total_sell_qty=3900, last_traded_qty=65,
                last_traded_ts_raw=1792386301000, seq=42, day_open=98.0, day_high=101.0, day_low=97.5,
                prev_close=96.0)
    summary, store = run(tmp_path, [Tick("99926000", 1, 22550.0, at(9, 15), at(9, 15)), rich], start=at(9, 14),
                         close="09:16")
    row = store.read("opening_ticks", DAY).iloc[0]
    assert (row["atp"], row["total_buy_qty"], row["total_sell_qty"], row["last_traded_qty"], row["seq"]) == \
        (99.5, 6500, 3900, 65, 42)
    assert (row["day_open"], row["day_high"], row["day_low"], row["prev_close"]) == (98.0, 101.0, 97.5, 96.0)
    assert row["depth"] is not None and "130" in row["depth"]
