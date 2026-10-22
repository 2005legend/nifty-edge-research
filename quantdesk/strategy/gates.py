"""The seven pre-trade gates, in spec order (spec §6.1 step 4, design §10). The first that fails names the reason.

Each gate is `(signal, ctx, frame, helpers, h) -> bool` and reads only rows stamped before the decision. Inputs
that are still warming up (no HAR forecast, no volatility threshold, no spike reference) never reach a gate:
`decide()` reports them as `warmup` first (R12).
"""

import math
from dataclasses import dataclass
from datetime import datetime, time, timedelta

import pandas as pd

from quantdesk.analysis.bands import slot
from quantdesk.analysis.breadth import breadth_agrees
from quantdesk.analysis.levels import opposing_levels
from quantdesk.analysis.macro import event_block, vix_block
from quantdesk.clock import IST
from quantdesk.pricing import black76_vec
from quantdesk.pricing.clock import Clock
from quantdesk.pricing.quotes import sessions_left
from quantdesk.pricing.surface import Surface, sigma_bt
from quantdesk.strategy.types import DayContext, Signal
from quantdesk.validation.hypotheses import param

CLOSE = time(15, 30)
STRIKE_STEP = {"NIFTY": 50, "SENSEX": 100}


@dataclass(frozen=True)
class Helpers:
    clock: Clock
    surface: Surface
    quotes: object | None = None


def _row(frame: pd.DataFrame, at: datetime) -> pd.Series:
    rows = frame[frame["ts"] == at - timedelta(minutes=1)]
    return rows.iloc[-1]


def _sigma_now(signal: Signal, frame: pd.DataFrame, helpers: Helpers) -> float:
    return sigma_bt(float(_row(frame, signal.at)["vix"]), signal.at, helpers.clock)


def gate_event_shock(signal, ctx: DayContext, frame, helpers, h) -> bool:
    if event_block(ctx.events, signal.at, h) is not None:
        return False
    return not vix_block(float(_row(frame, signal.at)["vix"]), ctx.vix_prev_close, param(h, "gate.intraday_vix_band"))


def gate_stop_fit(signal, ctx, frame, helpers, h) -> bool:
    """The structural cap of R19; the rupee fit is checked per strike by the picker."""
    one_session = signal.ref_close * _sigma_now(signal, frame, helpers)
    return 0 < signal.b <= param(h, "stop.max_daily_move_fraction") * one_session


def atm_drag(signal: Signal, ctx: DayContext, frame: pd.DataFrame, helpers: Helpers, h: dict) -> float:
    """Index points the nearest-weekly ATM option loses to time over the planning horizon (design §10 step 4.3)."""
    clock, at = helpers.clock, signal.at
    expiry = ctx.expiry_1 if datetime.combine(ctx.expiry_1, CLOSE, tzinfo=IST) > at else ctx.expiry_2
    expiry_close = datetime.combine(expiry, CLOSE, tzinfo=IST)
    spot, vix = signal.ref_close, float(_row(frame, at)["vix"])
    step = STRIKE_STEP[ctx.index]
    strike = round(spot / step) * step
    kind = "call" if signal.side == "long" else "put"
    sigma = helpers.surface.sigma(at, expiry_close, spot, [strike], vix, clock, sessions_left(clock, at.date(), expiry))[0]
    T = clock.bt(at, expiry_close)
    horizon = min(at + timedelta(minutes=param(h, "planning.target_horizon_min")),
                  datetime.combine(at.date(), CLOSE, tzinfo=IST))
    theta = float(black76_vec.theta_bt(spot, strike, T, sigma, kind))
    delta = abs(float(black76_vec.delta(spot, strike, T, sigma, kind)))
    return theta * clock.bt(at, horizon) / max(delta, 1e-6)


def gate_room_in_time(signal, ctx, frame, helpers, h) -> bool:
    remaining = max(0.0, 1.0 - helpers.clock.w_done(signal.at))
    sigma_rem_pts = ctx.sigma_day * math.sqrt(remaining) * ctx.open
    need = param(h, "gate.room_in_time_multiplier") * (abs(signal.target_level - signal.ref_close)
                                                       + atm_drag(signal, ctx, frame, helpers, h))
    return param(h, "gate.room_in_time_range_factor") * sigma_rem_pts >= need


def gate_room_to_run(signal, ctx, frame, helpers, h) -> bool:
    return not opposing_levels(ctx, frame, signal, h)


def gate_volatility(signal, ctx, frame, helpers, h) -> bool:
    return _sigma_now(signal, frame, helpers) / ctx.sigma_day <= ctx.vol_rich_threshold


def gate_confirmation(signal, ctx, frame, helpers, h) -> bool:
    return breadth_agrees(_row(frame, signal.at), signal.side, param(h, "gate.breadth_agree_min"))


def gate_spike_guard(signal, ctx, frame, helpers, h) -> bool:
    if ctx.spike_ref is None:
        return True
    window = param(h, "gate.spike_window_min")
    seen = frame[frame["ts"] <= signal.at - timedelta(minutes=1)].sort_values("ts").tail(window + 1)
    changes = seen["atm_premium"].diff().abs()
    multiple = param(h, "gate.spike_multiple")
    for ts, change in zip(seen["ts"].iloc[1:], changes.iloc[1:]):
        ref = ctx.spike_ref[slot(ts)]
        if not math.isnan(change) and not math.isnan(ref) and change > multiple * ref:
            return False
    return True


GATES = (("event_shock", gate_event_shock), ("stop_fit", gate_stop_fit), ("room_in_time", gate_room_in_time),
         ("room_to_run", gate_room_to_run), ("volatility", gate_volatility), ("confirmation", gate_confirmation),
         ("spike_guard", gate_spike_guard))


def first_failed_gate(signal: Signal, ctx: DayContext, frame: pd.DataFrame, helpers: Helpers, h: dict) -> str | None:
    """`gate.skip` exists only in the owner's relaxed idea settings, never in the pre-registration."""
    skip = set(((h.get("parameters") or {}).get("gate.skip") or {}).get("value") or [])
    for name, gate in GATES:
        if name in skip:
            continue
        if not gate(signal, ctx, frame, helpers, h):
            return name
    return None
