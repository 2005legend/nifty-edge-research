"""Replay a recorded day through the live engine, and the parity check against the backtest (SP3 design S12).

The live engine runs on a simulated clock, one step a minute, in shadow mode with a scratch journal. The
backtest path calls `decide()` at every check time on the full day. Both use the same day source, so any
difference is a timing or slicing bug in the live engine, which the parity test exists to catch.
"""

from datetime import date, datetime, time, timedelta

from quantdesk.clock import IST
from quantdesk.live.engine import LiveEngine
from quantdesk.live.notify import NullNotifier
from quantdesk.strategy.pipeline import decide
from quantdesk.strategy.timeline import check_times


def replay_day(source, day: date, cfg, model, h: dict, journal, indices=("NIFTY", "SENSEX")) -> list:
    engine = LiveEngine(lambda now: source, journal, NullNotifier(), cfg, model, h, day, mode="shadow",
                        indices=indices, sessions=[day])
    out = []
    now = datetime.combine(day, time(9, 16, 5), tzinfo=IST)
    end = datetime.combine(day, time(15, 31), tzinfo=IST)
    while now <= end:
        out += engine.step(now)
        now += timedelta(minutes=1)
    return out


def backtest_day(source, day: date, cfg, model, h: dict, indices=("NIFTY", "SENSEX")) -> list:
    out = []
    for index in indices:
        try:
            ctx = source.context(index, day)
        except (KeyError, ValueError):
            continue
        frame = source.frame(ctx)
        helpers = source.helpers(ctx, frame)
        out += [decide(ctx, frame, at, cfg, model, helpers, h, day) for at in check_times(day, ctx.is_expiry_day, h)]
    return out


def summary(decisions) -> list[tuple]:
    return sorted((d.index, d.at, d.failed, d.signal.side if d.signal else None,
                   d.choice.strike if d.choice else None, round(d.p, 6) if d.p is not None else None)
                  for d in decisions)
