from dataclasses import replace
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from quantdesk.clock import IST
from quantdesk.pricing.quotes import Quote
from quantdesk.strategy.configs import config_for
from quantdesk.strategy.gates import Helpers
from quantdesk.strategy.meta import Consensus
from quantdesk.strategy.pipeline import decide
from quantdesk.strategy.types import ZRef
from quantdesk.validation.hypotheses import load_hypotheses
from tests.derived_fixture import clock_for, flat_surface, session_days
from tests.test_bands import make_ctx

H = load_hypotheses()
TODAY = date(2026, 10, 22)
DAY = date(2024, 3, 5)
AT = datetime(2024, 3, 5, 10, 0, tzinfo=IST)


class ConvexQuotes:
    """A call that gains 1.0 per index point above 22010 and loses 0.2 per point below it."""

    def __init__(self, frame):
        self.frame = frame.set_index("ts")

    def state(self, index, at):
        row = self.frame.loc[at - timedelta(minutes=1)]
        return float(row["close"]), float(row["vix"])

    def mid(self, index, expiry, strike, kind, at, spot=None, vix=None, sigma_scale=1.0):
        s = spot if spot is not None else self.state(index, at)[0]
        return 50.0 + 0.2 * (s - 22010.0) + 0.8 * max(0.0, s - 22010.0)

    def quote(self, index, expiry, strike, kind, at):
        m = self.mid(index, expiry, strike, kind, at)
        return Quote(bid=round(m - 0.1, 2), ask=round(m + 0.1, 2), mid=m)


def setup():
    refs = {(f, "10:00"): ZRef(0.0, 1.0, 100) for f in ("adv_share", "above_share", "top5_ret")}
    refs.update({(f, "*"): ZRef(0.0, 1.0, 100) for f in ("loc_vwap", "loc_level")})
    ctx = make_ctx(np.full(375, 0.0005), open_=21980.0, prev_close=21980.0, day=DAY,
                   prev_day=(22300.0, 21700.0, 21980.0), prev_week=(22400.0, 21600.0, 21900.0),
                   expiry_1=date(2024, 3, 7), expiry_2=date(2024, 3, 14), dte_1=2, sigma_day=0.01,
                   vix_prev_close=14.0, vol_rich_threshold=10.0, spike_ref=np.full(375, 0.5), z_refs=refs)
    ts = [AT - timedelta(minutes=k) for k in range(10, 0, -1)] + [AT + timedelta(minutes=k) for k in range(0, 5)]
    frame = pd.DataFrame({"ts": ts, "close": 22010.0, "high": 22010.0, "low": 22005.0, "vwap": 21995.0, "vix": 14.0,
                          "adv_share": 0.2, "above_share": 0.6, "top5_ret": 0.001, "atm_premium": 120.0})
    helpers = Helpers(clock=clock_for(session_days(60)), surface=flat_surface(), quotes=ConvexQuotes(frame))
    return ctx, frame, helpers


def test_decide_reports_the_first_failing_step():
    ctx, frame, helpers = setup()
    d = decide(replace(ctx, session_kind="irregular"), frame, AT, config_for("B0", {}), Consensus(0, 0), helpers, H, TODAY)
    assert d.failed == "irregular_session" and d.signal is None
    d = decide(replace(ctx, vol_rich_threshold=None), frame, AT, config_for("B0", {}), Consensus(0, 0), helpers, H, TODAY)
    assert d.failed == "warmup"


def test_decide_returns_an_alert_with_a_backstop():
    ctx, frame, helpers = setup()
    d = decide(ctx, frame, AT, config_for("B0", {}), Consensus(0.0, 0.0), helpers, H, TODAY)
    assert d.failed is None and d.p == 0.5
    alert = d.alert
    assert alert.entry_limit == pytest.approx(alert.choice.ask + 2 * 0.05)
    assert alert.backstop_trigger == pytest.approx(alert.choice.ask - 400 / alert.choice.lot)
    assert alert.backstop_limit == pytest.approx(alert.backstop_trigger - max(0.1 * alert.backstop_trigger, 0.25))
    assert alert.index_stop == d.signal.stop_level and alert.reasons_for


def test_hurdles_follow_the_trial_configuration():
    ctx, frame, helpers = setup()
    ctx = replace(ctx, delta_parts={"event": 0.0, "shock": 0.04, "stress": 0.04, "slow_trend": 0.0, "gamma": 0.0})
    assert decide(ctx, frame, AT, config_for("B0", {}), Consensus(0, 0), helpers, H, TODAY).delta == 0.0
    rv1 = decide(ctx, frame, AT, config_for("RV-1", {"X1": True, "RV-2": True}), Consensus(0, 0), helpers, H, TODAY)
    assert rv1.delta == pytest.approx(0.08)


def test_pass_rate_mode_needs_no_model():
    ctx, frame, helpers = setup()
    d = decide(ctx, frame, AT, config_for("B0", {}), None, helpers, H, TODAY)
    assert d.failed is None and d.p is None and d.choice is not None and d.alert is None


def test_decide_never_reads_beyond_at():
    ctx, frame, helpers = setup()
    full = decide(ctx, frame, AT, config_for("B0", {}), Consensus(0, 0), helpers, H, TODAY)
    cut = decide(ctx, frame[frame.ts <= AT - timedelta(minutes=1)], AT, config_for("B0", {}), Consensus(0, 0),
                 helpers, H, TODAY)
    assert full == cut
