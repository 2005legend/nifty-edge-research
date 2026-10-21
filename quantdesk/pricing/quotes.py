"""Option quotes: modelled for the backtest, recorded later for live and replay (design §8).

A quote is a mid from Black-76 on the business-time clock, with a half-spread from the pre-registered
table. The ask is rounded up to the ₹0.05 tick and the bid down, so the model never fills inside a real book.
`ModelQuotes` reads the index and VIX from the bar stamped one minute before the moment asked about, the bar
that has closed by then (R4). Asking for a moment with no such bar is an error, never a guess.
"""

import math
from bisect import bisect_right
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Protocol

import pandas as pd

from quantdesk.clock import IST
from quantdesk.pricing import black76_vec
from quantdesk.pricing.clock import Clock
from quantdesk.pricing.surface import Surface
from quantdesk.validation.hypotheses import param

TICK = 0.05
CLOSE = time(15, 30)
KINDS = {"CE": "call", "PE": "put"}


@dataclass(frozen=True)
class Quote:
    bid: float
    ask: float
    mid: float


class QuoteSource(Protocol):
    def quote(self, index: str, expiry: date, strike: float, kind: str, at: datetime) -> Quote: ...


def round_up_tick(x: float) -> float:
    return round(math.ceil(x / TICK - 1e-9) * TICK, 2)


def round_down_tick(x: float) -> float:
    return max(TICK, round(math.floor(x / TICK + 1e-9) * TICK, 2))


def half_spread(index: str, mid: float, at: datetime, h: dict) -> float:
    """The design §8 table: by index and premium, times the time-of-day multiplier."""
    if index == "SENSEX":
        base = param(h, "spread.half_sensex")
    else:
        base = param(h, "spread.half_nifty_under_50") if mid < 50 else param(h, "spread.half_nifty_50_up")
    clock = at.astimezone(IST).time()
    if clock < time(9, 30) or clock > time(14, 45):
        mult = param(h, "spread.mult_before_0930") if clock < time(9, 30) else param(h, "spread.mult_after_1445")
    elif clock < time(10, 0):
        mult = param(h, "spread.mult_0930_1000")
    else:
        mult = 1.0
    return base * mult


def sessions_left(clock: Clock, day: date, expiry: date) -> int:
    """Trading days left, the expiry day counted: 0 on expiry day, 1 the session before."""
    return bisect_right(clock.sessions, expiry) - bisect_right(clock.sessions, day)


class ModelQuotes:
    def __init__(self, frames: dict[str, pd.DataFrame], surface: Surface, clock: Clock, h: dict):
        self.surface, self.clock, self.h = surface, clock, h
        self._bars = {index: frame.set_index("ts")[["close", "vix"]].sort_index() for index, frame in frames.items()}

    def state(self, index: str, at: datetime) -> tuple[float, float]:
        """(index close, VIX) of the bar stamped at - 1 minute."""
        row = self._bars[index].loc[at - timedelta(minutes=1)]   # KeyError when that bar does not exist
        return float(row["close"]), float(row["vix"])

    def mid(self, index: str, expiry: date, strike: float, kind: str, at: datetime,
            spot: float | None = None, vix: float | None = None, sigma_scale: float = 1.0) -> float:
        """Model premium at `at`; `spot`, `vix` and `sigma_scale` let the strike picker plan a moved market."""
        if spot is None or vix is None:
            s, v = self.state(index, at)
            spot, vix = (spot if spot is not None else s), (vix if vix is not None else v)
        expiry_close = datetime.combine(expiry, CLOSE, tzinfo=IST)
        dte = sessions_left(self.clock, at.date(), expiry)
        sigma = self.surface.sigma(at, expiry_close, spot, [strike], vix, self.clock, dte)[0] * sigma_scale
        T = self.clock.bt(at, expiry_close)
        return float(black76_vec.price(spot, strike, T, sigma, KINDS[kind]))

    def quote(self, index: str, expiry: date, strike: float, kind: str, at: datetime) -> Quote:
        mid = self.mid(index, expiry, strike, kind, at)
        spread = half_spread(index, mid, at, self.h)
        return Quote(bid=round_down_tick(mid - spread), ask=round_up_tick(mid + spread), mid=mid)
