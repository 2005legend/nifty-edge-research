"""Fitting the business-time clock (design §7), run once by `fit clock` and then frozen.

Three separate measurements, each with its own sample:

* the 375 minute weights come from realised intraday variance, winsorised per slot so one bad print cannot
  buy a minute of option time;
* theta_night comes from official daily OHLC, as the variance of a back-to-back overnight return relative to
  the variance of the session that follows it;
* theta_weekend_day and theta_holiday come from the decay of ATM implied variance across a gap, scaled by
  that day's VIX so a change in the volatility level is not read as time passing.

Nothing here reads a strategy parameter: the fit window, the winsor quantile and the dte window all arrive
as arguments from `research/hypotheses.yaml` (design §7, spec §6.0).
"""

from bisect import bisect_right
from collections.abc import Sequence

import numpy as np
import pandas as pd

from quantdesk.black76 import implied_vol
from quantdesk.clock import IST
from quantdesk.pricing.clock import MINUTES, OPEN, gap_days

DAY = 365.0             # the design's calendar-T denominator
MIN_PAIRS = 4           # more gaps than the three coefficients, or the regression has no residual left
OPTION_TYPES = ("CE", "PE")


def fit_minute_weights(minutes: pd.DataFrame, opens: pd.Series, q: float) -> np.ndarray:
    """w_m ∝ mean over days of min(r²_{d,m}, q_m), normalised to one session (design §7).

    `minutes` is one index's regular-session bars with `day`, `ts` and `close`; `opens` is that index's
    official open by day. Slot 0 is measured from the official open, because that is the anchor the noise
    band and the daily table use, not from whatever the first bar happens to print. A bar missing on one
    day leaves that slot and the return spanning it out of the mean; it is never filled in.
    """
    closes = _slots(minutes)
    log_close = np.log(closes.to_numpy(dtype=float))
    log_open = np.log(opens.reindex(closes.index).to_numpy(dtype=float))[:, None]
    r2 = np.diff(np.concatenate([log_open, log_close], axis=1), axis=1) ** 2
    capped = np.minimum(r2, np.nanquantile(r2, q, axis=0))       # q_m per slot, so a wide minute keeps its shape
    weights = np.nanmean(capped, axis=0)
    return weights / weights.sum()


def fit_theta_night(daily: pd.DataFrame, sessions) -> float:
    """θ_n = mean(r_on²) / mean(ln(C/O)²) over back-to-back sessions (design §7).

    `daily` is one target's official OHLC by day. A pair with a weekend day or a holiday between its two
    sessions carries more than one night of news, so it measures a gap weight and is left out here; those
    are what `fit_weekend_holiday` is for.
    """
    frame = daily.set_index("day")
    days = tuple(sorted(sessions))
    pairs = [(a, b) for a, b in zip(days, days[1:]) if (b - a).days == 1 and a in frame.index and b in frame.index]
    if not pairs:
        raise ValueError("theta_night needs a pair of back-to-back sessions with both days in daily")
    previous = frame.loc[[a for a, _ in pairs], "close"].to_numpy(dtype=float)
    today = frame.loc[[b for _, b in pairs], ["open", "close"]].to_numpy(dtype=float)
    overnight = np.log(today[:, 0] / previous)
    intraday = np.log(today[:, 1] / today[:, 0])
    return float(np.mean(overnight ** 2) / np.mean(intraday ** 2))


def atm_implied_variance(eod: pd.DataFrame, vix_close: pd.Series, dte: Sequence[int], sessions) -> pd.DataFrame:
    """Ṽ = IV² × T / (VIX/100)² for the ATM strike of each (day, expiry) in the dte window (design §7 1-4).

    `eod` is one index's `options_eod` rows, `sessions` the calendar the trading days left are counted on,
    and `dte` the pre-registered window (`clock.atm_dte`). Only rows that dealt are candidates, and only a
    strike whose call and put both dealt: an untraded row carries a close but no price. Dividing by VIX²
    takes the level out, so what is left is the variance the market says will accrue over T.
    """
    rows = eod[eod["instrument"] == "IDO"]
    dealt = rows["traded"].fillna(False).astype(bool)
    rows = rows[dealt & rows["option_type"].isin(OPTION_TYPES)]
    empty = pd.DataFrame(columns=["day", "expiry", "v_tilde"])
    if rows.empty:
        return empty
    legs = rows.pivot(index=["day", "expiry", "strike"], columns="option_type", values="close")
    legs = legs.reindex(columns=list(OPTION_TYPES))       # a leg nobody traded is a column of holes, not an error
    vix = vix_close.to_dict()
    days = tuple(sorted(sessions))
    out = []
    for (day, expiry), strikes in legs.groupby(level=[0, 1], sort=True):
        left = bisect_right(days, expiry) - bisect_right(days, day)   # trading days left, expiry day included
        if left not in dte or not np.isfinite(vix.get(day, np.nan)):
            continue
        both = strikes.droplevel([0, 1]).dropna()
        if both.empty:
            continue
        strike, call, put = _atm(both)
        t = (expiry - day).days / DAY                                 # calendar T, as the design specifies
        forward = strike + call - put                                 # put-call parity at r = 0
        if forward <= 0:
            continue
        try:
            iv = 0.5 * (implied_vol(call, forward, strike, t, kind="call")
                        + implied_vol(put, forward, strike, t, kind="put"))
        except ValueError:
            continue                                                  # a print the model cannot invert is no fit input
        out.append({"day": day, "expiry": expiry, "v_tilde": iv * iv * t / (vix[day] / 100.0) ** 2})
    return pd.DataFrame(out, columns=list(empty.columns)) if out else empty


def fit_weekend_holiday(vt: pd.DataFrame, sessions, theta_night: float) -> dict:
    """ΔṼ = β0 + β1·W + β2·H by OLS, then θ_w and θ_h as shares of one session plus one night (design §7 5-6).

    One back-to-back pair is β0, so β1/β0 and β2/β0 are the gap days' shares of a session, scaled by
    (1 + θ_n) to put them in the same units as the clock's night weight. The reported standard errors are
    those of β1 and β2 from (X'X)⁻¹s², carried onto the θ scale by the same factor.
    """
    days = tuple(sorted(sessions))
    position = {day: i for i, day in enumerate(days)}
    weekend, holiday = gap_days(days)
    drops = []
    for _, chain in vt.groupby("expiry", sort=True):
        level = dict(zip(chain["day"], chain["v_tilde"]))
        known = sorted(day for day in level if day in position)
        for a, b in zip(known, known[1:]):
            if position[b] - position[a] != 1:
                continue                                              # a hole in the chain is not one night
            drops.append((level[a] - level[b], weekend[position[a]], holiday[position[a]]))
    if len(drops) < MIN_PAIRS:
        raise ValueError(f"the weekend and holiday fit needs {MIN_PAIRS} consecutive-session pairs, got {len(drops)}")
    y = np.array([row[0] for row in drops], dtype=float)
    x = np.column_stack([np.ones(len(drops)), [row[1] for row in drops], [row[2] for row in drops]])
    beta, *_ = np.linalg.lstsq(x, y, rcond=None)
    residual = y - x @ beta
    s2 = residual @ residual / (len(y) - x.shape[1])
    se = np.sqrt(np.diag(np.linalg.inv(x.T @ x) * s2))
    scale = 1.0 + theta_night
    share = scale / abs(beta[0])
    return {"theta_weekend_day": float(np.clip(beta[1] / beta[0] * scale, 0.0, scale)),
            "theta_holiday": float(np.clip(beta[2] / beta[0] * scale, 0.0, scale)),
            "se_weekend": float(se[1] * share),
            "se_holiday": float(se[2] * share),
            "n": int(len(y))}


def _slots(minutes: pd.DataFrame) -> pd.DataFrame:
    """A day x slot matrix of closes, slot m stamped 09:15 + m minutes; prints outside the session drop out."""
    stamp = pd.to_datetime(minutes["ts"])
    local = stamp.dt.tz_localize(IST) if stamp.dt.tz is None else stamp.dt.tz_convert(IST)
    frame = pd.DataFrame({"day": np.asarray(minutes["day"]), "close": minutes["close"].to_numpy(dtype=float),
                          "slot": (local.dt.hour * 60 + local.dt.minute - (OPEN.hour * 60 + OPEN.minute)).to_numpy()})
    return (frame.pivot(index="day", columns="slot", values="close")
            .reindex(columns=range(MINUTES)).sort_index())


def _atm(strikes: pd.DataFrame) -> tuple[float, float, float]:
    """The strike nearest the parity forward, and its two closes.

    F = K + C − P makes |K − F| = |C − P|, so the ATM strike needs no spot input: it is the traded strike
    whose call and put are closest in price. Ties go to the lower strike.
    """
    gap = (strikes["CE"] - strikes["PE"]).abs()
    strike = float(gap.sort_values(kind="mergesort").index[0])
    return strike, float(strikes.loc[strike, "CE"]), float(strikes.loc[strike, "PE"])
