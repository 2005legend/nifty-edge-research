"""Stage B, one trial on one set of test days: probability, EV gate, caps, fill, exit (design §12).

Every signal on a test day becomes a row:
- filled trades carry their net R at today's charges, and at the trade day's own charges beside it
- signals stopped by a gate, the EV gate, a cap, a lapse or a flip carry R = 0

P&L exists only here, and only with a registry ticket (R32). `placebo_run` is the exception: random entries
for the controls, which prove the engine finds no edge where there is none.
"""

import math
from collections import defaultdict
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

from quantdesk.backtest.fills import fill
from quantdesk.costs import round_trip
from quantdesk.strategy.exits import OpenTrade, simulate_exit
from quantdesk.strategy.meta import Consensus, columns
from quantdesk.strategy.strikes import Candidate, candidates, pick
from quantdesk.strategy.timeline import check_times, timeline_block
from quantdesk.strategy.types import Signal, TrialConfig
from quantdesk.validation.hypotheses import param
from quantdesk.validation.registry import TrialTicket

TICK = 0.05
EXCHANGE = {"NIFTY": "NSE", "SENSEX": "BSE"}
HURDLE_COLUMN = {"shock": "delta_shock", "stress": "delta_stress"}


class NoTicketError(RuntimeError):
    """P&L on history without a registry ticket (R32)."""


def month_quota(day: date, sessions: list[date], per_year: int) -> int:
    in_month = sum(1 for d in sessions if d.year == day.year and d.month == day.month)
    in_year = sum(1 for d in sessions if d.year == day.year)
    return math.ceil(per_year * in_month / in_year) if in_year else per_year


def signal_from(row) -> Signal:
    return Signal(row["index"], row["at"], row["side"], float(row["ref_close"]), float(row["upper"]),
                  float(row["lower"]), float(row["vwap"]), float(row["stop_level"]), float(row["b"]),
                  float(row["target_level"]))


def _value(x):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else float(x)


def probability(row, cfg: TrialConfig, model) -> float:
    scores = {name: _value(row[name]) for name in ("technical", "options", "macro")}
    if isinstance(model, Consensus):
        parts = [v for v in scores.values() if v is not None]
        return model.predict(sum(parts) / len(parts))
    return model.predict(columns(scores, row["side"], float(row["har_pct"]), int(row["dte"])))


def hurdle(row, cfg: TrialConfig, h: dict) -> float:
    total = float(row["delta_event"] or 0.0) + sum(float(row[HURDLE_COLUMN[x]] or 0.0)
                                                  for x in cfg.hurdles if x in HURDLE_COLUMN)
    return min(param(h, "ev.delta_cap"), total)


def _trade(signal, choice, source, cfg, h, today, delay, day):
    ctx = source.context(signal.index, day)
    frame = source.frame(ctx)
    quotes = source.helpers(ctx, frame).quotes
    filled = fill(signal, choice, frame, quotes, delay, ctx, h)
    if filled.status != "filled":
        return {"status": filled.status}
    trigger = filled.premium - param(h, "account.risk_rupees") / choice.lot
    limit = trigger - max(0.10 * trigger, 5 * TICK)
    out = simulate_exit(OpenTrade(signal, choice, filled.at, filled.premium, trigger, limit), frame, quotes, ctx,
                        cfg.exit_policy, h, today)
    asof = out.gross - round_trip(filled.premium, out.exit_premium, choice.lot, exchange=EXCHANGE[choice.index],
                                  day=day).total
    risk = param(h, "account.risk_rupees")
    return {"status": "filled", "entry_at": filled.at, "entry_premium": filled.premium, "exit_at": out.exit_at,
            "exit_premium": out.exit_premium, "exit_reason": out.reason, "exit_model": out.model, "pnl": out.pnl,
            "pnl_asof": asof, "gross": out.gross, "r": out.pnl / risk, "r_asof": asof / risk,
            "turnover": filled.premium * choice.lot}


def run_trial_split(dataset, test_days: set, cfg: TrialConfig, model, source, h: dict, today: date, delay: int,
                    ticket, sessions: list[date]) -> pd.DataFrame:
    if not isinstance(ticket, TrialTicket):
        raise NoTicketError("a P&L run on history needs a registry ticket (R32); use placebo_run for controls")
    signals = dataset.signals[dataset.signals["day"].isin(test_days)].copy()
    signals["nifty_first"] = signals["index"] != "NIFTY"
    signals = signals.sort_values(["at", "nifty_first"])
    cands = {sid: [Candidate(**{k: r[k] for k in ("index", "expiry", "strike", "kind", "lot", "ask", "delta", "gain", "loss")})
                   for _, r in g.iterrows()] for sid, g in dataset.candidates.groupby("signal_id")}
    per_day, per_week, per_month = set(), defaultdict(int), defaultdict(int)
    rows = []
    for _, row in signals.iterrows():
        day = row["day"]
        base = {"signal_id": row["signal_id"], "day": day, "index": row["index"], "at": row["at"], "side": row["side"],
                "r": 0.0, "r_asof": 0.0, "pnl": 0.0, "turnover": 0.0, "weekday": row["weekday"],
                "expiry_day": row["expiry_day"], "vix_prev_close": row["vix_prev_close"]}
        failed = row["failed"]
        if isinstance(failed, str):
            rows.append({**base, "status": failed})
            continue
        p = probability(row, cfg, model)
        delta = hurdle(row, cfg, h)
        choice = pick(cands.get(row["signal_id"], []), p, delta, h)
        base.update({"p": p, "delta": delta})
        if choice is None:
            rows.append({**base, "status": "no_strike"})
            continue
        week = day - timedelta(days=day.weekday())
        if (day in per_day or per_week[week] >= param(h, "caps.per_week")
                or per_month[(day.year, day.month)] >= month_quota(day, sessions, param(h, "caps.per_year"))):
            rows.append({**base, "status": "cap"})
            continue
        result = _trade(signal_from(row), choice, source, cfg, h, today, delay, day)
        rows.append({**base, "expiry": choice.expiry, "strike": choice.strike, "kind": choice.kind, "lot": choice.lot,
                     **result})
        if result["status"] == "filled":
            per_day.add(day)
            per_week[week] += 1
            per_month[(day.year, day.month)] += 1
    return pd.DataFrame(rows)


def placebo_run(source, days: list[date], h: dict, today: date, seed: int, side_rule: str = "random",
                index: str = "NIFTY") -> pd.DataFrame:
    """Random entries (or always-long on drifting data) through the same fills and exits; gross R reported."""
    rng = np.random.default_rng(seed)
    risk = param(h, "account.risk_rupees")
    rows = []
    for day in days:
        try:
            ctx = source.context(index, day)
        except KeyError:
            continue
        frame = source.frame(ctx)
        times = [t for t in check_times(day, ctx.is_expiry_day, h) if not timeline_block(ctx, t, h)]
        if not times:
            continue
        at = times[int(rng.integers(len(times)))]
        bar = frame[frame["ts"] == at - timedelta(minutes=1)]
        if bar.empty:
            continue
        close = float(bar["close"].iloc[-1])
        sigma = ctx.band_sigma[min(int((at - timedelta(minutes=1)).hour * 60 + (at - timedelta(minutes=1)).minute - 555), 374)]
        b = (0.002 if np.isnan(sigma) else sigma) * ctx.open
        side = ("long" if rng.random() < 0.5 else "short") if side_rule == "random" else side_rule
        sign = 1.0 if side == "long" else -1.0
        sig = Signal(index, at, side, close, close, close, close, close - sign * b, b, close + sign * 2.3 * b)
        helpers = source.helpers(ctx, frame)
        choice = pick(candidates(sig, ctx, helpers, h, today), None, 0.0, h, evaluate_ev=False)
        if choice is None:
            continue
        cfg = TrialConfig("PLACEBO", "X1", "consensus")
        result = _trade(sig, choice, source, cfg, h, today, 0, day)
        if result["status"] == "filled":
            rows.append({"day": day, "side": side, "r": result["r"], "gross_r": result["gross"] / risk})
    return pd.DataFrame(rows, columns=["day", "side", "r", "gross_r"])
