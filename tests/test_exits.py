from dataclasses import replace
from datetime import date, datetime, time, timedelta

import numpy as np
import pandas as pd
import pytest

from quantdesk.clock import IST
from quantdesk.pricing.quotes import Quote
from quantdesk.strategy.exits import OpenTrade, simulate_exit
from quantdesk.strategy.types import Signal, StrikeChoice
from quantdesk.validation.hypotheses import load_hypotheses
from tests.test_bands import make_ctx

H = load_hypotheses()
TODAY = date(2026, 10, 22)
DAY = date(2024, 3, 5)
FILL = datetime(2024, 3, 5, 10, 0, tzinfo=IST)


class StubQuotes:
    """Call premium = 50 + 0.5 x (index - 22000); one-rupee-tenth half-spread."""

    def __init__(self, frame):
        self.close = frame.set_index("ts")["close"]

    def mid(self, index, expiry, strike, kind, at, spot=None, vix=None, sigma_scale=1.0):
        s = spot if spot is not None else self.close[at - timedelta(minutes=1)]
        return 50.0 + 0.5 * (s - 22000.0)

    def quote(self, index, expiry, strike, kind, at):
        m = self.mid(index, expiry, strike, kind, at)
        return Quote(bid=round(m - 0.1, 2), ask=round(m + 0.1, 2), mid=m)


def frame_of(closes, start=FILL, vwap=21950.0):
    ts = [start + timedelta(minutes=i) for i in range(len(closes))]
    return pd.DataFrame({"ts": ts, "close": closes, "vwap": vwap})


def trade(start=FILL):
    sig = Signal("NIFTY", start, "long", 22000.0, 21990.0, 21900.0, 21950.0, 21980.0, 20.0, 22046.0)
    choice = StrikeChoice("NIFTY", date(2024, 3, 7), 22000.0, "CE", 50, 50.1, 0.5, 800.0, 380.0, 0.32, 100.0, 0.2)
    return OpenTrade(sig, choice, fill_at=start, fill_premium=50.1, backstop_trigger=42.1, backstop_limit=37.89)


def ctx(hard=time(15, 10)):
    return make_ctx(np.full(375, 0.002), day=DAY, hard_exit=hard)


def test_trail_starts_at_one_b_and_ratchets_with_a_two_minute_delay():
    closes = [22000 + 4 * i for i in range(5)] + [22020 + (i - 5) * 20 / 14 for i in range(5, 20)] \
             + [22040 - 2 * (i - 19) for i in range(20, 60)]
    frame = frame_of(closes)
    out = simulate_exit(trade(), frame, StubQuotes(frame), ctx(), "X1", H, TODAY)
    assert out.ratchets == 3
    assert out.reason == "stop" and out.exit_at == FILL + timedelta(minutes=37)
    assert out.exit_premium == pytest.approx(50 + 0.5 * 6 - 0.1)        # bar 36 closes at 22006, sold at the bid


def test_laggard_exits_at_30_minutes_when_flat():
    frame = frame_of([22000 + (3 if i % 2 else -3) for i in range(60)])
    out = simulate_exit(trade(), frame, StubQuotes(frame), ctx(), "X1", H, TODAY)
    assert (out.reason, out.exit_at) == ("laggard", FILL + timedelta(minutes=32))


def test_a_delayed_exit_never_passes_the_hard_exit():
    start = datetime(2024, 3, 5, 15, 0, tzinfo=IST)
    frame = frame_of([22000.0] * 8 + [21970.0] * 12, start=start)       # the stop breaks on the 15:08 bar
    out = simulate_exit(trade(start), frame, StubQuotes(frame), ctx(), "X1", H, TODAY)
    assert (out.reason, out.exit_at) == ("hard_exit", datetime(2024, 3, 5, 15, 10, tzinfo=IST))


def test_x1_books_the_worse_of_index_alert_and_premium_backstop():
    closes = [22000 - 2 * i for i in range(10)] + [21982 + 3 * (i - 9) for i in range(10, 70)]
    frame = frame_of(closes)
    out = simulate_exit(trade(), frame, StubQuotes(frame), ctx(hard=time(11, 0)), "X1", H, TODAY)
    assert out.model == "B" and out.pnl == out.pnl_b < out.pnl_a
    assert out.exit_at == FILL + timedelta(minutes=9) and out.exit_premium == pytest.approx(41.9)


def test_a_backstop_that_cannot_fill_falls_back_to_the_index_alert():
    closes = [22000.0] * 5 + [21900.0] * 55                            # a gap through the limit
    frame = frame_of(closes)
    out = simulate_exit(trade(), frame, StubQuotes(frame), ctx(), "X1", H, TODAY)
    assert out.model == "A" and out.reason == "stop" and out.exit_at == FILL + timedelta(minutes=8)


def test_x0_takes_the_fixed_target():
    closes = [22000 + 4 * i for i in range(30)]                         # 22048 at bar 12
    frame = frame_of(closes)
    out = simulate_exit(trade(), frame, StubQuotes(frame), ctx(), "X0", H, TODAY)
    assert (out.reason, out.exit_at) == ("target", FILL + timedelta(minutes=13))
    assert out.exit_premium == pytest.approx(50 + 0.5 * 48 - 0.1)


def test_pnl_uses_todays_charges():
    from quantdesk.costs import round_trip
    closes = [22000 + 4 * i for i in range(30)]
    frame = frame_of(closes)
    out = simulate_exit(trade(), frame, StubQuotes(frame), ctx(), "X0", H, TODAY)
    costs = round_trip(50.1, out.exit_premium, 50, exchange="NSE", day=TODAY).total
    assert out.pnl == pytest.approx((out.exit_premium - 50.1) * 50 - costs)
