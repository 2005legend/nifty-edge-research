"""Running the zero-trial pilots on real data: P1, P2, P4, P9, P10 and the D2 report.

None of these compute option P&L, win rates or R:
- P1 counts what passes each step
- P2 measures index excursions
- P9 and P4 measure the data
- P10 simulates

They are allowed before the registry exists (spec §6.3).
"""

import math
from datetime import date, datetime, time, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from quantdesk.analysis.bands import slot
from quantdesk.clock import IST
from quantdesk.derived.store import DerivedStore
from quantdesk.pricing.clock import load_clock
from quantdesk.pricing.fitting import clock_sessions
from quantdesk.pricing.quotes import ModelQuotes
from quantdesk.pricing.surface import load_surface
from quantdesk.strategy.configs import config_for
from quantdesk.strategy.daycard import DayLoader
from quantdesk.strategy.gates import Helpers
from quantdesk.strategy.pipeline import decide
from quantdesk.strategy.timeline import check_times
from quantdesk.strategy.trigger import h1
from quantdesk.validation.hypotheses import param
from quantdesk.validation.pilots.p2_excursions import excursions
from quantdesk.validation.pilots.p4_autocorr import ar1_mac5
from quantdesk.validation.pilots.p9_vwap import vwap_agreement
from quantdesk.validation.pilots.p10_power import power

P1_END = date(2025, 12, 31)
P2_END = date(2022, 12, 31)


def make_loader(derived: DerivedStore, h: dict, events: list, frozen: Path) -> DayLoader:
    import yaml

    holidays = {e.date for e in events if e.type == "holiday_nse"}
    clock = load_clock(frozen / "clock_v1.yaml", clock_sessions(derived, holidays))
    surface = load_surface(frozen / "surface_v1.yaml")
    shock = frozen / "shock_v1.yaml"
    shock_h = yaml.safe_load(shock.read_text(encoding="utf-8"))["h"] if shock.exists() else None
    return DayLoader(derived, clock, surface, h, events, shock_h=shock_h)


def vix_terciles(loader: DayLoader, start: date, end: date) -> dict[date, int]:
    vix = loader.daily["INDIAVIX"]["close"]
    prev = vix.shift(1)
    window = prev[(prev.index >= start) & (prev.index <= end)].dropna()
    lo, hi = np.quantile(window, [1 / 3, 2 / 3])
    return {d: (1 if v <= lo else 2 if v <= hi else 3) for d, v in window.items()}


D2_SCENARIO = {"account.capital": 15000, "account.risk_rupees": 600,
               "account.premium_budget": 14500}   # same ₹500 margin under capital as 9,500 at ₹10k (ruling)


# The owner's idea feed (22 Oct 2026): no rupee cap on the stop or the premium; the owner sizes each idea.
IDEAS_SCENARIO = {"account.risk_rupees": 1e9, "account.premium_budget": 1e9}


def with_values(h: dict, values: dict) -> dict:
    """A copy of the pre-registration with some values replaced; the registered file is untouched."""
    import copy

    out = copy.deepcopy(h)
    for key, value in values.items():
        out["parameters"][key]["value"] = value
    return out


def d2_scenario(h: dict) -> dict:
    """D2 option 1 (₹15k, ₹600 stop) for the zero-trial pilots only; the registered values are untouched."""
    return with_values(h, D2_SCENARIO)


def run_p1(loader: DayLoader, h: dict, today: date, end: date = P1_END, progress=None) -> tuple[pd.DataFrame, pd.DataFrame]:
    starts = {"NIFTY": date.fromisoformat(param(h, "backtest.nifty_from")),
              "SENSEX": date.fromisoformat(param(h, "backtest.sensex_from"))}
    terciles = vix_terciles(loader, starts["NIFTY"], end)
    cfg = config_for("B0", {})
    records, moves = [], []
    for day in loader.days:
        if day > end or loader.kind.get(day) != "regular":
            continue
        for index, start in starts.items():
            if day < start or (index, day) not in loader.expiries.index or index not in loader.daily:
                continue
            ctx = loader.day_context(index, day, z_refs=False)
            frame = loader.minute_frame(ctx)
            helpers = Helpers(loader.clock, loader.surface,
                              ModelQuotes({index: frame}, loader.surface, loader.clock, h))
            for at in check_times(day, ctx.is_expiry_day, h):
                d = decide(ctx, frame, at, cfg, None, helpers, h, today)
                if d.signal is None:
                    continue
                c = d.choice
                records.append({"day": day, "index": index, "at": at, "side": d.signal.side, "b": d.signal.b,
                                "failed": d.failed, "vix_tercile": terciles.get(day, 0), "lot": ctx.lot_1,
                                "p_be": c.p_be if c else np.nan, "gain": c.gain if c else np.nan,
                                "loss": c.loss if c else np.nan, "delta": c.delta if c else np.nan})
                if d.failed is None and day <= P2_END:
                    hard = datetime.combine(day, ctx.hard_exit, tzinfo=IST)
                    moves.append({"day": day, "index": index, **excursions(frame, d.signal, hard)})
        if progress:
            progress(day)
    return pd.DataFrame(records), pd.DataFrame(moves)


def eligible_days_per_year(records: pd.DataFrame, years=range(2020, 2026)) -> float:
    """Days with at least one eligible setup, across both indices: what one trade a day can take."""
    ok = records[records["failed"].isna()]
    per_year = ok.groupby(ok["day"].map(lambda d: d.year))["day"].nunique()
    return float(per_year.reindex(list(years), fill_value=0).mean())


def p2_summary(moves: pd.DataFrame) -> dict:
    if moves.empty:
        return {"setups": 0}
    peak_early = (moves["minutes_to_mfe"] <= 30) & (moves["retrace_after_mfe_b"] >= 1.0)
    return {"setups": int(len(moves)), "mfe_b_median": float(moves["mfe_b"].median()),
            "mae_b_median": float(moves["mae_b"].median()),
            "minutes_to_mfe_median": float(moves["minutes_to_mfe"].median()),
            "share_mfe_over_2_5b": float((moves["mfe_b"] > 2.5).mean()),
            "share_peak_within_30_then_revert": float(peak_early.mean()),
            "d1_reversal_clause": bool(peak_early.mean() > 0.5)}


def run_p10(records: pd.DataFrame, h: dict, n_trials: int = 5) -> dict:
    ok = records[records["failed"].isna()]
    per_year = min(eligible_days_per_year(records), param(h, "caps.per_year"))
    if ok.empty or per_year == 0:
        return {"p_all_gates": 0.0, "mde_80": None, "setups_per_year": per_year, "note": "no eligible setups"}
    risk = param(h, "account.risk_rupees")
    payoff = (float(ok["gain"].median() / risk), float(ok["loss"].median() / risk))
    base_p = float(ok["p_be"].median())
    return power(per_year, 7, 0.03, base_p, payoff, {"n_prior": param(h, "gate.n_prior"), "n_trials": n_trials},
                 h, n_sims=400, seed=20261022)


def run_p4(loader: DayLoader) -> dict:
    return ar1_mac5(loader.daily["NIFTY"]["close"], after=date(2016, 1, 1))


def _expiry_of(symbol: str) -> date | None:
    """NIFTY27OCT26FUT -> 27 Oct 2026."""
    try:
        return datetime.strptime(symbol.replace("NIFTY", "").replace("FUT", ""), "%d%b%y").date()
    except ValueError:
        return None


def run_p9(loader: DayLoader, h: dict) -> dict:
    derived = loader.derived
    targets = derived.read("minutes", where="target like 'NIFTY%FUT'", columns="distinct target")["target"]
    frames, futs, first_day = [], [], None
    for target in targets:
        expiry = _expiry_of(target)
        if expiry is None:
            continue
        fut = derived.read("minutes", where=f"target = '{target}'", columns="ts, day, high, low, close, volume")
        if fut.empty:
            continue
        futures = derived.read("options_eod", where=f"symbol = 'NIFTY' and instrument = 'IDF' and "
                                                    f"day >= DATE '{fut['day'].min()}'", columns="day, expiry")
        front_of = {d: min((e for e in g["expiry"] if e >= d), default=None) for d, g in futures.groupby("day")}
        before = [d for d in loader.days if d < expiry]
        last_two = set(before[-2:])
        # front month = the nearest futures expiry on the previous session's chain is this contract's
        front = [d for d in before if d not in last_two and front_of.get(loader.previous(d)) == expiry]
        for day in front:
            if loader.kind.get(day) != "regular":
                continue
            day_fut = fut[fut["day"] == day]
            if day_fut.empty or day_fut["volume"].sum() == 0:
                continue
            ctx = loader.day_context("NIFTY", day, with_refs=False)
            frame = loader.minute_frame(ctx, with_atm=False)
            frames.append(frame[["ts", "close", "vwap"]].assign(day=day))
            futs.append(day_fut)
            first_day = day if first_day is None else min(first_day, day)
    if not frames:
        return {"passed": False, "note": "no front-month futures minutes"}
    b = _median_b(loader, h, first_day)
    out = vwap_agreement(pd.concat(frames), pd.concat(futs), b)
    out["days"] = len(frames)
    return out


def _median_b(loader: DayLoader, h: dict, before: date, sessions: int = 250) -> float:
    """Median structural stop of H1 signals over the 250 regular sessions before the P9 window (no gates)."""
    days = [d for d in loader.days if d < before and loader.kind.get(d) == "regular"][-sessions:]
    bs = []
    for day in days:
        ctx = loader.day_context("NIFTY", day, with_refs=False)
        frame = loader.minute_frame(ctx, with_atm=False)
        for at in check_times(day, ctx.is_expiry_day, h):
            s = h1(frame, at, ctx, h)
            if s is not None:
                bs.append(s.b)
    return float(np.median(bs)) if bs else float("nan")
