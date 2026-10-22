from datetime import date

import pandas as pd

from quantdesk.backtest.dataset import build_dataset, load_dataset, save_dataset
from quantdesk.derived.store import DerivedStore
from quantdesk.validation.hypotheses import load_hypotheses
from tests.test_pipeline import AT, DAY, TODAY, setup

H = load_hypotheses()


class FakeSource:
    def __init__(self):
        self.ctx, self.frame_, self.helpers_ = setup()
        self.recorded = []

    def context(self, index, day):
        return self.ctx

    def frame(self, ctx):
        return self.frame_

    def helpers(self, ctx, frame):
        return self.helpers_

    def record_signal(self, day, raw):
        self.recorded.append((day, raw))


def test_the_dataset_holds_each_signal_once_with_scores_label_and_candidates(tmp_path):
    source = FakeSource()
    ds = build_dataset(source, [DAY], {"NIFTY": DAY}, H, TODAY)
    row = ds.signals.set_index("at").loc[AT]
    assert row["failed"] is None or pd.isna(row["failed"])
    assert row["side"] == "long" and row["label"] in (0, 1) and row["technical"] is not None
    assert len(ds.candidates) > 0 and set(ds.candidates["signal_id"]) == {row["signal_id"]}
    assert source.recorded and source.recorded[0][0] == DAY
    derived = DerivedStore(tmp_path)
    save_dataset(ds, derived)
    again = load_dataset(derived)
    assert len(again.signals) == len(ds.signals) and len(again.candidates) == len(ds.candidates)


def test_an_index_before_its_start_is_skipped():
    ds = build_dataset(FakeSource(), [DAY], {"SENSEX": date(2025, 1, 1)}, H, TODAY)
    assert ds.signals.empty
