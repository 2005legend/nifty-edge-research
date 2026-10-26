"""The strike picker, with the EV gate applied strike by strike (spec §6.1 steps 6-7, design §10 step 6).

Each candidate is priced three times:
- at entry, from the ask
- at the stop: the index 1.3 stops away, 15 minutes later, its vol moved by the spot-vol beta, sold 3
  half-spreads under the mid
- at the planning target: 60 minutes later, sold one half-spread under the mid

Costs are today's charges for every trade (spec §6.0). The breakeven probability is the strike's own,
L / (G + L), so a cheap far strike and a dear near one face different hurdles.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

import numpy as np

from quantdesk.clock import IST
from quantdesk.costs import round_trip
from quantdesk.pricing import black76_vec
from quantdesk.pricing.quotes import half_spread, sessions_left
from quantdesk.strategy.types import DayContext, Signal, StrikeChoice
from quantdesk.validation.hypotheses import param

CLOSE = time(15, 30)
STEP = {"NIFTY": 50, "SENSEX": 100}
EXCHANGE = {"NIFTY": "NSE", "SENSEX": "BSE"}


@dataclass(frozen=True)
class Candidate:
    index: str
    expiry: date
    strike: float
    kind: str
    lot: int
    ask: float
    delta: float
    gain: float
    loss: float
    target_premium: float | None = None


def _strike_grid(spot: float, step: int, side: str, otm_max: float, itm: int) -> list[float]:
    atm = round(spot / step) * step
    if side == "long":                                   # calls: ITM is below the index
        return [float(k) for k in np.arange(atm - itm * step, spot * (1 + otm_max) + 1e-9, step)]
    return [float(k) for k in np.arange(atm + itm * step, spot * (1 - otm_max) - 1e-9, -step)]


def candidates(signal: Signal, ctx: DayContext, helpers, h: dict, today: date) -> list[Candidate]:
    quotes, clock, surface = helpers.quotes, helpers.clock, helpers.surface
    at, spot = signal.at, signal.ref_close
    _, vix = quotes.state(ctx.index, at)
    kind = "CE" if signal.side == "long" else "PE"
    session_close = datetime.combine(at.date(), CLOSE, tzinfo=IST)
    t_stop = min(at + timedelta(minutes=param(h, "planning.stop_horizon_min")), session_close)
    t_target = min(at + timedelta(minutes=param(h, "planning.target_horizon_min")), session_close)
    sign = 1.0 if signal.side == "long" else -1.0
    s_stop = spot - sign * param(h, "stop.overshoot_factor") * signal.b
    s_target = signal.target_level
    scale_stop = surface.shifted(1.0, s_stop / spot - 1.0)
    scale_target = surface.shifted(1.0, s_target / spot - 1.0)
    exits = param(h, "stop.stop_exit_half_spreads")
    out = []
    for expiry, lot in ((ctx.expiry_1, ctx.lot_1), (ctx.expiry_2, ctx.lot_2)):
        if expiry is None or not lot or datetime.combine(expiry, CLOSE, tzinfo=IST) <= t_target:
            continue
        expiry_close = datetime.combine(expiry, CLOSE, tzinfo=IST)
        T = clock.bt(at, expiry_close)
        dte = sessions_left(clock, at.date(), expiry)
        for strike in _strike_grid(spot, STEP[ctx.index], signal.side, param(h, "strike.otm_max"),
                                   param(h, "strike.itm_strikes")):
            ask = quotes.quote(ctx.index, expiry, strike, kind, at).ask
            sigma = surface.sigma(at, expiry_close, spot, [strike], vix, clock, dte)[0]
            delta = float(black76_vec.delta(spot, strike, T, sigma, "call" if kind == "CE" else "put"))
            mid_stop = quotes.mid(ctx.index, expiry, strike, kind, t_stop, spot=s_stop, vix=vix, sigma_scale=scale_stop)
            mid_tgt = quotes.mid(ctx.index, expiry, strike, kind, t_target, spot=s_target, vix=vix, sigma_scale=scale_target)
            p_stop = max(mid_stop - exits * half_spread(ctx.index, mid_stop, t_stop, h), 0.05)
            p_tgt = max(mid_tgt - half_spread(ctx.index, mid_tgt, t_target, h), 0.05)
            exchange = EXCHANGE[ctx.index]
            loss = (ask - p_stop) * lot + round_trip(ask, p_stop, lot, exchange=exchange, day=today).total
            gain = (p_tgt - ask) * lot - round_trip(ask, p_tgt, lot, exchange=exchange, day=today).total
            out.append(Candidate(ctx.index, expiry, strike, kind, int(lot), ask, delta, gain, loss, round(p_tgt, 2)))
    return out


def pick(cands: list[Candidate], p: float | None, delta: float, h: dict, evaluate_ev: bool = True) -> StrikeChoice | None:
    budget, buffer = param(h, "account.premium_budget"), param(h, "account.fixed_cost_buffer")
    risk, capital = param(h, "account.risk_rupees"), param(h, "account.capital")
    kept = []
    for c in cands:
        if c.ask * c.lot + buffer > budget or not 0 < c.loss <= risk or c.gain <= 0:
            continue
        if c.gain / c.loss < param(h, "strike.gain_loss_min"):
            continue
        if not param(h, "strike.delta_min") <= abs(c.delta) <= param(h, "strike.delta_max"):
            continue
        p_be = c.loss / (c.gain + c.loss)
        if evaluate_ev:
            ev = p * c.gain - (1 - p) * c.loss
            kelly = p - (1 - p) * c.loss / c.gain
            if p < p_be + param(h, "ev.margin") + delta:
                continue
            if ev < max(param(h, "ev.min_r") * risk, param(h, "ev.min_rupees")) or kelly < c.loss / capital:
                continue
        else:
            ev, kelly = float("nan"), float("nan")
        kept.append(StrikeChoice(c.index, c.expiry, c.strike, c.kind, c.lot, c.ask, c.delta, c.gain, c.loss,
                                 p_be, ev, kelly, c.target_premium))
    if not kept:
        return None
    key = lambda s: ((-s.ev if evaluate_ev else 0.0), s.index != "NIFTY", s.expiry, abs(abs(s.delta) - 0.40))
    return sorted(kept, key=key)[0]
