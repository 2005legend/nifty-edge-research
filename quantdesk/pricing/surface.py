"""India VIX on the business-time clock, and the frozen volatility surface (design §7-§8, R15, R16).

`sigma_bt` turns a VIX print into volatility per sqrt(session unit). VIX is a 30-calendar-day figure, so
its variance is spread over the business time of the next 30 calendar days.

`Surface` adds what VIX does not carry:
- R(dte), the ratio of an expiry's ATM business-time vol to sigma_bt
- a quadratic skew in standardised moneyness, floored so a wing never prices at zero vol
- the spot-vol beta, which the strike picker uses to plan a premium at its stop and target (R16)

All of it is fitted once on 2019-2022 NIFTY chains and frozen in config/frozen/surface_v1.yaml. Sensex uses
the same numbers (R11).
"""

import math
from bisect import bisect_right
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from quantdesk.black76 import implied_vol
from quantdesk.clock import IST
from quantdesk.pricing.clock import Clock
from quantdesk.pricing.clockfit import _atm

CLOSE = time(15, 30)
VIX_DAYS = 30
YEAR_DAYS = 365
WINDOW = 15            # minutes per spot-vol window, from 09:30 (design §8)
FIRST_SLOT = 15        # 09:30
LAST_SLOT = 360        # 15:15, the spot cutoff
DTE_MAX = 6


def future_sessions(past: Sequence[date], holidays: set[date], until: date) -> tuple:
    """Recorded sessions, then every later weekday up to `until` that is not a listed holiday.

    The trading calendar is published a year ahead, so counting future sessions is not look-ahead. The 30-day
    VIX horizon always reaches past the last recorded session.
    """
    days = tuple(sorted(past))
    day = days[-1] + timedelta(days=1) if days else until
    extra = []
    while day <= until:
        if day.weekday() < 5 and day not in holidays:
            extra.append(day)
        day += timedelta(days=1)
    return days + tuple(extra)


def roll_to_session(at: datetime, sessions: Sequence[date]) -> datetime:
    """`at` if its day is a session, else the close of the last session before it."""
    days = tuple(sessions)
    if at.date() in set(days):
        return at
    before = bisect_right(days, at.date()) - 1
    if before < 0:
        raise ValueError(f"no session on or before {at.date()}")
    return datetime.combine(days[before], CLOSE, tzinfo=at.tzinfo)


def sigma_bt(vix: float, at: datetime, clock: Clock) -> float:
    """sigma per sqrt(session unit): (VIX/100)^2 * 30/365 spread over BT(at, at + 30 calendar days) (R15)."""
    end = roll_to_session(at + timedelta(days=VIX_DAYS), clock.sessions)
    bt = clock.bt(at, end)
    if bt <= 0:
        raise ValueError(f"no business time between {at} and {end}")
    return vix / 100.0 * math.sqrt(VIX_DAYS / YEAR_DAYS / bt)


@dataclass(frozen=True)
class Surface:
    r_dte: dict
    b1: float
    b2: float
    floor: float
    gamma_dn: float
    gamma_up: float
    max_abs_z: float = field(default=3.0)

    def sigma_from_atm(self, atm_sigma: float, F: float, K, T: float) -> np.ndarray:
        """The skew: atm * max(floor, 1 + b1 z + b2 z^2), z = ln(K/F) / (atm sqrt T), with |z| capped at the fit's range."""
        K = np.asarray(K, dtype=float)
        z = np.clip(np.log(K / F) / (atm_sigma * math.sqrt(T)), -self.max_abs_z, self.max_abs_z)
        return atm_sigma * np.maximum(self.floor, 1.0 + self.b1 * z + self.b2 * z * z)

    def sigma(self, at: datetime, expiry_close: datetime, F: float, K, vix: float, clock: Clock, dte: int) -> np.ndarray:
        atm = self.r_dte[min(max(dte, 0), DTE_MAX)] * sigma_bt(vix, at, clock)
        return self.sigma_from_atm(atm, F, K, clock.bt(at, expiry_close))

    def shifted(self, sigma_bt_value: float, move: float) -> float:
        """Planning vol after an index move (R16): falls raise vol by gamma_dn, rises by gamma_up."""
        gamma = self.gamma_dn if move < 0 else self.gamma_up
        return float(sigma_bt_value * math.exp(gamma * move))


def fifteen_minute_windows(index: pd.DataFrame, vix: pd.DataFrame) -> pd.DataFrame:
    """Non-overlapping 15-minute windows from 09:30 to 15:15: the index log return and the change in ln VIX."""
    def by_slot(frame):
        stamp = pd.to_datetime(frame["ts"]).dt.tz_convert(IST)
        slot = stamp.dt.hour * 60 + stamp.dt.minute - (9 * 60 + 15)
        return frame.assign(slot=slot.to_numpy()).set_index(["day", "slot"])["close"]

    both = pd.concat({"index": by_slot(index), "vix": by_slot(vix)}, axis=1)
    boundaries = list(range(FIRST_SLOT, LAST_SLOT + 1, WINDOW))
    rows = []
    for day, frame in both.groupby(level=0, sort=True):
        frame = frame.droplevel(0)
        for a, b in zip(boundaries, boundaries[1:]):
            if a in frame.index and b in frame.index:
                start, end = frame.loc[a], frame.loc[b]
                if start.notna().all() and end.notna().all():
                    rows.append({"day": day, "r": math.log(end["index"] / start["index"]),
                                 "dlnvix": math.log(end["vix"] / start["vix"])})
    return pd.DataFrame(rows, columns=["day", "r", "dlnvix"])


def _slope(x: np.ndarray, y: np.ndarray) -> float:
    design = np.column_stack([np.ones(len(x)), x])
    beta, *_ = np.linalg.lstsq(design, y, rcond=None)
    return float(beta[1])


def fit_surface(eod: pd.DataFrame, vix_close: pd.Series, clock: Clock, windows: pd.DataFrame,
                dte: Sequence[int], max_abs_z: float, floor: float) -> tuple[Surface, dict]:
    """R(dte) from traded ATM pairs, the skew from every traded strike, and the spot-vol beta (design §8)."""
    rows = eod[(eod["instrument"] == "IDO") & eod["traded"].fillna(False).astype(bool)]
    legs = rows.pivot_table(index=["day", "expiry", "strike"], columns="option_type", values="close", aggfunc="last")
    legs = legs.reindex(columns=["CE", "PE"])
    days = tuple(clock.sessions)
    vix = vix_close.to_dict()
    ratios: dict[int, list[float]] = {d: [] for d in dte}
    skew_z, skew_y = [], []
    for (day, expiry), chain in legs.groupby(level=[0, 1], sort=True):
        left = bisect_right(days, expiry) - bisect_right(days, day)
        if left not in ratios or day not in vix or not np.isfinite(vix[day]):
            continue
        chain = chain.droplevel([0, 1])
        both = chain.dropna()
        if both.empty:
            continue
        strike, call, put = _atm(both)
        forward = strike + call - put
        at = datetime.combine(day, CLOSE, tzinfo=IST)
        T = clock.bt(at, datetime.combine(expiry, CLOSE, tzinfo=IST))
        if forward <= 0 or T <= 0:
            continue
        try:
            atm = 0.5 * (implied_vol(call, forward, strike, T, kind="call") + implied_vol(put, forward, strike, T, kind="put"))
        except ValueError:
            continue
        ratios[left].append(atm / sigma_bt(vix[day], at, clock))
        for K, legs_k in chain.iterrows():          # out-of-the-money legs carry the skew; puts below F, calls above
            kind, side = ("call", "CE") if K >= forward else ("put", "PE")
            price = legs_k[side]
            if not np.isfinite(price):
                continue
            z = math.log(K / forward) / (atm * math.sqrt(T))
            if abs(z) > max_abs_z:
                continue
            try:
                iv = implied_vol(price, forward, K, T, kind=kind)
            except ValueError:
                continue
            skew_z.append(z)
            skew_y.append(iv / atm - 1.0)
    medians = {d: float(np.median(v)) for d, v in ratios.items() if v}
    if 1 not in medians:
        raise ValueError("R(1) could not be fitted: no traded ATM pair one session before expiry")
    r_dte = {d: medians.get(d, medians[1]) for d in range(DTE_MAX + 1)}
    r_dte[0] = medians[1]          # expiry-day intraday uses R(1) until recorded chains measure it (design §8)
    z = np.asarray(skew_z)
    (b1, b2), *_ = np.linalg.lstsq(np.column_stack([z, z * z]), np.asarray(skew_y), rcond=None)
    down, up = windows[windows["r"] < 0], windows[windows["r"] >= 0]
    surface = Surface(r_dte=r_dte, b1=float(b1), b2=float(b2), floor=floor,
                      gamma_dn=_slope(down["r"].to_numpy(), down["dlnvix"].to_numpy()),
                      gamma_up=_slope(up["r"].to_numpy(), up["dlnvix"].to_numpy()), max_abs_z=max_abs_z)
    report = {"n_atm": {d: len(v) for d, v in ratios.items()}, "n_skew": len(skew_z),
              "n_windows_down": len(down), "n_windows_up": len(up)}
    return surface, report


def save_surface(path: Path, surface: Surface, meta: dict) -> None:
    payload = {"r_dte": {int(k): float(v) for k, v in surface.r_dte.items()}, "b1": surface.b1, "b2": surface.b2,
               "floor": surface.floor, "gamma_dn": surface.gamma_dn, "gamma_up": surface.gamma_up,
               "max_abs_z": surface.max_abs_z, **meta}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def load_surface(path: Path) -> Surface:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return Surface(r_dte={int(k): float(v) for k, v in raw["r_dte"].items()}, b1=float(raw["b1"]), b2=float(raw["b2"]),
                   floor=float(raw["floor"]), gamma_dn=float(raw["gamma_dn"]), gamma_up=float(raw["gamma_up"]),
                   max_abs_z=float(raw.get("max_abs_z", 3.0)))
