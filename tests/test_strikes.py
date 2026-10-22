from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from quantdesk.clock import IST
from quantdesk.pricing.quotes import ModelQuotes
from quantdesk.strategy.gates import Helpers
from quantdesk.strategy.strikes import Candidate, candidates, pick
from quantdesk.strategy.types import Signal
from quantdesk.validation.hypotheses import load_hypotheses
from tests.derived_fixture import clock_for, flat_surface, session_days
from tests.test_bands import make_ctx

H = load_hypotheses()


def test_the_ev_gate_uses_the_breakeven_of_each_strike():
    c = Candidate("NIFTY", date(2024, 3, 7), 22000.0, "CE", 50, ask=60.0, delta=0.4, gain=800.0, loss=380.0)
    # p_be = 380 / 1180 = 0.322; need p >= 0.322 + 0.04 + 0.0 = 0.362
    assert pick([c], p=0.35, delta=0.0, h=H) is None
    choice = pick([c], p=0.44, delta=0.0, h=H)
    assert choice.ev == pytest.approx(0.44 * 800 - 0.56 * 380)      # 139.2 >= max(0.10 x 400, 75)
    assert choice.p_be == pytest.approx(380 / 1180) and choice.kelly == pytest.approx(0.44 - 0.56 * 380 / 800)


def test_the_hurdle_raises_the_probability_needed():
    c = Candidate("NIFTY", date(2024, 3, 7), 22000.0, "CE", 50, ask=60.0, delta=0.4, gain=800.0, loss=380.0)
    assert pick([c], p=0.40, delta=0.04, h=H) is None and pick([c], p=0.41, delta=0.04, h=H) is not None


def test_affordability_and_delta_bounds_are_never_relaxed():
    pricey = Candidate("NIFTY", date(2024, 3, 7), 22000.0, "CE", 75, ask=130.0, delta=0.5, gain=900.0, loss=390.0)
    deep = Candidate("NIFTY", date(2024, 3, 7), 21500.0, "CE", 50, ask=60.0, delta=0.70, gain=900.0, loss=390.0)
    assert pick([pricey, deep], p=0.9, delta=0.0, h=H) is None   # 130*75+60 > 9500; delta > 0.55


def test_loss_and_payoff_ratio_filters():
    big_loss = Candidate("NIFTY", date(2024, 3, 7), 22000.0, "CE", 50, 60.0, 0.4, 900.0, 410.0)
    thin = Candidate("NIFTY", date(2024, 3, 7), 22000.0, "CE", 50, 60.0, 0.4, 500.0, 380.0)   # G/L 1.3
    assert pick([big_loss, thin], p=0.9, delta=0.0, h=H) is None


def test_ties_go_to_nifty_then_nearer_expiry_then_delta_near_040():
    a = Candidate("SENSEX", date(2024, 3, 8), 73000.0, "CE", 10, 200.0, 0.40, 800.0, 380.0)
    b = Candidate("NIFTY", date(2024, 3, 14), 22000.0, "CE", 50, 60.0, 0.40, 800.0, 380.0)
    c = Candidate("NIFTY", date(2024, 3, 7), 22050.0, "CE", 50, 60.0, 0.30, 800.0, 380.0)
    d = Candidate("NIFTY", date(2024, 3, 7), 22000.0, "CE", 50, 60.0, 0.41, 800.0, 380.0)
    assert pick([a, b, c, d], p=0.6, delta=0.0, h=H).strike == 22000.0


def test_pass_rate_mode_skips_the_probability_filters():
    c = Candidate("NIFTY", date(2024, 3, 7), 22000.0, "CE", 50, ask=60.0, delta=0.4, gain=800.0, loss=380.0)
    assert pick([c], p=None, delta=0.0, h=H, evaluate_ev=False).strike == 22000.0


def test_candidates_price_calls_from_one_itm_to_one_and_a_half_percent_otm():
    days = session_days(60)
    clock = clock_for(days)
    at = datetime(2024, 3, 5, 10, 0, tzinfo=IST)
    frame = pd.DataFrame({"ts": [at - timedelta(minutes=1)], "close": [22010.0], "vix": [14.0]})
    helpers = Helpers(clock=clock, surface=flat_surface(), quotes=ModelQuotes({"NIFTY": frame}, flat_surface(), clock, H))
    ctx = make_ctx(np.full(375, 0.002), day=date(2024, 3, 5), expiry_1=date(2024, 3, 7), expiry_2=date(2024, 3, 14),
                   lot_1=50, lot_2=50)
    sig = Signal("NIFTY", at, "long", 22010.0, 21990.0, 21960.0, 21995.0, 21990.0, 20.0, 22056.0)
    cands = candidates(sig, ctx, helpers, H, today=date(2026, 10, 22))
    strikes = sorted({c.strike for c in cands if c.expiry == date(2024, 3, 7)})
    assert strikes[0] == 21950.0 and strikes[-1] <= 22010.0 * 1.015 and all(c.kind == "CE" for c in cands)
    atm = [c for c in cands if c.strike == 22000.0 and c.expiry == date(2024, 3, 7)][0]
    assert 0.4 < atm.delta < 0.6 and atm.loss > 0 and atm.gain > 0
