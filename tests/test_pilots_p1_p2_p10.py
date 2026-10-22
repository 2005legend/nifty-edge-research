from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from quantdesk.clock import IST
from quantdesk.strategy.types import Signal
from quantdesk.validation.hypotheses import load_hypotheses
from quantdesk.validation.pilots.p1_pass_rates import pass_rates
from quantdesk.validation.pilots.p2_excursions import excursions
from quantdesk.validation.pilots.p10_power import d2_report, power
from quantdesk.validation.stats import deflated_sharpe

H = load_hypotheses()


def rec(day, failed, tercile, lot=50, index="NIFTY"):
    return {"day": day, "index": index, "failed": failed, "vix_tercile": tercile, "lot": lot}


def test_pass_rates_by_tercile():
    d = date(2021, 3, 1)
    rows = [rec(d, None, 1), rec(d, "stop_fit", 1), rec(d, "no_strike", 2), rec(d, None, 2),
            rec(d, "stop_fit", 3), rec(d, "stop_fit", 3), rec(d, "warmup", 3)]
    out = pass_rates(pd.DataFrame(rows)).set_index("vix_tercile")
    assert out.loc[1, "signals"] == 2 and out.loc[1, "stop_fit_rate"] == 0.5 and out.loc[1, "eligible"] == 1
    assert out.loc[2, "stop_fit_rate"] == 1.0 and out.loc[2, "picker_rate"] == 0.5
    assert out.loc[3, "stop_fit_rate"] == 0.0 and out.loc[3, "signals"] == 2      # warm-up is not a signal


def test_excursions_of_a_known_path():
    ts = [datetime(2021, 3, 1, 10, 0, tzinfo=IST) + timedelta(minutes=i) for i in range(30)]
    closes = [100.0 + 0.2 * min(i, 10) - 0.3 * max(0, i - 10) for i in range(30)]     # +2b at 10, then -1b by 20
    closes = [c if i <= 20 else closes[20] for i, c in enumerate(closes)]
    frame = pd.DataFrame({"ts": ts, "close": closes})
    sig = Signal("NIFTY", ts[0], "long", 100.0, 99.0, 98.0, 99.0, 99.0, 1.0, 102.3)
    out = excursions(frame, sig, hard_exit_at=ts[-1])
    assert out["mfe_b"] == pytest.approx(2.0) and out["minutes_to_mfe"] == 10
    assert out["retrace_after_mfe_b"] == pytest.approx(3.0) and out["mae_b"] == pytest.approx(1.0)


def test_dsr_formula_on_a_fixed_input():
    # SR 0.1 per period, 1000 periods, normal returns, 10 trials with SR variance 0.04^2
    out = deflated_sharpe(sr=0.1, T=1000, skew=0.0, kurt=3.0, n_trials=10, var_sr=0.04 ** 2)
    from scipy.stats import norm
    g = 0.5772156649
    sr0 = 0.04 * ((1 - g) * norm.ppf(1 - 1 / 10) + g * norm.ppf(1 - 1 / (10 * np.e)))
    assert out == pytest.approx(norm.cdf((0.1 - sr0) * np.sqrt(999) / np.sqrt(1 + 0.5 * 0.01)))


def test_power_is_low_without_uplift():
    out = power(setups_per_year=60, years=6, uplift=0.0, base_p=0.4, payoff=(1.5, 1.0),
                gates={"n_prior": 46, "n_trials": 5}, h=H, n_sims=500, seed=1)
    assert out["p_all_gates"] < 0.05


def test_power_rises_with_uplift():
    out = power(setups_per_year=300, years=5, uplift=0.10, base_p=0.4, payoff=(1.5, 1.0),
                gates={"n_prior": 46, "n_trials": 5}, h=H, n_sims=300, seed=2)
    assert out["p_all_gates"] > 0.5


def test_d2_triggers_below_60_setups():
    p1 = pd.DataFrame({"year": [2020, 2021], "vix_tercile": [1, 3], "lot": 50, "signals": [100, 100],
                       "stop_fit_pass": [60, 50], "picker_pass": [20, 20], "eligible": [40, 40],
                       "stop_fit_rate": [0.6, 0.5], "picker_rate": [0.33, 0.4]})
    text = d2_report(p1, {"mfe_b_median": 1.2}, {"p_all_gates": 0.1, "mde_80": 0.08}, H)
    assert "D2 checkpoint: triggered" in text and "15,000" in text
