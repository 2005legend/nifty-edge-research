from datetime import datetime, timedelta

from quantdesk.broker.ws import Tick
from quantdesk.clock import IST
from quantdesk.recorder.bars import MinuteAggregator, is_bad_tick

T0 = datetime(2026, 10, 20, 9, 15, tzinfo=IST)


def tick(token, ltp, seconds=0, **kw):
    ts = T0 + timedelta(seconds=seconds)
    return Tick(token=token, exchange_type=kw.pop("exchange_type", 2), ltp=ltp, exchange_ts=ts,
                received_at=ts, **kw)


def test_bars_ohlc_and_volume_delta():
    agg = MinuteAggregator(option_tokens=set(), depth_tokens=set(), index_tokens=set())
    for i, (price, vol) in enumerate([(100, 1000), (102, 1100), (99, 1200), (101, 1300)]):
        agg.add(tick("FUT", price, seconds=i * 10, volume=vol))
    bars = agg.flush(T0 + timedelta(minutes=1)).bars
    row = bars.iloc[0]
    assert (row["open"], row["high"], row["low"], row["close"]) == (100, 102, 99, 101)
    assert row["volume"] == 300
    assert row["n_ticks"] == 4
    assert row["minute"] == T0


def test_option_snapshot_is_last_state_in_minute():
    agg = MinuteAggregator(option_tokens={"OPT"}, depth_tokens=set(), index_tokens=set())
    agg.add(tick("OPT", 50, seconds=5, bid=49.9, ask=50.1, bid_qty=65, ask_qty=130, volume=10, oi=100))
    agg.add(tick("OPT", 51, seconds=40, bid=50.9, ask=51.2, bid_qty=65, ask_qty=65, volume=20, oi=120))
    snap = agg.flush(T0 + timedelta(minutes=1)).snapshots.iloc[0]
    assert (snap["ltp"], snap["bid"], snap["ask"], snap["oi"]) == (51, 50.9, 51.2, 120)


def test_bad_ticks_dropped_and_counted():
    agg = MinuteAggregator(option_tokens={"OPT"}, depth_tokens=set(), index_tokens={"IDX"})
    assert agg.add(tick("OPT", 0, seconds=1)) == "non_positive"
    assert agg.add(tick("OPT", 10, seconds=2, bid=10.0, ask=9.0)) == "crossed"
    assert agg.add(tick("IDX", 22500, seconds=3, exchange_type=1)) is None
    assert agg.add(tick("IDX", 23700, seconds=4, exchange_type=1)) == "index_jump"
    result = agg.flush(T0 + timedelta(minutes=1))
    assert result.dropped == {"non_positive": 1, "crossed": 1, "index_jump": 1}
    assert is_bad_tick(tick("IDX", 22600, exchange_type=1), last_ltp=22500, is_index=True) is None


def test_zero_quote_flagged_not_dropped():
    agg = MinuteAggregator(option_tokens={"OPT"}, depth_tokens=set(), index_tokens=set())
    assert agg.add(tick("OPT", 12.5, seconds=3, bid=0.0, ask=0.0)) is None
    result = agg.flush(T0 + timedelta(minutes=1))
    assert bool(result.snapshots.iloc[0]["zero_quote"]) is True
    assert result.zero_quotes == 1


def test_depth_rows_only_for_depth_tokens():
    depth = tuple([("buy", i, 100 - i * 0.05, 65) for i in range(1, 6)] +
                  [("sell", i, 100 + i * 0.05, 65) for i in range(1, 6)])
    agg = MinuteAggregator(option_tokens={"A", "B"}, depth_tokens={"A"}, index_tokens=set())
    agg.add(tick("A", 100, seconds=1, bid=99.95, ask=100.05, depth=depth))
    agg.add(tick("B", 100, seconds=1, bid=99.95, ask=100.05, depth=depth))
    rows = agg.flush(T0 + timedelta(minutes=1)).depth
    assert set(rows["token"]) == {"A"}
    assert len(rows) == 10
    assert set(rows.columns) >= {"minute", "token", "side", "level", "price", "qty"}


def test_index_jump_reference_expires_after_60s():
    agg = MinuteAggregator(option_tokens=set(), depth_tokens=set(), index_tokens={"IDX"})
    assert agg.add(tick("IDX", 22500, seconds=0, exchange_type=1)) is None
    assert agg.add(tick("IDX", 23700, seconds=61, exchange_type=1)) is None


def test_index_reaccepts_after_three_consistent_rejections():
    agg = MinuteAggregator(option_tokens=set(), depth_tokens=set(), index_tokens={"IDX"})
    assert agg.add(tick("IDX", 22500, seconds=0, exchange_type=1)) is None
    assert agg.add(tick("IDX", 23700, seconds=1, exchange_type=1)) == "index_jump"
    assert agg.add(tick("IDX", 23710, seconds=2, exchange_type=1)) == "index_jump"
    assert agg.add(tick("IDX", 23705, seconds=3, exchange_type=1)) is None   # third agreeing tick re-accepted
    assert agg.add(tick("IDX", 23720, seconds=4, exchange_type=1)) is None


def test_late_tick_after_flush_dropped_not_duplicated():
    agg = MinuteAggregator(option_tokens=set(), depth_tokens=set(), index_tokens=set())
    agg.add(tick("FUT", 100, seconds=10, volume=1))
    agg.flush(T0 + timedelta(minutes=1))
    assert agg.add(tick("FUT", 101, seconds=59, volume=2)) == "late"
    assert agg.flush(T0 + timedelta(minutes=2)).bars.empty


def test_bars_carry_atp_and_order_book_totals():
    agg = MinuteAggregator(option_tokens={"OPT"}, depth_tokens=set(), index_tokens=set())
    agg.add(tick("FUT", 100, seconds=5, volume=10, atp=99.5, total_buy_qty=650, total_sell_qty=1300))
    agg.add(tick("OPT", 50, seconds=5, bid=49.9, ask=50.1, atp=49.8, total_buy_qty=65, total_sell_qty=130))
    result = agg.flush(T0 + timedelta(minutes=1))
    assert result.bars.iloc[0]["atp"] == 99.5
    assert result.bars.iloc[0]["total_buy_qty"] == 650
    assert result.snapshots.iloc[0]["atp"] == 49.8
    assert result.snapshots.iloc[0]["total_sell_qty"] == 130


def test_flush_keeps_later_minutes():
    agg = MinuteAggregator(option_tokens=set(), depth_tokens=set(), index_tokens=set())
    agg.add(tick("FUT", 100, seconds=10, volume=1))
    agg.add(tick("FUT", 101, seconds=70, volume=2))
    first = agg.flush(T0 + timedelta(minutes=1))
    assert len(first.bars) == 1
    second = agg.flush(T0 + timedelta(minutes=2))
    assert len(second.bars) == 1
    assert second.bars.iloc[0]["minute"] == T0 + timedelta(minutes=1)
