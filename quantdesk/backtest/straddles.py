"""SP5: the ATM straddle bought at the close when the market prices it below the forecast move, held one session,
on real bhavcopy closes. The rule is fixed in research/sp5/PREREG.md; this module only carries it out.
"""

import math
from datetime import date, datetime, time

import numpy as np
import pandas as pd

from quantdesk.black76 import implied_vol
from quantdesk.clock import IST
from quantdesk.costs import round_trip
from quantdesk.pricing.quotes import half_spread
from quantdesk.vol.ivsurface import atm_strike, parity_forward

CLOSE = time(15, 30)
SPREAD_AT = time(15, 29)
TICK = 0.05
VALIDATION = (date(2019, 2, 11), date(2025, 12, 31))


def _at(day: date, t: time) -> datetime:
    return datetime.combine(day, t, tzinfo=IST)


def _leg(rows: pd.DataFrame, strike: float, kind: str):
    r = rows[(rows["strike"] == strike) & (rows["option_type"] == kind) & rows["traded"].fillna(False).astype(bool)]
    return (float(r["close"].iloc[0]), int(r["lot"].iloc[0])) if len(r) else (None, None)


def straddle_study(eod: dict, har: pd.DataFrame, clock, h: dict, today: date, index: str = "NIFTY") -> pd.DataFrame:
    """`eod`: day -> that day's option rows (expiry, strike, option_type, close, lot, traded). `har`: indexed by day,
    with `rv_hat_nogap` (the forecast for that day, known at the previous close)."""
    days = sorted(eod)
    rows = []
    for d, d1 in zip(days, days[1:]):
        today_rows, next_rows = eod[d], eod[d1]
        expiries = sorted(e for e in today_rows["expiry"].unique() if e > d1)
        if not expiries or d1 not in har.index:
            continue
        expiry = expiries[0]
        chain, chain1 = today_rows[today_rows["expiry"] == expiry], next_rows[next_rows["expiry"] == expiry]
        # the ATM strike among those whose two legs also traded the next day
        both_next = set(chain1[chain1["traded"].fillna(False).astype(bool)].groupby("strike")["option_type"]
                        .nunique().loc[lambda s: s == 2].index)
        k = atm_strike(chain[chain["strike"].isin(both_next)])
        if k is None:
            continue
        (c, lot), (p, _) = _leg(chain, k, "CE"), _leg(chain, k, "PE")
        (c1, _), (p1, _) = _leg(chain1, k, "CE"), _leg(chain1, k, "PE")
        if None in (c, p, c1, p1):
            continue
        F = parity_forward(chain, k)
        T = clock.bt(_at(d, CLOSE), _at(expiry, CLOSE))
        try:
            iv = (implied_vol(c, F, k, T, kind="call") + implied_vol(p, F, k, T, kind="put")) / 2.0
        except ValueError:
            continue
        t1 = clock.bt(_at(d, CLOSE), _at(d1, CLOSE))
        forecast = float(har.loc[d1, "rv_hat_nogap"]) * (1.0 + clock.theta_night)
        if not forecast > 0 or math.isnan(forecast):
            continue
        rho = iv * iv * t1 / forecast
        legs_in = [x + half_spread(index, x, _at(d, SPREAD_AT), h) for x in (c, p)]
        legs_out = [max(TICK, x - half_spread(index, x, _at(d1, SPREAD_AT), h)) for x in (c1, p1)]
        exchange = "NSE" if index == "NIFTY" else "BSE"
        charges = sum(round_trip(i, o, lot, exchange=exchange, day=today).total for i, o in zip(legs_in, legs_out))
        charges_asof = sum(round_trip(i, o, lot, exchange=exchange, day=d1).total for i, o in zip(legs_in, legs_out))
        premium = sum(legs_in) * lot
        gross = (sum(legs_out) - sum(legs_in)) * lot
        rows.append({"day": d, "exit_day": d1, "expiry": expiry, "strike": k, "forward": F, "lot": lot, "iv": iv,
                     "implied_var": iv * iv * t1, "forecast_var": forecast, "rho": rho, "signal": bool(rho < 1.0),
                     "premium": premium, "pnl": gross - charges, "ret": (gross - charges) / premium,
                     "ret_asof": (gross - charges_asof) / premium})
    return pd.DataFrame(rows)


def _t(x: pd.Series) -> float:
    x = x.dropna().astype(float)
    return float(x.mean() / (x.std(ddof=1) / math.sqrt(len(x)))) if len(x) > 1 and x.std(ddof=1) > 0 else math.nan


def _welch(a: pd.Series, b: pd.Series) -> float:
    a, b = a.dropna().astype(float), b.dropna().astype(float)
    if len(a) < 2 or len(b) < 2:
        return math.nan
    se = math.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    return float((a.mean() - b.mean()) / se) if se > 0 else math.nan


def _summary(x: pd.DataFrame) -> dict:
    r = x["ret"].astype(float)
    return {"n": int(len(r)), "mean": float(r.mean()) if len(r) else math.nan, "t": _t(r),
            "win_rate": float((r > 0).mean()) if len(r) else math.nan}


def evaluate(rows: pd.DataFrame) -> dict:
    """The PREREG gates on 11 Feb 2019 - 31 Dec 2025; 2026 reported apart (touched)."""
    day = pd.to_datetime(rows["day"]).dt.date
    valid = rows[(day >= VALIDATION[0]) & (day <= VALIDATION[1])]
    filt, base = valid[valid["signal"]], valid
    years = pd.to_datetime(filt["day"]).dt.year
    by_year = {int(y): _summary(g) for y, g in filt.groupby(years)}
    full_years = [by_year[y]["mean"] for y in range(2020, 2026) if y in by_year]
    f, b = _summary(filt), _summary(base)
    gates = {"mean_positive_t2": bool(f["mean"] > 0 and f["t"] >= 2),
             "years_positive_4_of_6": bool(sum(m > 0 for m in full_years) >= 4),
             "beats_baseline": bool(f["mean"] > b["mean"] and _welch(filt["ret"], base["ret"]) >= 2)}
    touched = rows[day >= date(2026, 1, 1)]
    return {"filtered": f, "baseline": b, "welch_t": _welch(filt["ret"], base["ret"]), "by_year": by_year,
            "share_signal": float(valid["signal"].mean()) if len(valid) else math.nan, "gates": gates,
            "passed": all(gates.values()), "touched_2026": {"filtered": _summary(touched[touched["signal"]]),
                                                            "baseline": _summary(touched),
                                                            "n": int(len(touched))}}
