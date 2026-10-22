"""The exit simulator (spec §6.1 step 8, design §11, R2): minute by minute from the fill, on closed bars.

Policies:
- **X0:** stop at b, fixed target 2.3b, exit on a VWAP cross, stall at 45 minutes, deadline at 90.
- **X1, the E-trail:**
  - The trail switches on once the index has run 1.0b. From then the stop is max(stop, best - 1.5b, VWAP)
    (mirrored for shorts).
  - The owner moves his stop-loss order when a phone alert says so. Alerts are at least 10 minutes apart, and
    each takes effect 2 minutes after it is sent.
  - Laggards: a trade that never ran 1.0b exits at 30 minutes if the index is within 0.05% of entry, and at 60
    minutes regardless.
- **X2:** stop = max(stop, VWAP), no target and no trail.

Every exit that needs the owner to act fills 2 minutes after the decision, at the bid, and never after the
hard exit. X1 also has a premium SL-limit backstop (model B), moved with each ratchet, and the trade books
whichever of the index-alert path (A) and the backstop path (B) pays less.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta

import pandas as pd

from quantdesk.analysis.macro import timed_event_exits
from quantdesk.costs import round_trip
from quantdesk.strategy.types import DayContext, Signal, StrikeChoice
from quantdesk.validation.hypotheses import param

TICK = 0.05
EXCHANGE = {"NIFTY": "NSE", "SENSEX": "BSE"}


@dataclass
class OpenTrade:
    signal: Signal
    choice: StrikeChoice
    fill_at: datetime
    fill_premium: float
    backstop_trigger: float
    backstop_limit: float


@dataclass
class ExitResult:
    exit_at: datetime
    exit_premium: float
    reason: str
    model: str
    ratchets: int
    pnl_a: float
    pnl_b: float | None
    pnl: float
    gross: float


def _bid(quotes, trade: OpenTrade, at: datetime) -> float:
    c = trade.choice
    return max(TICK, quotes.quote(c.index, c.expiry, c.strike, c.kind, at).bid)


def _pnl(trade: OpenTrade, exit_premium: float, today: date) -> tuple[float, float]:
    c = trade.choice
    gross = (exit_premium - trade.fill_premium) * c.lot
    costs = round_trip(trade.fill_premium, exit_premium, c.lot, exchange=EXCHANGE[c.index], day=today).total
    return gross - costs, gross


def _path_a(trade: OpenTrade, frame: pd.DataFrame, ctx: DayContext, policy: str, h: dict):
    """(decision moment, fill moment, reason, ratchet schedule [(effective_at, stop)], fill is at-the-touch)."""
    sig = trade.signal
    sign = 1.0 if sig.side == "long" else -1.0
    b, s0 = sig.b, sig.ref_close
    stop = sig.stop_level
    delay = timedelta(minutes=param(h, "exit.manual_delay_min"))
    gap = timedelta(minutes=param(h, "exit.ratchet_alert_min_gap"))
    hard = datetime.combine(ctx.day, ctx.hard_exit, tzinfo=sig.at.tzinfo)
    events = [e for e in timed_event_exits(ctx.events, ctx.day) if e > trade.fill_at]
    laggard_min, laggard_band = param(h, "exit.laggard_minutes"), param(h, "exit.laggard_band")
    deadline = param(h, "exit.laggard_deadline_min")
    if policy == "X0":
        laggard_min, deadline = param(h, "exit.x0_stall_min"), param(h, "exit.x0_deadline_min")
    best, active, reached = s0, False, False
    last_alert, pending, schedule = None, [], []
    scheduled_exit = None
    for row in frame[frame["ts"] >= trade.fill_at].sort_values("ts").itertuples():
        moment = row.ts + timedelta(minutes=1)
        for effective, new_stop in list(pending):
            if effective <= moment:
                stop = new_stop
                pending.remove((effective, new_stop))
        if moment >= hard:
            return hard, hard, "hard_exit", schedule, False
        if scheduled_exit is not None and moment >= scheduled_exit[1]:
            return scheduled_exit[0], scheduled_exit[1], scheduled_exit[2], schedule, False
        if scheduled_exit is not None:
            continue
        close = float(row.close)
        move = sign * (close - s0)
        best = max(best, close) if sign > 0 else min(best, close)
        reached = reached or move >= param(h, "exit.trail_start_b") * b
        elapsed = (moment - trade.fill_at).total_seconds() / 60.0
        if policy == "X0" and move >= sign * (sig.target_level - s0):
            return moment, moment, "target", schedule, True
        if policy == "X1" and reached:
            trail = best - sign * param(h, "exit.trail_distance_b") * b
            wanted = max(stop, trail, row.vwap) if sign > 0 else min(stop, trail, row.vwap)
            current = pending[-1][1] if pending else stop
            if sign * (wanted - current) > 1e-9 and (last_alert is None or moment - last_alert >= gap):
                last_alert = moment
                pending.append((moment + delay, wanted))
                schedule.append((moment + delay, wanted))
        if policy == "X2":
            stop = max(stop, row.vwap) if sign > 0 else min(stop, row.vwap)
        reason = None
        if sign * (close - stop) <= 0:
            reason = "stop"
        elif policy == "X0" and sign * (close - row.vwap) < 0:
            reason = "vwap_cross"
        elif not reached and policy in ("X0", "X1") and elapsed >= deadline:
            reason = "deadline" if policy == "X0" else "laggard"
        elif (not reached and policy in ("X0", "X1") and elapsed >= laggard_min
              and abs(close / s0 - 1.0) <= laggard_band):
            reason = "stall" if policy == "X0" else "laggard"
        elif any(e <= moment for e in events):
            reason = "event"
        if reason is not None:
            fill = moment + delay
            if fill >= hard:
                return hard, hard, "hard_exit", schedule, False
            scheduled_exit = (moment, fill, reason)
    last = frame["ts"].max() + timedelta(minutes=1)
    return last, last, "end_of_data", schedule, False


def _backstop(trade: OpenTrade, frame: pd.DataFrame, quotes, schedule: list, until: datetime):
    """First moment the premium SL-limit fills before `until`, and its price; None if it never fills."""
    c = trade.choice
    trigger, limit = trade.backstop_trigger, trade.backstop_limit
    moves = sorted(schedule)
    for row in frame[frame["ts"] >= trade.fill_at].sort_values("ts").itertuples():
        moment = row.ts + timedelta(minutes=1)
        if moment >= until:
            return None
        while moves and moves[0][0] <= moment:
            _, index_stop = moves.pop(0)
            trigger = quotes.mid(c.index, c.expiry, c.strike, c.kind, moment, spot=index_stop)
            limit = trigger - max(0.10 * trigger, 5 * TICK)
        bid = _bid(quotes, trade, moment)
        if bid <= trigger and bid >= limit:
            return moment, max(limit, bid)
    return None


def simulate_exit(trade: OpenTrade, frame: pd.DataFrame, quotes, ctx: DayContext, policy: str, h: dict,
                  today: date) -> ExitResult:
    decided, exit_at, reason, schedule, at_touch = _path_a(trade, frame, ctx, policy, h)
    premium_a = _bid(quotes, trade, exit_at)
    pnl_a, gross_a = _pnl(trade, premium_a, today)
    result = ExitResult(exit_at, premium_a, reason, "A", len(schedule), pnl_a, None, pnl_a, gross_a)
    if policy != "X1":
        return result
    filled = _backstop(trade, frame, quotes, schedule, exit_at)
    if filled is None:
        result.pnl_b = pnl_a
        return result
    moment, price = filled
    pnl_b, gross_b = _pnl(trade, price, today)
    result.pnl_b = pnl_b
    if pnl_b < pnl_a:
        return ExitResult(moment, price, "backstop", "B", len([s for s in schedule if s[0] <= moment]),
                          pnl_a, pnl_b, pnl_b, gross_b)
    return result
