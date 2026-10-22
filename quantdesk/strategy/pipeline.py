"""decide(): from market data up to a check time to an alert, or to the named reason there is none (spec §6.1).

The order is the spec's:
1. timeline and session
2. H1
3. warm-up (R12)
4. the seven gates
5. probability
6. the strike picker with the per-strike EV gate
7. the alert

The function is pure. The backtester and the live engine call it the same way, which is what the parity test
(SP3) checks.

With `model=None` it runs in pass-rate mode for pilot P1: everything up to the picker, without the probability
filters, and no alert.
"""

import math
from datetime import datetime, timedelta

import pandas as pd

from quantdesk.analysis.levels import nearest_opposing_distance
from quantdesk.analysis.technical import technical_raw, technical_score
from quantdesk.analysis.zscore import causal_z
from quantdesk.strategy.gates import first_failed_gate
from quantdesk.strategy.meta import Consensus, MetaModel, columns
from quantdesk.strategy.strikes import candidates, pick
from quantdesk.strategy.timeline import timeline_block
from quantdesk.strategy.trigger import h1
from quantdesk.strategy.types import Alert, DayContext, Decision, TrialConfig
from quantdesk.validation.hypotheses import param

TICK = 0.05


def _warm(ctx: DayContext) -> bool:
    return (not math.isnan(ctx.sigma_day) and ctx.vol_rich_threshold is not None and ctx.spike_ref is not None
            and ctx.har_pct is not None and ctx.expiry_1 is not None)


def _options_score(ctx: DayContext, sign: float, h: dict) -> float | None:
    if not ctx.options_raw:
        return None
    min_n, winsor = param(h, "meta.zscore_min_sessions"), param(h, "meta.winsor")
    zs = [causal_z(ctx.options_raw.get(f, math.nan), ctx.z_refs.get((f, "day")), min_n, winsor) for f in ("pcr", "rr25")]
    zs = [z for z in zs if z is not None]
    return sign * sum(zs) / len(zs) if zs else None


def family_scores(ctx: DayContext, frame: pd.DataFrame, signal, h: dict) -> dict:
    sign = 1.0 if signal.side == "long" else -1.0
    row = frame[frame["ts"] == signal.at - timedelta(minutes=1)].iloc[-1]
    raw = technical_raw(row, signal, nearest_opposing_distance(ctx, frame, signal, h))
    return {"technical": technical_score(raw, ctx.z_refs, signal.at.strftime("%H:%M"), h),
            "options": _options_score(ctx, sign, h), "macro": sign * ctx.macro_raw, "raw": raw}


def _delta(ctx: DayContext, cfg: TrialConfig, h: dict) -> float:
    parts = ctx.delta_parts or {}
    total = parts.get("event", 0.0) + sum(parts.get(name, 0.0) for name in cfg.hurdles)
    return min(param(h, "ev.delta_cap"), total)


def decide(ctx: DayContext, frame: pd.DataFrame, at: datetime, cfg: TrialConfig, model, helpers, h: dict,
           today) -> Decision:
    frame = frame[frame["ts"] <= at - timedelta(minutes=1)]          # nothing at or after `at` exists yet (R4)
    blocked = timeline_block(ctx, at, h)
    if blocked:
        return Decision(ctx.index, at, None, blocked)
    signal = h1(frame, at, ctx, h)
    if signal is None:
        return Decision(ctx.index, at, None, "no_signal")
    if not _warm(ctx):
        return Decision(ctx.index, at, signal, "warmup")
    failed = first_failed_gate(signal, ctx, frame, helpers, h)
    if failed:
        return Decision(ctx.index, at, signal, failed)
    scores = family_scores(ctx, frame, signal, h)
    delta = _delta(ctx, cfg, h)
    p = None
    if model is not None:
        if scores["technical"] is None:
            return Decision(ctx.index, at, signal, "warmup", scores=scores)
        if isinstance(model, Consensus):
            parts = [v for v in (scores["technical"], scores["options"], scores["macro"]) if v is not None]
            p = model.predict(sum(parts) / len(parts))
        else:
            p = model.predict(columns(scores, signal.side, ctx.har_pct, ctx.dte_1))
    choice = pick(candidates(signal, ctx, helpers, h, today), p, delta, h, evaluate_ev=model is not None)
    decision = Decision(ctx.index, at, signal, None if choice else "no_strike", p=p, delta=delta, scores=scores,
                        choice=choice)
    if choice is None or model is None:
        return decision
    trigger = choice.ask - param(h, "account.risk_rupees") / choice.lot
    limit = trigger - max(0.10 * trigger, 5 * TICK)
    names = ("technical", "options", "macro")
    reasons_for = tuple(f"{n} {scores[n]:+.2f}" for n in names if scores.get(n) is not None and scores[n] > 0)
    reasons_against = tuple(f"{n} {scores[n]:+.2f}" for n in names if scores.get(n) is not None and scores[n] < 0)
    decision.alert = Alert(choice, signal.side, at, choice.ask + param(h, "alert.entry_limit_ticks") * TICK,
                           signal.stop_level, signal.target_level, trigger, limit, p, delta, dict(ctx.delta_parts),
                           reasons_for or ("H1 breakout with every gate passed",), reasons_against)
    return decision
