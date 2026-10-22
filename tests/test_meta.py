from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from quantdesk.clock import IST
from quantdesk.strategy.meta import Consensus, MetaModel, columns, fit_consensus, fit_meta, label
from quantdesk.strategy.types import Signal


def closes_frame(closes):
    ts = [datetime(2024, 3, 4, 10, 0, tzinfo=IST) + timedelta(minutes=i) for i in range(len(closes))]
    return pd.DataFrame({"ts": ts, "close": closes})


def test_label_target_before_stop():
    frame = closes_frame([100.0, 100.2, 99.6, 100.9])                  # target 100.69, stop 99.7
    sig = Signal("NIFTY", frame.ts[0], "long", 100.0, 99.9, 0, 99.95, 99.7, 0.3, 100.69)
    assert label(frame, sig, hard_exit_at=frame.ts.iloc[-1]) == 0      # 99.6 hits the stop first
    up = closes_frame([100.0, 100.2, 100.7, 99.0])
    assert label(up, sig, hard_exit_at=up.ts.iloc[-1]) == 1
    flat = closes_frame([100.0, 100.1, 100.2, 100.69])
    assert label(flat, sig, hard_exit_at=flat.ts.iloc[2]) == 0          # the target came after the hard exit


def test_label_for_a_short():
    frame = closes_frame([100.0, 99.8, 99.3])
    sig = Signal("NIFTY", frame.ts[0], "short", 100.0, 0, 100.1, 100.05, 100.3, 0.3, 99.31)
    assert label(frame, sig, hard_exit_at=frame.ts.iloc[-1]) == 1


def test_columns_layout():
    x = columns({"technical": 1.0, "options": None, "macro": -1.0}, "long", har_pct=0.8, dte=7)
    assert x.tolist() == pytest.approx([1.0, 0.0, -1.0, 1.0, 0.3, 1.0])


def test_ridge_recovers_the_direction_and_shrinks():
    rng = np.random.default_rng(3)
    X = rng.normal(size=(3000, 6)); true = np.array([0.8, 0, 0, 0, 0, 0])
    y = (rng.random(3000) < 1 / (1 + np.exp(-(X @ true - 0.5)))).astype(int)
    m = fit_meta(X, y, lam=10.0, split=0.8)
    assert 0.6 < m.beta[1] < 0.95 and abs(m.beta[2]) < 0.1     # beta[0] is the intercept
    unpenalised = fit_meta(X, y, lam=0.0, split=0.8)
    assert abs(m.beta[1]) < abs(unpenalised.beta[1])


def test_well_calibrated_models_get_no_platt():
    rng = np.random.default_rng(4)
    X = rng.normal(size=(5000, 6)); y = (rng.random(5000) < 1 / (1 + np.exp(-X[:, 0]))).astype(int)
    assert fit_meta(X, y, lam=10.0, split=0.8).platt is None


def test_an_overconfident_fit_gets_platt():
    rng = np.random.default_rng(5)
    n = 4000
    X = rng.normal(size=(n, 6))
    signal = X[:, 0]
    y = np.where(np.arange(n) < 0.8 * n, rng.random(n) < 1 / (1 + np.exp(-3 * signal)),   # the fit window
                 rng.random(n) < 1 / (1 + np.exp(-0.5 * signal))).astype(int)              # the calibration window
    assert fit_meta(X, y, lam=1.0, split=0.8).platt is not None


def test_macro_column_cannot_move_p_more_than_8_points():
    m = MetaModel(beta=np.array([0, 0, 0, 5.0, 0, 0, 0]), platt=None, base_rate=0.5, macro_clip=0.08)
    assert abs(m.predict(np.array([0, 0, 2.0, 0, 0, 0])) - 0.5) <= 0.0801


def test_model_round_trips_through_json():
    m = MetaModel(beta=np.arange(7.0) / 10, platt=(0.1, 0.9), base_rate=0.3, macro_clip=0.08)
    again = MetaModel.from_json(m.to_json())
    x = np.ones(6) * 0.2
    assert again.predict(x) == pytest.approx(m.predict(x))


def test_consensus_is_a_one_variable_logistic():
    rng = np.random.default_rng(6)
    s = rng.normal(size=4000)
    y = (rng.random(4000) < 1 / (1 + np.exp(-(0.3 + 1.2 * s)))).astype(int)
    c = fit_consensus(s, y)
    assert c.a == pytest.approx(0.3, abs=0.1) and c.b == pytest.approx(1.2, abs=0.15)
    assert Consensus(0.0, 1.0).predict(0.0) == 0.5
