import math
from datetime import date, datetime, time

import numpy as np
import pandas as pd
import pytest

from quantdesk.backtest.straddles import evaluate, straddle_study
from quantdesk.black76 import black76
from quantdesk.clock import IST
from quantdesk.pricing.clock import Clock
from quantdesk.validation.hypotheses import load_hypotheses
from quantdesk.vol.ivsurface import atm_strike, chain_ivs

H = load_hypotheses()
D0, D1, D2 = date(2024, 3, 4), date(2024, 3, 5), date(2024, 3, 6)
NEAR, NEXT = date(2024, 3, 5), date(2024, 3, 7)            # NEAR expires on the exit day: never chosen
DAYS = tuple(date(2024, 3, 1) + pd.Timedelta(days=k).to_pytimedelta() for k in range(40)
             if (date(2024, 3, 1) + pd.Timedelta(days=k).to_pytimedelta()).weekday() < 5)
CLOCK = Clock(np.full(375, 1 / 375), 0.5, 0.2, 0.2, DAYS)


def T(day, expiry):
    return CLOCK.bt(datetime.combine(day, time(15, 30), tzinfo=IST), datetime.combine(expiry, time(15, 30), tzinfo=IST))


def chain(day, F, sigma, expiries=(NEAR, NEXT), strikes=range(21800, 22250, 50), traded=True):
    rows = []
    for e in [x for x in expiries if x > day]:                                 # an expired contract is not listed
        for k in strikes:
            for kind, flag in (("CE", "call"), ("PE", "put")):
                rows.append({"day": day, "expiry": e, "strike": float(k), "option_type": kind, "lot": 50,
                             "close": round(black76(F, float(k), T(day, e), sigma, kind=flag), 2), "traded": traded})
    return pd.DataFrame(rows)


def test_the_solver_recovers_the_volatility_the_chain_was_priced_at():
    rows = chain(D0, 22010.0, 0.15)
    k = atm_strike(rows[rows["expiry"] == NEXT])
    assert k == 22000.0
    ivs = chain_ivs(rows[rows["expiry"] == NEXT], F=22010.0, T=T(D0, NEXT))
    assert len(ivs) == 9 and ivs["iv"].sub(0.15).abs().max() < 2e-3          # one OTM option per strike


def test_the_study_takes_the_expiry_after_the_exit_day_and_charges_every_leg():
    eod = {D0: chain(D0, 22010.0, 0.15), D1: chain(D1, 22200.0, 0.15), D2: chain(D2, 22100.0, 0.15)}
    har = pd.DataFrame({"rv_hat_nogap": [1e-4, 1e-4, 1e-4]}, index=[D0, D1, D2])
    rows = straddle_study(eod, har, CLOCK, H, today=date(2026, 10, 26))
    first = rows.iloc[0]
    assert first["expiry"] == NEXT and first["strike"] == 22000.0 and first["exit_day"] == D1
    assert first["iv"] == pytest.approx(0.15, abs=2e-3)
    implied = 0.15 ** 2 * T(D0, D1)
    assert first["rho"] == pytest.approx(implied / (1e-4 * (1 + CLOCK.theta_night)), rel=0.03)
    gross = 50 * sum(eod[D1].query("expiry == @NEXT and strike == 22000.0")["close"]) - first["premium"]
    assert first["pnl"] < gross                                                # charges and spreads are paid
    assert first["signal"] == (first["rho"] < 1.0)


def test_a_leg_that_did_not_trade_on_either_day_is_skipped():
    d1 = chain(D1, 22200.0, 0.15)
    d1.loc[(d1["strike"] == 22000.0) & (d1["option_type"] == "PE"), "traded"] = False
    rows = straddle_study({D0: chain(D0, 22010.0, 0.15), D1: d1}, pd.DataFrame({"rv_hat_nogap": [1e-4, 1e-4]},
                          index=[D0, D1]), CLOCK, H, today=date(2026, 10, 26))
    assert rows.empty or (rows["strike"] != 22000.0).all()


def test_the_gates_follow_the_preregistration():
    rng = np.random.default_rng(5)
    days = pd.bdate_range("2019-03-01", "2026-06-30").date
    rows = pd.DataFrame({"day": days, "signal": rng.random(len(days)) < 0.3,
                         "ret": rng.normal(-0.05, 0.3, len(days))})
    rows.loc[rows["signal"], "ret"] += 0.12                                   # a planted edge on signal days
    g = evaluate(rows)
    assert g["gates"]["mean_positive_t2"] and g["gates"]["beats_baseline"] and g["passed"]
    assert set(g["by_year"]) >= {2020, 2025} and g["touched_2026"]["n"] > 0
    flat = rows.assign(ret=rng.normal(-0.05, 0.3, len(days)))
    assert not evaluate(flat)["passed"]
