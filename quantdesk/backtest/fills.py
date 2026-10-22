"""Entry fills (spec §6.1 step 8, §6.2): a delayed, capped, marketable limit.

With delay k, the order fills at the bar stamped T + k - 1 (R4), at the ask plus one tick (paper-fill rule,
spec §7).

It does not fill when:
- **the alert lapsed:** more than 5 minutes passed, or the hard exit came first
- **the index ran past the chase cap:** min(0.15 sigma(tau) x open, 0.3 b)
- **for delays of 3 minutes or more, the signal flipped back:** the close at T + 2 is inside the band or on
  the wrong side of VWAP (spec §6.2)

A signal that does not fill still counts, with R = 0.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from quantdesk.analysis.bands import slot
from quantdesk.strategy.types import DayContext, Signal, StrikeChoice
from quantdesk.validation.hypotheses import param

TICK = 0.05


@dataclass(frozen=True)
class FillResult:
    status: str                  # "filled", "lapsed" or "rejected_flip"
    at: datetime | None
    premium: float | None
    spot: float | None


def _close_at(frame: pd.DataFrame, ts: datetime) -> float | None:
    rows = frame[frame["ts"] == ts]
    return float(rows["close"].iloc[-1]) if len(rows) else None


def fill(signal: Signal, choice: StrikeChoice, frame: pd.DataFrame, quotes, delay_min: int, ctx: DayContext,
         h: dict) -> FillResult:
    at = signal.at + timedelta(minutes=delay_min)
    hard = datetime.combine(ctx.day, ctx.hard_exit, tzinfo=signal.at.tzinfo)
    if delay_min > param(h, "time.alert_lapse_min") or at >= hard:
        return FillResult("lapsed", None, None, None)
    spot = _close_at(frame, at - timedelta(minutes=1))
    if spot is None:
        return FillResult("lapsed", None, None, None)
    sign = 1.0 if signal.side == "long" else -1.0
    sigma = ctx.band_sigma[slot(signal.at - timedelta(minutes=1))]
    cap = min(param(h, "fill.chase_sigma_fraction") * (0 if np.isnan(sigma) else sigma) * ctx.open,
              param(h, "fill.chase_stop_fraction") * signal.b)
    if sign * (spot - signal.ref_close) > cap:
        return FillResult("lapsed", None, None, None)
    if delay_min >= param(h, "fill.sign_flip_check_min"):
        check = frame[frame["ts"] == signal.at + timedelta(minutes=2)]
        if len(check):
            row = check.iloc[-1]
            edge = row["upper"] if signal.side == "long" else row.get("lower", np.nan)
            back = sign * (row["close"] - edge) <= 0 if not pd.isna(edge) else False
            if back or sign * (row["close"] - row["vwap"]) <= 0:
                return FillResult("rejected_flip", None, None, None)
    ask = quotes.quote(choice.index, choice.expiry, choice.strike, choice.kind, at).ask
    return FillResult("filled", at, ask + param(h, "fill.entry_ticks_over_ask") * TICK, spot)
