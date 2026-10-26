from datetime import date

import pandas as pd
import pytest

from quantdesk.backtest.ideas import idea_backtest, summarise
from quantdesk.strategy.configs import config_for
from quantdesk.strategy.meta import Consensus
from quantdesk.validation.hypotheses import load_hypotheses
from quantdesk.validation.pilots.run import IDEAS_RELAXED, with_values
from tests.test_live_engine import FakeLiveSource
from tests.test_pipeline import DAY

H = load_hypotheses()


def test_each_idea_is_filled_and_exited_like_the_live_paper_trade_one_at_a_time():
    rows = idea_backtest(FakeLiveSource(), [DAY], {"NIFTY": date(2019, 1, 1)}, config_for("X1", {}),
                         Consensus(-3.0, 0.0), with_values(H, IDEAS_RELAXED), H, date(2026, 10, 26))
    filled = rows[rows["status"] == "filled"]
    assert len(rows) == 1 and len(filled) == 1                     # later signals wait while the idea is open
    r = filled.iloc[0]
    assert r["pnl"] > 0 and r["r"] == pytest.approx(r["pnl"] / r["planned_loss"]) and r["p"] < 0.1
    assert r["entry_at"] > r["at"] and r["exit_at"] > r["entry_at"]


def test_the_summary_splits_the_research_years_from_2026():
    rows = pd.DataFrame({"day": [date(2024, 3, 5), date(2025, 6, 2), date(2026, 2, 3), date(2026, 2, 4)],
                         "index": "NIFTY", "status": ["filled", "filled", "filled", "lapsed"],
                         "r": [1.0, -1.0, 0.5, None], "pnl": [600.0, -500.0, 300.0, None],
                         "roi": [0.2, -0.15, 0.1, None], "reason": ["target", "stop", "deadline", None]})
    s = summarise(rows)
    assert s["all"]["ideas"] == 4 and s["all"]["filled"] == 3 and s["all"]["win_rate"] == pytest.approx(2 / 3)
    assert s["2019-2025"]["filled"] == 2 and s["2026"]["filled"] == 1
    assert s["all"]["mean_r"] == pytest.approx(0.5 / 3)
