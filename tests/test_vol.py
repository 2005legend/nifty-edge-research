from datetime import date

import numpy as np
import pandas as pd
import pytest

import quantdesk.vol.har as har
from quantdesk.validation.hypotheses import load_hypotheses, param
from quantdesk.vol.har import HarFit, fit_har, forecast, har_design, har_series
from quantdesk.vol.rv import garman_klass

H = load_hypotheses()
C = param(H, "har.overnight_c")
WINDOW = param(H, "vol.har_window_days")
PCT_WINDOW = param(H, "vol.har_percentile_window")
PCT_MIN = param(H, "har.percentile_min")
TERMS = ["x1", "x2", "x3", "x4", "x5"]


def _toy_design(n: int) -> pd.DataFrame:
    """Random regressors and a y that is an exact linear function of them plus a little noise."""
    rng = np.random.default_rng(n)
    x = rng.normal(size=(n, 5))
    design = pd.DataFrame(x, columns=TERMS, index=pd.date_range("2019-01-01", periods=n).date)
    beta = np.array([0.4, 0.3, 0.1, 0.2, 0.05])
    design["y"] = -9.0 + x @ beta + rng.normal(scale=0.01, size=n)
    return design


def _toy_market(n: int, seed: int = 3) -> tuple[pd.DataFrame, pd.DataFrame]:
    """A synthetic index and its VIX over business days, shaped like the `daily` derived table."""
    rng = np.random.default_rng(seed)
    days = pd.bdate_range("2019-01-01", periods=n).date
    close = 22000.0 * np.exp(np.cumsum(rng.normal(scale=0.008, size=n)))
    open_ = np.concatenate([[close[0] * 0.999], close[:-1]]) * np.exp(rng.normal(scale=0.003, size=n))
    spread = np.abs(rng.normal(scale=0.004, size=n))
    daily = pd.DataFrame({"day": days, "open": open_, "high": np.maximum(open_, close) * (1 + spread),
                          "low": np.minimum(open_, close) * (1 - spread), "close": close})
    vix = pd.DataFrame({"day": days, "close": rng.uniform(10.0, 25.0, n)})
    return daily, vix


def test_garman_klass_hand_value():
    v = garman_klass(np.array([100.0]), np.array([102.0]), np.array([99.0]), np.array([101.0]))
    expected = 0.5 * np.log(102 / 99) ** 2 - (2 * np.log(2) - 1) * np.log(101 / 100) ** 2
    assert v[0] == pytest.approx(expected)


def test_garman_klass_is_zero_on_a_flat_day_and_positive_on_a_wide_one():
    flat = garman_klass(np.array([100.0]), np.array([100.0]), np.array([100.0]), np.array([100.0]))
    wide = garman_klass(np.array([100.0]), np.array([104.0]), np.array([97.0]), np.array([99.0]))
    assert flat[0] == 0.0
    assert wide[0] > 0.0


def test_har_recovers_planted_coefficients():
    rng = np.random.default_rng(1)
    n = 900
    X = rng.normal(size=(n, 5))
    beta = np.array([-9.0, 0.4, 0.3, 0.1, 0.2, 0.05])
    y = beta[0] + X @ beta[1:] + rng.normal(scale=0.01, size=n)
    design = pd.DataFrame(X, columns=TERMS, index=pd.date_range("2019-01-01", periods=n).date).assign(y=y)
    fit = fit_har(design, refit_day=design.index[-1], window=WINDOW)
    assert np.allclose(fit.beta, beta, atol=0.01)
    assert fit.n == WINDOW
    assert fit.s2 == pytest.approx(0.01 ** 2, rel=0.2)
    assert fit.x5_mean == pytest.approx(design["x5"].iloc[-WINDOW - 1:-1].mean())  # the refit day is excluded


def test_har_never_uses_the_refit_day_or_later():
    design = _toy_design(800)
    a = fit_har(design, refit_day=design.index[760], window=WINDOW)
    changed = design.copy()
    changed.loc[design.index[760]:, "y"] += 100.0
    b = fit_har(changed, refit_day=design.index[760], window=WINDOW)
    assert np.allclose(a.beta, b.beta)


def test_a_fit_on_too_few_rows_is_refused():
    design = _toy_design(har.MIN_FIT_ROWS)  # one short: the refit day itself is never in the window
    with pytest.raises(ValueError, match=f"got {har.MIN_FIT_ROWS - 1}"):
        fit_har(design, refit_day=design.index[-1], window=WINDOW)


def test_the_design_row_for_a_day_uses_only_earlier_sessions():
    """R4/R13: y is that day's variance, but every regressor is fixed by 09:16, before the session trades."""
    daily, vix = _toy_market(40)
    design = har_design(daily, vix, C)
    assert list(design.columns) == ["y", *TERMS]
    assert design.index[-1] == daily["day"].iloc[-1]
    rv = pd.Series(garman_klass(*(daily[k].to_numpy() for k in ("open", "high", "low", "close"))),
                   index=daily["day"])
    last, previous = design.index[-1], design.index[-2]
    assert design.loc[last, "y"] == pytest.approx(np.log(rv.loc[last]))
    assert design.loc[last, "x1"] == pytest.approx(design.loc[previous, "y"])
    assert design.loc[last, "x2"] == pytest.approx(np.log(rv.iloc[-6:-1].mean()))
    assert design.loc[last, "x3"] == pytest.approx(np.log(rv.iloc[-23:-1].mean()))
    assert design.loc[last, "x4"] == pytest.approx(np.log((vix["close"].iloc[-2] / 100) ** 2 / 252))
    assert design.loc[last, "x5"] == pytest.approx(np.log(np.log(daily["open"].iloc[-1]
                                                                 / daily["close"].iloc[-2]) ** 2 + C))
    assert design["x3"].iloc[:22].isna().all()  # the monthly term needs 22 earlier sessions
    assert design[TERMS].notna().all(axis=1).iloc[22:].all()
    assert design["y"].notna().all()


def test_a_day_missing_from_the_vix_leaves_the_next_row_unusable():
    """No filling: a hole in the VIX costs the next day's x4, and `fit_har` drops that row."""
    daily, vix = _toy_market(40)
    design = har_design(daily, vix[vix["day"] != daily["day"].iloc[-2]], C)
    assert np.isnan(design.loc[design.index[-1], "x4"])
    assert design.loc[design.index[1:-1], "x4"].notna().all()  # only the day after the hole is lost


def test_forecast_adds_the_lognormal_correction_and_drops_the_gap_term():
    row = pd.Series({"y": -8.0, "x1": -8.1, "x2": -8.2, "x3": -8.3, "x4": -8.4, "x5": -9.0})
    beta = np.array([-1.0, 0.4, 0.3, 0.1, 0.2, 0.05])
    fit = HarFit(refit_day=date(2019, 3, 1), beta=beta, s2=0.04, n=750, x5_mean=-11.0)
    rv, no_gap = forecast(fit, row)
    y = beta[0] + beta[1:] @ row[TERMS].to_numpy()
    assert rv == pytest.approx(np.exp(y + 0.04 / 2))
    assert no_gap == pytest.approx(np.exp(y + 0.04 / 2 - 0.05 * (-9.0 - -11.0)))  # x5 at its fit-window mean
    flat = HarFit(refit_day=date(2019, 3, 1), beta=np.array([-8.0, 0, 0, 0, 0, 0]), s2=0.0, n=750, x5_mean=-11.0)
    assert forecast(flat, row) == (pytest.approx(np.exp(-8.0)), pytest.approx(np.exp(-8.0)))


def test_har_series_refits_on_the_first_session_of_each_month(monkeypatch):
    daily, vix = _toy_market(800)
    refits = []
    real = har.fit_har
    monkeypatch.setattr(har, "fit_har",
                        lambda design, refit_day, window: refits.append(refit_day) or real(design, refit_day, window))
    frame = har_series(daily, vix, window=WINDOW, c=C, percentile_window=PCT_WINDOW, percentile_min=PCT_MIN)
    days = list(frame.index)
    month_starts = [d for i, d in enumerate(days)
                    if i == 0 or (d.year, d.month) != (days[i - 1].year, days[i - 1].month)]
    assert refits == month_starts[2:]  # Jan and Feb 2019 hold too few complete rows for six coefficients


def test_har_series_columns_and_the_percentile_floor():
    daily, vix = _toy_market(400)
    frame = har_series(daily, vix, window=WINDOW, c=C, percentile_window=PCT_WINDOW, percentile_min=PCT_MIN)
    assert list(frame.columns) == ["rv_hat", "rv_hat_nogap", "sigma_day", "har_pct"]
    assert np.allclose(frame["sigma_day"].dropna(), np.sqrt(frame["rv_hat"].dropna()))
    assert frame["rv_hat"].dropna().gt(0).all()
    first = frame["har_pct"].first_valid_index()
    assert len(frame.loc[:first, "rv_hat"].iloc[:-1].dropna()) == PCT_MIN
    assert frame["har_pct"].dropna().between(0.0, 1.0).all()


def test_a_day_whose_own_realised_variance_is_missing_still_gets_a_forecast():
    """The forecast for day t needs x1..x5, all known at 09:16; y_t is the target, known only after the close."""
    daily, vix = _toy_market(400)
    flat = daily.index[-1]
    daily.loc[flat, ["high", "low", "close"]] = daily.loc[flat, "open"]   # a zero-range day: y is NaN
    out = har_series(daily, vix, window=WINDOW, c=C, percentile_window=PCT_WINDOW, percentile_min=PCT_MIN)
    assert np.isnan(har_design(daily, vix, C)["y"].iloc[-1])
    assert not np.isnan(out["rv_hat"].iloc[-1])
