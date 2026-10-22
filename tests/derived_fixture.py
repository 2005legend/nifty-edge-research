"""A small synthetic `data/derived` for tests of the day loader, the pipeline and the backtester.

`n_days` weekday sessions from 1 Jan 2024. NIFTY follows a seeded random walk and India VIX sits near 14.
Members trade every minute, and NIFTY weeklies expire on Thursdays with lot 50. Every table carries the columns
and `available_at` stamps that `quantdesk derive` writes.
"""

from datetime import date, datetime, time, timedelta

import numpy as np
import pandas as pd

from quantdesk.black76 import black76
from quantdesk.clock import IST
from quantdesk.derived.store import DerivedStore
from quantdesk.pricing.clock import Clock
from quantdesk.pricing.surface import Surface

START = date(2024, 1, 1)


def session_days(n_days: int) -> list[date]:
    return list(pd.bdate_range(START, periods=n_days).date)


def _thursdays(days):
    return [d for d in days if d.weekday() == 3]


def build(tmp_path, n_days: int = 30, seed: int = 7, drift: float = 0.0) -> tuple[DerivedStore, list[date]]:
    rng = np.random.default_rng(seed)
    derived = DerivedStore(tmp_path / "derived")
    days = session_days(n_days)
    bars, members, daily = [], [], []
    level, vix_level = 22000.0, 14.0
    for d in days:
        t0 = datetime.combine(d, time(9, 15), tzinfo=IST)
        ts = [t0 + timedelta(minutes=i) for i in range(375)]
        path = level * np.exp(np.cumsum(rng.normal(drift, 0.0004, 375)))
        vix = vix_level + np.cumsum(rng.normal(0, 0.005, 375))
        open_ = level * (1 + rng.normal(0, 0.001))
        path = path * open_ / path[0]
        bars.append(pd.DataFrame({"target": "NIFTY", "ts": ts, "open": path, "high": path * 1.0002,
                                  "low": path * 0.9998, "close": path, "volume": 0, "day": d}))
        bars.append(pd.DataFrame({"target": "INDIAVIX", "ts": ts, "open": vix, "high": vix, "low": vix, "close": vix,
                                  "volume": 0, "day": d}))
        adv = rng.integers(10, 40, 375)
        members.append(pd.DataFrame({"ts": ts, "members_total": 50, "members_present": 48,
                                     "tv": rng.uniform(1e8, 3e8, 375), "adv": adv, "dec": 50 - adv - 2,
                                     "above_vwap": rng.integers(10, 40, 375), "top5_ret": rng.normal(0, 0.002, 375),
                                     "day": d, "available_at": [t + timedelta(minutes=1) for t in ts]}))
        stamp = datetime.combine(d, time(16, 0), tzinfo=IST)
        daily.append({"target": "NIFTY", "day": d, "open": path[0], "high": path.max() * 1.0002,
                      "low": path.min() * 0.9998, "close": path[-1], "available_at": stamp})
        daily.append({"target": "INDIAVIX", "day": d, "open": vix[0], "high": vix.max(), "low": vix.min(),
                      "close": vix[-1], "available_at": stamp})
        level, vix_level = path[-1], float(vix[-1])
    minutes = pd.concat(bars, ignore_index=True)
    minutes["available_at"] = minutes["ts"] + timedelta(minutes=1)
    minutes["year"] = [d.year for d in minutes["day"]]
    derived.write_frame("minutes", minutes)
    derived.write_frame("sessions", pd.DataFrame({"day": days, "bars": 375, "first_bar": time(9, 15),
                                                  "last_bar": time(15, 29), "kind": "regular"}))
    derived.write_frame("daily", pd.DataFrame(daily))
    derived.write_frame("members_minute", pd.concat(members, ignore_index=True))
    thursdays = _thursdays(days) + [days[-1] + timedelta(days=7 * k) for k in range(1, 3)]
    expiries, eod = [], []
    for i, d in enumerate(days):
        ahead = [e for e in thursdays if e >= d]
        expiries.append({"symbol": "NIFTY", "day": d, "expiry_1": ahead[0], "expiry_2": ahead[1], "lot_1": 50,
                         "lot_2": 50, "is_expiry_day": ahead[0] == d,
                         "available_at": datetime.combine(d, time(9, 0), tzinfo=IST)})
        F = float(daily[2 * i]["close"])
        for e in ahead[:2]:
            T = max((e - d).days, 1) / 365.0
            for K in np.arange(round(F / 50) * 50 - 500, round(F / 50) * 50 + 550, 50.0):
                for kind, side in (("call", "CE"), ("put", "PE")):
                    eod.append({"day": d, "symbol": "NIFTY", "instrument": "IDO", "expiry": e, "strike": float(K),
                                "option_type": side, "close": black76(F, K, T, 0.14, kind=kind), "oi": 1000,
                                "volume": 10, "traded": True, "lot": 50,
                                "available_at": datetime.combine(d + timedelta(days=1), time(9, 0), tzinfo=IST),
                                "year": d.year})
    derived.write_frame("expiries", pd.DataFrame(expiries))
    derived.write_frame("options_eod", pd.DataFrame(eod))
    derived.write_frame("fii_ratio", pd.DataFrame({"day": days, "ratio": 0.45,
                                                   "available_at": [datetime.combine(d, time(20, 0), tzinfo=IST) for d in days]}))
    derived.write_frame("macro", pd.DataFrame({"series_id": "brent", "date": days, "value": 80.0,
                                               "available_at": [datetime.combine(d, time(9, 0), tzinfo=IST) for d in days]}))
    return derived, days


def clock_for(days, extra_days: int = 60) -> Clock:
    future = list(pd.bdate_range(days[-1] + timedelta(days=1), periods=extra_days).date)
    return Clock(np.full(375, 1 / 375), 0.5, 0.1, 0.2, tuple(days) + tuple(future))


def flat_surface() -> Surface:
    return Surface(r_dte={d: 1.0 for d in range(7)}, b1=0.0, b2=0.0, floor=0.5, gamma_dn=-2.0, gamma_up=-1.0)
