"""Running the frozen fits on the derived tables: the clock and the surface (design §7-§8, plan 1 task 16).

These are the only places that read 2019-2022 to set numbers the backtest later uses. Every number comes
back with the data hash it was fitted on, so a later rebuild can show the fit is the one the trials saw.
"""

from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

from quantdesk.clock import IST
from quantdesk.derived.store import DerivedStore
from quantdesk.pricing.clock import MINUTES, Clock
from quantdesk.pricing.clockfit import atm_implied_variance, fit_minute_weights, fit_theta_night, fit_weekend_holiday
from quantdesk.pricing.surface import Surface, fifteen_minute_windows, fit_surface, future_sessions
from quantdesk.validation.hypotheses import param

HORIZON_DAYS = 400   # future sessions the clock needs: VIX's 30 days and the next expiries, with room to spare


def _window(h: dict) -> tuple[date, date]:
    return date.fromisoformat(param(h, "clock.fit_start")), date.fromisoformat(param(h, "clock.fit_end"))


def clock_sessions(derived: DerivedStore, holidays: set[date]) -> tuple:
    """Recorded sessions of any kind, then the published calendar ahead (time passes on irregular days too)."""
    past = sorted(derived.read("sessions", columns="day")["day"])
    return future_sessions(past, holidays, past[-1] + timedelta(days=HORIZON_DAYS))


def _between(start: date, end: date) -> str:
    return f"day >= DATE '{start}' and day <= DATE '{end}'"


def fit_clock_from(derived: DerivedStore, h: dict, holidays: set[date]) -> tuple[Clock, dict, str]:
    start, end = _window(h)
    window = _between(start, end)
    sessions = derived.read("sessions", where=window)
    regular = set(sessions.loc[sessions["kind"] == "regular", "day"])
    minutes = derived.read("minutes", where=f"target = 'NIFTY' and {window}", columns="ts, day, close")
    minutes = minutes[minutes["day"].isin(regular)]
    daily = derived.read("daily", where=f"target = 'NIFTY' and {window}")
    opens = daily.set_index("day")["open"]
    weights = fit_minute_weights(minutes, opens, param(h, "clock.weight_winsor_q"))
    theta_n = fit_theta_night(daily[daily["day"].isin(regular)], sorted(regular))
    all_sessions = clock_sessions(derived, holidays)
    eod = derived.read("options_eod", where=f"symbol = 'NIFTY' and {window}")
    vix = derived.read("daily", where=f"target = 'INDIAVIX' and {window}").set_index("day")["close"]
    vt = atm_implied_variance(eod, vix, param(h, "clock.atm_dte"), all_sessions)
    gaps = fit_weekend_holiday(vt, all_sessions, theta_n)
    clock = Clock(weights, theta_n, gaps["theta_weekend_day"], gaps["theta_holiday"], all_sessions)
    meta = {"fit_window": f"{start}..{end}", "data_hash": derived.data_hash(),
            "fitted_at": datetime.now(IST).isoformat(timespec="seconds"),
            "overnight_share": theta_n / (1 + theta_n), "se_weekend": gaps["se_weekend"],
            "se_holiday": gaps["se_holiday"], "n_pairs": gaps["n"], "n_days": len(regular)}
    return clock, meta, clock_report(clock, meta)


def clock_report(clock: Clock, meta: dict) -> str:
    blocks = clock.minute_weights.reshape(MINUTES // 15, 15).sum(axis=1)
    lines = ["# CLOCK: business-time weights fitted on " + meta["fit_window"], "",
             f"- data_hash `{meta['data_hash']}`, fitted {meta['fitted_at']}, {meta['n_days']} regular sessions",
             f"- theta_night {clock.theta_night:.4f} (overnight share {meta['overnight_share']:.3f}; research measured 0.38-0.43)",
             f"- theta_weekend_day {clock.theta_weekend_day:.4f} ± {meta['se_weekend']:.4f}",
             f"- theta_holiday {clock.theta_holiday:.4f} ± {meta['se_holiday']:.4f} ({meta['n_pairs']} implied-variance pairs)",
             "", "| 15 minutes from | share of a session's variance |", "|---|---|"]
    for i, share in enumerate(blocks):
        at = datetime(2000, 1, 1, 9, 15) + timedelta(minutes=15 * i)
        lines.append(f"| {at:%H:%M} | {share:.4f} |")
    return "\n".join(lines) + "\n"


def fit_surface_from(derived: DerivedStore, h: dict, clock: Clock) -> tuple[Surface, dict, str]:
    start, end = _window(h)
    window = _between(start, end)
    sessions = derived.read("sessions", where=window)
    regular = set(sessions.loc[sessions["kind"] == "regular", "day"])
    eod = derived.read("options_eod", where=f"symbol = 'NIFTY' and {window}")
    vix = derived.read("daily", where=f"target = 'INDIAVIX' and {window}").set_index("day")["close"]
    index_minutes = derived.read("minutes", where=f"target = 'NIFTY' and {window}", columns="ts, day, close")
    vix_minutes = derived.read("minutes", where=f"target = 'INDIAVIX' and {window}", columns="ts, day, close")
    windows = fifteen_minute_windows(index_minutes[index_minutes["day"].isin(regular)],
                                     vix_minutes[vix_minutes["day"].isin(regular)])
    surface, fit = fit_surface(eod, vix, clock, windows, dte=param(h, "clock.fit_dte"),
                               max_abs_z=param(h, "pricing.skew_max_abs_z"), floor=param(h, "pricing.skew_floor"))
    meta = {"fit_window": f"{start}..{end}", "data_hash": derived.data_hash(),
            "fitted_at": datetime.now(IST).isoformat(timespec="seconds"), **fit}
    lines = ["", "## Surface", "",
             "| dte | R(dte) | ATM pairs |", "|---|---|---|"]
    lines += [f"| {d} | {surface.r_dte[d]:.4f} | {fit['n_atm'].get(d, 0)} |" for d in sorted(surface.r_dte)]
    lines += ["", f"- skew b1 {surface.b1:.4f}, b2 {surface.b2:.4f} ({fit['n_skew']} strikes, |z| <= {surface.max_abs_z})",
              f"- spot-vol beta: gamma_dn {surface.gamma_dn:.3f} ({fit['n_windows_down']} windows), "
              f"gamma_up {surface.gamma_up:.3f} ({fit['n_windows_up']} windows)"]
    return surface, meta, "\n".join(lines) + "\n"
