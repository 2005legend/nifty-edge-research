from datetime import datetime, timezone

from quantdesk.broker.ws import TickStream, normalize_tick
from quantdesk.clock import IST
from tests.fakes import FakeClock, FakeSleep, FakeStream

START = datetime(2026, 10, 20, 9, 15, tzinfo=IST)
EPOCH_0915 = int(datetime(2026, 10, 20, 3, 45, tzinfo=timezone.utc).timestamp() * 1000)


def raw_tick(token="43210", ltp_paise=1234550, **extra):
    data = {
        "subscription_mode": 3,
        "exchange_type": 2,
        "token": token,
        "exchange_timestamp": EPOCH_0915,
        "last_traded_price": ltp_paise,
        "volume_trade_for_the_day": 1000,
        "open_interest": 5000,
    }
    data.update(extra)
    return data


def test_normalize_tick_converts_paise_and_epoch(monkeypatch):
    monkeypatch.setenv("TZ", "America/New_York")
    tick = normalize_tick(raw_tick(), received_at=START)
    assert tick.ltp == 12345.50
    assert tick.exchange_ts == datetime(2026, 10, 20, 9, 15, tzinfo=IST)
    assert tick.exchange_ts.utcoffset().total_seconds() == 5.5 * 3600
    assert tick.token == "43210"
    assert tick.volume == 1000
    assert tick.oi == 5000


def test_normalize_tick_depth_five_levels():
    buys = [{"flag": 0, "quantity": 65 * (i + 1), "price": 10000 - i * 5, "no of orders": 1} for i in range(5)]
    sells = [{"flag": 1, "quantity": 65 * (i + 1), "price": 10010 + i * 5, "no of orders": 1} for i in range(5)]
    tick = normalize_tick(raw_tick(best_5_buy_data=buys, best_5_sell_data=sells), received_at=START)
    assert len(tick.depth) == 10
    assert tick.bid == 100.00
    assert tick.ask == 100.10
    assert tick.bid_qty == 65
    assert tick.ask_qty == 65
    assert tick.depth[0] == ("buy", 1, 100.00, 65)
    assert tick.depth[5] == ("sell", 1, 100.10, 65)


def test_stale_fires_after_30_seconds_without_ticks():
    clock = FakeClock(START)
    stale_events = []
    stream = TickStream("jwt", "key", "C1", "feed", on_tick=lambda t: None,
                        on_stale=lambda since, now: stale_events.append((since, now)),
                        clock=clock, ws_factory=FakeStream([]), stale_seconds=30,
                        sleep=FakeSleep(clock))
    stream.subscribe({2: ["a"]})
    clock.advance(31)
    stream.check_stale()
    stream.check_stale()
    assert len(stale_events) == 1
    stream._on_data(None, raw_tick())
    clock.advance(10)
    stream.check_stale()
    assert len(stale_events) == 1
    clock.advance(25)
    stream.check_stale()
    assert len(stale_events) == 2


def test_reconnect_resubscribes_all_tokens():
    clock = FakeClock(START)
    ticks = []
    holder = {}

    def add_b(ws):
        holder["stream"].add_tokens({2: ["b"]})

    def finish(ws):
        holder["stream"].close()

    factory = FakeStream([[raw_tick("a"), add_b, "drop"], [raw_tick("b"), finish]])
    stream = TickStream("jwt", "key", "C1", "feed", on_tick=ticks.append, on_stale=lambda *a: None,
                        clock=clock, ws_factory=factory, stale_seconds=30, sleep=FakeSleep(clock))
    holder["stream"] = stream
    stream.subscribe({2: ["a"]})
    stream.run()
    assert len(factory.connections) == 2
    second = factory.connections[1]
    tokens = set()
    for _, _, token_list in second.subscribe_calls:
        for entry in token_list:
            tokens.update(entry["tokens"])
    assert tokens == {"a", "b"}
    assert [t.token for t in ticks] == ["a", "b"]
