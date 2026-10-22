"""Pre-flight controls (R36): the engine finds a planted edge and finds nothing where there is none."""

from datetime import date, datetime, time, timedelta

import numpy as np
import pandas as pd

from quantdesk.backtest.engine import placebo_run
from quantdesk.clock import IST
from quantdesk.pricing.quotes import Quote
from quantdesk.strategy.gates import Helpers
from quantdesk.validation.hypotheses import load_hypotheses
from quantdesk.validation.stats import t_stat
from tests.derived_fixture import clock_for, flat_surface
from tests.test_bands import make_ctx

H = load_hypotheses()
TODAY = date(2026, 10, 22)
DAYS = list(pd.bdate_range("2024-01-01", periods=120).date)
CLOCK = clock_for(DAYS)


class KindQuotes:
    def __init__(self, frame):
        self.frame = frame.set_index("ts")

    def state(self, index, at):
        return float(self.frame.loc[at - timedelta(minutes=1), "close"]), 14.0

    def mid(self, index, expiry, strike, kind, at, spot=None, vix=None, sigma_scale=1.0):
        s = spot if spot is not None else self.state(index, at)[0]
        base = 22000.0                     # every strike priced off the day's open: a smooth, never-floored premium
        move = s - base if kind == "CE" else base - s
        return max(1.0, 50.0 + 0.3 * move + 0.3 * max(0.0, move))

    def quote(self, index, expiry, strike, kind, at):
        m = self.mid(index, expiry, strike, kind, at)
        return Quote(bid=round(m - 0.1, 2), ask=round(m + 0.1, 2), mid=m)


class DriftSource:
    """Every session drifts by `drift` points a minute from 09:15, plus seeded noise."""

    def __init__(self, drift, seed):
        self.drift, self.rng = drift, np.random.default_rng(seed)

    def context(self, index, day):
        return make_ctx(np.full(375, 0.0005), open_=22000.0, prev_close=22000.0, day=day,
                        expiry_1=day + timedelta(days=7), expiry_2=day + timedelta(days=14), hard_exit=time(15, 10))

    def frame(self, ctx):
        t0 = datetime.combine(ctx.day, time(9, 15), tzinfo=IST)
        ts = [t0 + timedelta(minutes=i) for i in range(375)]
        noise = np.cumsum(self.rng.normal(0, 2.0, 375))
        close = 22000.0 + self.drift * np.arange(375) + noise
        return pd.DataFrame({"ts": ts, "close": close, "vwap": close - 5.0, "upper": close, "lower": close})

    def helpers(self, ctx, frame):
        return Helpers(clock=CLOCK, surface=flat_surface(), quotes=KindQuotes(frame))


def test_positive_control_recovers_a_planted_drift():
    out = placebo_run(DriftSource(drift=1.0, seed=1), DAYS, H, TODAY, seed=1, side_rule="long")
    assert len(out) > 30 and t_stat(out["gross_r"]) > 3


def test_negative_control_finds_no_edge_in_a_driftless_market():
    """No positive edge: paying the spread makes random entries lose a little, which is cost, not skill."""
    out = placebo_run(DriftSource(drift=0.0, seed=2), DAYS, H, TODAY, seed=2, side_rule="random")
    assert len(out) > 30 and t_stat(out["gross_r"]) < 2
