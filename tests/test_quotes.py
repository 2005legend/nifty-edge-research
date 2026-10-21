from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from quantdesk.black76 import black76
from quantdesk.clock import IST
from quantdesk.pricing.clock import Clock
from quantdesk.pricing.quotes import ModelQuotes, half_spread, round_down_tick, round_up_tick
from quantdesk.pricing.surface import Surface, sigma_bt
from quantdesk.validation.hypotheses import load_hypotheses

H = load_hypotheses()


def t(hh, mm):
    return datetime(2026, 10, 21, hh, mm, tzinfo=IST)


def test_half_spread_table_and_time_multipliers():
    assert half_spread("NIFTY", 40.0, t(11, 0), H) == pytest.approx(0.10)
    assert half_spread("NIFTY", 60.0, t(9, 20), H) == pytest.approx(0.40)
    assert half_spread("NIFTY", 60.0, t(9, 45), H) == pytest.approx(0.30)
    assert half_spread("SENSEX", 60.0, t(14, 50), H) == pytest.approx(1.00)


def test_quotes_round_away_from_the_mid():
    assert (round_up_tick(10.01), round_down_tick(10.04)) == (10.05, 10.0)
    assert round_up_tick(10.05) == 10.05 and round_down_tick(10.05) == 10.05     # a price on the grid stays put
    assert round_down_tick(0.01) == 0.05                                          # never below one tick


def test_model_quotes_price_from_the_bar_before_the_moment():
    days = tuple(date(2026, 10, 1) + timedelta(d) for d in range(60))
    clock = Clock(np.full(375, 1 / 375), 0.0, 0.0, 0.0, days)
    surface = Surface(r_dte={d: 1.0 for d in range(7)}, b1=0.0, b2=0.0, floor=0.5, gamma_dn=0.0, gamma_up=0.0)
    ts = [t(10, 0) + timedelta(minutes=i) for i in range(3)]
    frame = pd.DataFrame({"ts": ts, "close": [22000.0, 22100.0, 22200.0], "vix": [15.0, 15.0, 15.0]})
    quotes = ModelQuotes({"NIFTY": frame}, surface, clock, H)
    q = quotes.quote("NIFTY", date(2026, 10, 23), 22100.0, "CE", t(10, 2))        # uses the 10:01 bar: S = 22100
    at = t(10, 2)
    T = clock.bt(at, datetime(2026, 10, 23, 15, 30, tzinfo=IST))
    mid = black76(22100.0, 22100.0, T, sigma_bt(15.0, at, clock), kind="call")
    assert q.mid == pytest.approx(mid)
    h = half_spread("NIFTY", mid, at, H)
    assert q.ask == round_up_tick(mid + h) and q.bid == round_down_tick(mid - h)
    with pytest.raises(KeyError):
        quotes.quote("NIFTY", date(2026, 10, 23), 22100.0, "CE", t(10, 0))         # no bar before 10:00
