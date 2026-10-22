"""Fitting a trial's probability model inside one CV training set (design §13).

The rows are every signal on the training days that has defined scores and a label, including setups a gate
or a cap later stopped. Warm-up rows have no scores and train nothing. Test days are never seen.
"""

import math

import numpy as np

from quantdesk.strategy.meta import columns, fit_consensus, fit_meta
from quantdesk.strategy.types import TrialConfig
from quantdesk.validation.hypotheses import param


def _rows(dataset, train_days: set):
    s = dataset.signals
    rows = s[s["day"].isin(train_days) & (s["failed"] != "warmup") & s["technical"].notna() & s["label"].notna()]
    return rows.sort_values("at")


def _v(x):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else float(x)


def train(dataset, train_days: set, cfg: TrialConfig, h: dict):
    if cfg.probability == "meta_ctx":
        raise NotImplementedError("CTX's reversal feature is built only if P4 says it runs (R37)")
    rows = _rows(dataset, train_days)
    y = rows["label"].astype(float).to_numpy()
    if cfg.probability == "consensus":
        s = np.array([np.mean([v for v in (_v(r.technical), _v(r.options), _v(r.macro)) if v is not None])
                      for r in rows.itertuples()])
        return fit_consensus(s, y)
    X = np.vstack([columns({"technical": _v(r.technical), "options": _v(r.options), "macro": _v(r.macro)}, r.side,
                           float(r.har_pct), int(r.dte)) for r in rows.itertuples()])
    return fit_meta(X, y, param(h, "meta.ridge_lambda"), param(h, "meta.calibration_split"),
                    param(h, "meta.macro_clip_prob"))
