"""The recorded-chain pricing check (R17, spec §6.2): is the model's premium *change* close to the market's?

At each strategy check time on a recorded day, every option within 1.5% of the index is marked twice: by the
recorder (the bid/ask midpoint) and by the model. The check compares the change over 15, 30 and 60 minutes and
to the hard exit:

    err = |Δmodel − Δactual| / max(|Δactual|, 2 ticks)

The floor keeps a flat market from turning a one-tick difference into an infinite error. The state at moment
T is the snapshot stamped T − 1 minute, the last one closed by then: the same rule the model's bars follow.

It passes when the median error is at most 15%. That counts only with 15 or more recorded sessions per index,
including 4 or more expiry days, because expiry days are where the clock matters most.
"""

from collections.abc import Callable
from datetime import date, datetime, time, timedelta

import pandas as pd

from quantdesk.clock import IST
from quantdesk.validation.hypotheses import param

TICK = 0.05
FIRST, LAST, STEP = time(9, 45), time(14, 0), 15
OTM_LIMIT = 0.015
EXIT, EXIT_EXPIRY = time(15, 10), time(15, 0)


def _checks(day: date) -> list[datetime]:
    at = datetime.combine(day, FIRST, tzinfo=IST)
    end = datetime.combine(day, LAST, tzinfo=IST)
    out = []
    while at <= end:
        out.append(at)
        at += timedelta(minutes=STEP)
    return out


def price_errors(recorded: pd.DataFrame, model_mid: Callable, horizons: list,
                 is_expiry_day: dict[date, bool]) -> pd.DataFrame:
    """One row per (check, token, horizon) where both ends were recorded."""
    rec = recorded.assign(mid=(recorded["bid"] + recorded["ask"]) / 2.0)
    state = rec.set_index(["token", "minute"]).sort_index()
    rows = []
    for day in sorted({m.date() for m in rec["minute"]}):
        exit_time = EXIT_EXPIRY if is_expiry_day.get(day, False) else EXIT
        for check in _checks(day):
            now = rec[rec["minute"] == check - timedelta(minutes=1)]
            for r in now.itertuples():
                if abs(r.strike / r.spot - 1.0) > OTM_LIMIT:
                    continue
                for h in horizons:
                    later = datetime.combine(day, exit_time, tzinfo=IST) if h == "exit" else check + timedelta(minutes=h)
                    if later <= check:
                        continue
                    key = (r.token, later - timedelta(minutes=1))
                    if key not in state.index:
                        continue
                    actual = float(state.loc[key, "mid"]) - r.mid
                    model = (model_mid(r.underlying, r.expiry, r.strike, r.side, later)
                             - model_mid(r.underlying, r.expiry, r.strike, r.side, check))
                    rows.append({"check": check, "token": r.token, "underlying": r.underlying, "horizon": h,
                                 "actual": actual, "model": model,
                                 "err": abs(model - actual) / max(abs(actual), 2 * TICK)})
    return pd.DataFrame(rows, columns=["check", "token", "underlying", "horizon", "actual", "model", "err"])


def check_result(errors: pd.DataFrame, sessions_by_index: dict, h: dict) -> dict:
    need_sessions = param(h, "pricing.check_min_sessions")
    need_expiry = param(h, "pricing.check_min_expiry_days")
    enough = all(v["sessions"] >= need_sessions and v["expiry_days"] >= need_expiry for v in sessions_by_index.values())
    median = float(errors["err"].median()) if len(errors) else float("nan")
    return {"median_error": median, "enough_data": bool(enough),
            "passed": bool(enough and median <= param(h, "pricing.check_max_error")),
            "sessions": {k: v["sessions"] for k, v in sessions_by_index.items()},
            "expiry_days": {k: v["expiry_days"] for k, v in sessions_by_index.items()}}
