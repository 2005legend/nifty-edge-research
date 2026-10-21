"""HAR-RV per index (design §6, R13): a monthly-refit OLS on yesterday's, last week's and last month's
realised variance, the India VIX and the overnight gap.

The volatility gate and the shock rule read this forecast, so it has to be reproducible: a fit for day t
uses only complete rows strictly before t, refits happen on the first session of each month, and `HarFit`
carries n, the residual variance and the x5 mean so any forecast can be rebuilt later. HAR is refit, not
frozen - the frozen pieces are the clock and the surface (design §7).

x5 uses the day's official open, which `daily` stamps 16:00. A forecast made at 09:16 takes the same open
from the 09:15 bar, so the regressor is knowable at the time it is used; nothing else in the row is.
"""

import math
from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

from quantdesk.vol.rv import garman_klass

TERMS = ("x1", "x2", "x3", "x4", "x5")
WEEK = 5        # x2: the mean RV of the previous five sessions
MONTH = 22      # x3: the mean RV of the previous 22 sessions
VIX_DAYS = 252  # x4: the VIX is a 30-day annualised figure, so it becomes a daily variance over 252
MIN_FIT_ROWS = 6
COLUMNS = ["rv_hat", "rv_hat_nogap", "sigma_day", "har_pct"]


@dataclass(frozen=True)
class HarFit:
    """One refit: the intercept and five slopes, the residual variance, and the rows behind them."""

    refit_day: date
    beta: np.ndarray
    s2: float
    n: int
    x5_mean: float


def _by_day(frame: pd.DataFrame, columns) -> pd.DataFrame:
    """A derived-table frame, which carries `day` as a column, as one row per session in day order."""
    return frame.set_index("day")[list(columns)].sort_index()


def har_design(daily: pd.DataFrame, vix: pd.DataFrame, c: float) -> pd.DataFrame:
    """The HAR matrix for one index: y is that day's ln RV, x1..x5 are all fixed by 09:16 that day."""
    bars = _by_day(daily, ["open", "high", "low", "close"])
    rv = pd.Series(garman_klass(*(bars[column].to_numpy() for column in ("open", "high", "low", "close"))),
                   index=bars.index)
    rv = rv.mask(rv <= 0)  # a session with no range has no ln RV, and no row of the fit may see -inf
    vix_close = _by_day(vix, ["close"])["close"].reindex(bars.index).shift(1)
    design = pd.DataFrame(index=bars.index)
    design["y"] = np.log(rv)
    design["x1"] = design["y"].shift(1)
    design["x2"] = np.log(rv.rolling(WEEK).mean().shift(1))
    design["x3"] = np.log(rv.rolling(MONTH).mean().shift(1))
    design["x4"] = np.log((vix_close / 100.0) ** 2 / VIX_DAYS)
    design["x5"] = np.log(np.log(bars["open"] / bars["close"].shift(1)) ** 2 + c)
    return design


def fit_har(design: pd.DataFrame, refit_day: date, window: int) -> HarFit:
    """OLS with an intercept on the last `window` complete rows strictly before `refit_day`."""
    rows = design[design.index < refit_day].dropna().iloc[-window:]
    if len(rows) < MIN_FIT_ROWS:
        raise ValueError(f"HAR needs {MIN_FIT_ROWS} complete rows before {refit_day}, got {len(rows)}")
    x = np.column_stack([np.ones(len(rows)), rows[list(TERMS)].to_numpy(dtype=float)])
    y = rows["y"].to_numpy(dtype=float)
    beta, *_ = np.linalg.lstsq(x, y, rcond=None)
    residual = y - x @ beta
    return HarFit(refit_day=refit_day, beta=beta, s2=float(residual @ residual / (len(y) - x.shape[1])),
                  n=int(len(y)), x5_mean=float(rows["x5"].mean()))


def forecast(fit: HarFit, row: pd.Series) -> tuple[float, float]:
    """(RV_hat, RV_hat with the gap term at its fit-window mean) for one design row, in fraction squared."""
    x = row[list(TERMS)].to_numpy(dtype=float)
    y = fit.beta[0] + fit.beta[1:] @ x
    correction = fit.s2 / 2.0  # the target is ln RV, so E[RV] = exp(y_hat + s^2/2)
    return float(np.exp(y + correction)), float(np.exp(y + fit.beta[5] * (fit.x5_mean - x[4]) + correction))


def har_series(daily: pd.DataFrame, vix: pd.DataFrame, window: int, c: float, percentile_window: int,
               percentile_min: int) -> pd.DataFrame:
    """One row per session: the forecast variance, its pre-gap version, sigma, and the HAR percentile."""
    design = har_design(daily, vix, c)
    fit: HarFit | None = None
    month: tuple[int, int] | None = None
    complete = 0
    rows = []
    for day, row in design.iterrows():
        if (day.year, day.month) != month:
            month = (day.year, day.month)
            if complete >= MIN_FIT_ROWS:
                fit = fit_har(design, day, window)
        known = bool(row.notna().all())
        if fit is not None and known:
            rv, no_gap = forecast(fit, row)
            rows.append((day, rv, no_gap, math.sqrt(rv)))
        else:
            rows.append((day, math.nan, math.nan, math.nan))
        complete += known
    frame = pd.DataFrame(rows, columns=["day", *COLUMNS[:3]]).set_index("day")
    frame["har_pct"] = _percentile(frame["rv_hat"], percentile_window, percentile_min)
    return frame[COLUMNS]


def _percentile(rv_hat: pd.Series, window: int, minimum: int) -> pd.Series:
    """The share of the previous `window` forecasts below this one; NaN until `minimum` of them exist (R12)."""
    values = rv_hat.to_numpy(dtype=float)
    out = np.full(len(values), np.nan)
    for i, value in enumerate(values):
        if math.isnan(value):
            continue
        earlier = values[max(0, i - window):i]
        earlier = earlier[~np.isnan(earlier)]
        if len(earlier) >= minimum:
            out[i] = float((earlier < value).mean())
    return pd.Series(out, index=rv_hat.index)
