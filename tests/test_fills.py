from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from quantdesk.backtest.fills import fill
from quantdesk.clock import IST
from quantdesk.strategy.types import Signal, StrikeChoice
from quantdesk.validation.hypotheses import load_hypotheses
from tests.test_bands import make_ctx
from tests.test_exits import StubQuotes

H = load_hypotheses()
AT = datetime(2024, 3, 5, 10, 0, tzinfo=IST)
SIG = Signal("NIFTY", AT, "long", 22000.0, 21990.0, 21900.0, 21950.0, 21990.0, 10.0, 22023.0)
CHOICE = StrikeChoice("NIFTY", date(2024, 3, 7), 22000.0, "CE", 50, 50.1, 0.5, 800.0, 380.0, 0.32, 100.0, 0.2)
CTX = make_ctx(np.full(375, 0.002), open_=22000.0, prev_close=22000.0, day=date(2024, 3, 5))


def frame_from(closes, start=AT - timedelta(minutes=1)):
    ts = [start + timedelta(minutes=i) for i in range(len(closes))]
    return pd.DataFrame({"ts": ts, "close": closes, "vwap": 21950.0, "upper": 21990.0})


def test_delay_zero_fills_at_the_signal_bar_plus_one_tick():
    frame = frame_from([22000.0, 22001.0, 22002.0, 22003.0, 22004.0, 22005.0, 22006.0])
    out = fill(SIG, CHOICE, frame, StubQuotes(frame), 0, CTX, H)
    assert out.status == "filled" and out.at == AT
    assert out.premium == pytest.approx(50.0 + 0.1 + 0.05)          # ask of the 09:59 bar + 1 tick


def test_delay_three_uses_the_bar_two_minutes_after_the_signal():
    frame = frame_from([22000.0, 22001.0, 22002.0, 22003.0, 22004.0, 22005.0, 22006.0])
    out = fill(SIG, CHOICE, frame, StubQuotes(frame), 3, CTX, H)
    assert out.at == AT + timedelta(minutes=3)
    assert out.premium == pytest.approx(50.0 + 0.5 * 3 + 0.1 + 0.05)  # bar 10:02 closes 22003


def test_a_market_that_ran_past_the_chase_cap_lapses():
    frame = frame_from([22000.0, 22010.0, 22020.0, 22030.0, 22040.0, 22050.0, 22060.0])
    # cap = min(0.15 x 0.002 x 22000, 0.3 x 10) = min(6.6, 3.0) = 3 points
    assert fill(SIG, CHOICE, frame, StubQuotes(frame), 1, CTX, H).status == "lapsed"


def test_a_signal_that_flips_back_within_three_minutes_is_rejected():
    frame = frame_from([22000.0, 21998.0, 21985.0, 21980.0, 21990.0, 22000.0, 22000.0])   # back under the band at 10:01
    assert fill(SIG, CHOICE, frame, StubQuotes(frame), 3, CTX, H).status == "rejected_flip"
    assert fill(SIG, CHOICE, frame, StubQuotes(frame), 1, CTX, H).status == "filled"   # flip checked at delay >= 3


def test_delays_beyond_the_lapse_or_the_hard_exit_lapse():
    frame = frame_from([22000.0] * 10)
    assert fill(SIG, CHOICE, frame, StubQuotes(frame), 6, CTX, H).status == "lapsed"
    late = make_ctx(np.full(375, 0.002), open_=22000.0, prev_close=22000.0, day=date(2024, 3, 5),
                    hard_exit=(AT + timedelta(minutes=2)).timetz().replace(tzinfo=None))
    assert fill(SIG, CHOICE, frame, StubQuotes(frame), 3, late, H).status == "lapsed"
