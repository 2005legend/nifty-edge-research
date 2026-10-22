"""Labels, the ridge-logistic meta-model, and the B0 consensus (spec §6.1 step 5, design §13, R28).

Every H1 signal in the training days is a row, including signals that a gate or a cap later stopped. The label
is whether the index reached the planning target before the stop, before the hard exit.

The model is a ridge logistic on six columns with a fixed penalty (λ = 10, no tuning loop), fitted with
scipy. Platt calibration is added only when the calibration slope on the last 20% of the training rows has a
95% interval that excludes 1. The macro column may move p by at most 8 points (spec §5A.2).
"""

import math
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from quantdesk.strategy.types import Signal

Z95 = 1.959964


def label(frame: pd.DataFrame, signal: Signal, hard_exit_at: datetime) -> int:
    path = frame[(frame["ts"] >= signal.at) & (frame["ts"] <= hard_exit_at)].sort_values("ts")
    for close in path["close"]:
        if signal.side == "long":
            if close >= signal.target_level:
                return 1
            if close <= signal.stop_level:
                return 0
        else:
            if close <= signal.target_level:
                return 1
            if close >= signal.stop_level:
                return 0
    return 0


def columns(scores: dict, side: str, har_pct: float, dte: int) -> np.ndarray:
    def value(name):
        v = scores.get(name)
        return 0.0 if v is None or (isinstance(v, float) and math.isnan(v)) else float(v)

    return np.array([value("technical"), value("options"), value("macro"), 1.0 if side == "long" else 0.0,
                     har_pct - 0.5, min(max(dte, 0), 5) / 5.0])


def _sigmoid(z):
    return 1.0 / (1.0 + np.exp(-z))


def _logit(p):
    p = np.clip(p, 1e-9, 1 - 1e-9)
    return np.log(p / (1 - p))


def _fit_logistic(X: np.ndarray, y: np.ndarray, lam: float) -> np.ndarray:
    """Intercept first; the penalty skips the intercept."""
    A = np.column_stack([np.ones(len(X)), X])

    def loss(beta):
        z = A @ beta
        value = np.sum(np.logaddexp(0.0, z) - y * z) + 0.5 * lam * beta[1:] @ beta[1:]
        grad = A.T @ (_sigmoid(z) - y)
        grad[1:] += lam * beta[1:]
        return value, grad

    return minimize(loss, np.zeros(A.shape[1]), jac=True, method="L-BFGS-B").x


def _slope_ci(p: np.ndarray, y: np.ndarray) -> tuple[float, float, float, np.ndarray]:
    """Calibration slope of y on logit(p), its 95% Wald interval, and the (a, b) fit itself."""
    x = _logit(p)[:, None]
    beta = _fit_logistic(x, y, 0.0)
    A = np.column_stack([np.ones(len(x)), x])
    w = _sigmoid(A @ beta)
    info = A.T @ (A * (w * (1 - w))[:, None])
    se = math.sqrt(np.linalg.inv(info)[1, 1])
    return float(beta[1]), float(beta[1] - Z95 * se), float(beta[1] + Z95 * se), beta


@dataclass
class MetaModel:
    beta: np.ndarray                          # intercept, then the 6 columns
    platt: tuple | None
    base_rate: float
    macro_clip: float = 0.08

    def predict(self, x: np.ndarray) -> float:
        x = np.asarray(x, dtype=float)
        terms = self.beta[1:] * x
        limit = self.macro_clip / max(self.base_rate * (1 - self.base_rate), 1e-6)
        terms[2] = float(np.clip(terms[2], -limit, limit))       # the macro column (spec §5A.2)
        p = float(_sigmoid(self.beta[0] + terms.sum()))
        if self.platt is not None:
            a, b = self.platt
            p = float(_sigmoid(a + b * _logit(p)))
        return p

    def to_json(self) -> dict:
        return {"beta": [float(v) for v in self.beta], "platt": list(self.platt) if self.platt else None,
                "base_rate": self.base_rate, "macro_clip": self.macro_clip}

    @classmethod
    def from_json(cls, d: dict) -> "MetaModel":
        return cls(np.asarray(d["beta"], dtype=float), tuple(d["platt"]) if d["platt"] else None,
                   float(d["base_rate"]), float(d.get("macro_clip", 0.08)))


def fit_meta(X: np.ndarray, y: np.ndarray, lam: float, split: float, macro_clip: float = 0.08) -> MetaModel:
    X, y = np.asarray(X, dtype=float), np.asarray(y, dtype=float)
    cut = int(len(y) * split)
    platt = None
    if 0 < cut < len(y) and len(np.unique(y[cut:])) == 2:
        early = MetaModel(_fit_logistic(X[:cut], y[:cut], lam), None, float(y[:cut].mean()), macro_clip)
        p_hat = np.array([early.predict(x) for x in X[cut:]])
        _, lo, hi, ab = _slope_ci(p_hat, y[cut:])
        if not lo <= 1.0 <= hi:
            platt = (float(ab[0]), float(ab[1]))
    return MetaModel(_fit_logistic(X, y, lam), platt, float(y.mean()), macro_clip)


@dataclass(frozen=True)
class Consensus:
    a: float
    b: float

    def predict(self, mean_score: float) -> float:
        return float(_sigmoid(self.a + self.b * mean_score))


def fit_consensus(s: np.ndarray, y: np.ndarray) -> Consensus:
    beta = _fit_logistic(np.asarray(s, dtype=float)[:, None], np.asarray(y, dtype=float), 0.0)
    return Consensus(float(beta[0]), float(beta[1]))
