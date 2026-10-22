from datetime import date

import pandas as pd

from quantdesk.strategy.daycard import DayLoader
from quantdesk.validation.hypotheses import load_hypotheses
from quantdesk.validation.pilots.run import eligible_days_per_year, p2_summary, run_p1, run_p4, run_p10
from tests.derived_fixture import build, clock_for, flat_surface

H = load_hypotheses()


def test_p1_runs_end_to_end_on_a_small_store(tmp_path):
    derived, days = build(tmp_path, n_days=40)
    loader = DayLoader(derived, clock_for(days), flat_surface(), H, events=[])
    h = {**H, "parameters": {**H["parameters"], "backtest.nifty_from": {**H["parameters"]["backtest.nifty_from"],
                                                                         "value": str(days[0])}}}
    records, moves = run_p1(loader, h, today=date(2026, 10, 22), end=days[-1])
    assert set(records.columns) >= {"day", "index", "failed", "b", "vix_tercile", "lot"}
    assert len(records) > 0 and (records["failed"] == "warmup").all()       # 40 days: HAR never warms up
    assert moves.empty


def test_eligible_days_count_each_day_once():
    records = pd.DataFrame({"day": [date(2021, 1, 4)] * 3 + [date(2022, 1, 4)], "failed": [None, None, "stop_fit", None]})
    assert eligible_days_per_year(records, years=range(2021, 2023)) == 1.0


def test_p2_summary_and_p10_handle_empty_input():
    assert p2_summary(pd.DataFrame()) == {"setups": 0}
    out = run_p10(pd.DataFrame({"day": [date(2021, 1, 4)], "failed": ["stop_fit"]}), H)
    assert out["p_all_gates"] == 0.0
