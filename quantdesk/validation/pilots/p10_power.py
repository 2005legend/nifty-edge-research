"""P10: could the registry's gates pass at all, given how many setups there are? (R35)

Simulated trades win with probability breakeven + uplift and pay the median strike's payoff. The same t, year
and deflated-Sharpe gates are applied, with N = 46 earlier looks + trials. The answer goes to the owner at the
D2 checkpoint, before any trial is spent.
"""

import math

import numpy as np
import pandas as pd

from quantdesk.validation.hypotheses import param
from quantdesk.validation.stats import deflated_sharpe, sharpe_stats

GRID = [round(0.01 * k, 2) for k in range(1, 21)]


def _simulate(setups_per_year, years, p, payoff, gates, h, n_sims, rng):
    gain, loss = payoff
    n = max(int(round(setups_per_year * years)), 2)
    r = np.where(rng.random((n_sims, n)) < p, gain, -loss)
    t_min, dsr_min = param(h, "gate.t_min"), param(h, "gate.dsr_min")
    n_trials = gates["n_prior"] + gates["n_trials"]
    floor = param(h, "gate.dsr_sr_sd_floor") ** 2
    groups = np.array_split(np.arange(n), years)
    need = math.ceil(param(h, "gate.years_positive_min") / 6.0 * min(years, 6))
    ok_t = ok_dsr = ok_all = 0
    for row in r:
        sd = row.std(ddof=1)
        t = row.mean() / sd * math.sqrt(n) if sd > 0 else 0.0
        sr, skew, kurt = sharpe_stats(row)
        dsr = deflated_sharpe(sr, n, skew, kurt, n_trials, floor) if not math.isnan(sr) else 0.0
        years_ok = sum(row[g].mean() > 0 for g in groups[-6:]) >= need
        ok_t += t >= t_min
        ok_dsr += dsr >= dsr_min
        ok_all += t >= t_min and dsr >= dsr_min and years_ok
    return ok_all / n_sims, ok_t / n_sims, ok_dsr / n_sims


def power(setups_per_year: float, years: int, uplift: float, base_p: float, payoff: tuple, gates: dict, h: dict,
          n_sims: int, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    p_all, p_t, p_dsr = _simulate(setups_per_year, years, base_p + uplift, payoff, gates, h, n_sims, rng)
    mde = None
    for u in GRID:
        if _simulate(setups_per_year, years, base_p + u, payoff, gates, h, max(n_sims // 4, 50), rng)[0] >= 0.8:
            mde = u
            break
    return {"p_all_gates": p_all, "p_t": p_t, "p_dsr": p_dsr, "mde_80": mde, "setups_per_year": setups_per_year,
            "years": years, "uplift": uplift, "base_p": base_p, "gain_R": payoff[0], "loss_R": payoff[1]}


def _fmt(value) -> str:
    return f"{value:.3g}" if isinstance(value, float) else str(value)


def d2_report(p1: pd.DataFrame, p2: dict, p10: dict, h: dict) -> str:
    per_year = p1.groupby("year")["eligible"].sum()
    eligible = float(per_year.mean()) if len(per_year) else 0.0

    def rate(tercile):
        rows = p1[p1["vix_tercile"] == tercile]
        total = rows["signals"].sum()
        return float((rows["stop_fit_rate"] * rows["signals"]).sum() / total) if total else float("nan")

    low, high = rate(1), rate(3)
    few = eligible < 60
    skewed = not math.isnan(low) and not math.isnan(high) and high < 0.5 * low
    triggered = few or skewed
    p2_text = ", ".join(f"{k} {_fmt(v)}" for k, v in p2.items())
    lines = ["# D2 checkpoint (spec §6.3)", "",
             f"- Eligible setups a year (P1, mean over years): **{eligible:.0f}** (threshold about 60)",
             f"- Stop-fit pass rate, low-VIX tercile {low:.2f} vs high-VIX tercile {high:.2f} (trigger if high < half of low)",
             f"- P2: {p2_text}",
             f"- P10: chance every gate passes at the planned uplift {_fmt(p10.get('p_all_gates'))}; "
             f"smallest uplift with 80% power: {p10.get('mde_80')}", "",
             f"**D2 checkpoint: {'triggered' if triggered else 'not triggered'}.**", ""]
    if triggered:
        lines += ["The owner chooses, before go-live (spec §6.3 D2):",
                  "1. Raise capital to ₹15,000 with a ₹600 stop (still 4% risk). This widens stop room and lifts setups.",
                  "2. Alert-off: the system keeps recording, logging setups in shadow and running the desk."]
    lines += ["", "The owner also decides on X2 (the VWAP-runner exit): run it as a trial, or not (R3)."]
    return "\n".join(lines) + "\n"
