from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from quantdesk.backtest.dataset import SIGNAL_COLUMNS, SignalDataset
from quantdesk.backtest.training import train
from quantdesk.clock import IST
from quantdesk.strategy.configs import config_for
from quantdesk.strategy.meta import Consensus, MetaModel
from quantdesk.validation.hypotheses import load_hypotheses

H = load_hypotheses()


def synthetic_signals(n=600, seed=0):
    rng = np.random.default_rng(seed)
    days = list(pd.bdate_range("2019-02-11", periods=n).date)
    tech = rng.normal(size=n)
    label = (rng.random(n) < 1 / (1 + np.exp(-(tech - 0.5)))).astype(int)
    rows = pd.DataFrame({"signal_id": [f"s{i}" for i in range(n)], "day": days,
                         "at": [datetime.combine(d, datetime.min.time(), tzinfo=IST) + timedelta(hours=10) for d in days],
                         "index": "NIFTY", "side": np.where(rng.random(n) < 0.5, "long", "short"), "failed": None,
                         "technical": tech, "options": rng.normal(size=n), "macro": 0.0, "har_pct": rng.random(n),
                         "dte": rng.integers(0, 6, n), "label": label})
    rows.loc[::10, "failed"] = "room_to_run"                       # skipped setups still train the model
    rows.loc[5, "failed"] = "warmup"
    return SignalDataset(rows.reindex(columns=SIGNAL_COLUMNS), pd.DataFrame())


def test_consensus_trains_on_training_days_only():
    ds = synthetic_signals()
    first_half = set(ds.signals["day"].iloc[:300])
    model = train(ds, first_half, config_for("B0", {}), H)
    assert isinstance(model, Consensus) and model.b > 0


def test_meta_model_uses_skipped_setups_but_not_warmup_rows():
    ds = synthetic_signals()
    model = train(ds, set(ds.signals["day"]), config_for("M1", {"X1": True}), H)
    assert isinstance(model, MetaModel) and model.beta[1] > 0


def test_ctx_is_not_built_until_its_condition_is_met():
    with pytest.raises(NotImplementedError):
        train(synthetic_signals(), set(), config_for("CTX", {}), H)
