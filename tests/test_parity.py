from datetime import date

from quantdesk.live.journal import Journal
from quantdesk.live.replay import backtest_day, replay_day, summary
from quantdesk.strategy.configs import config_for
from quantdesk.strategy.meta import Consensus
from quantdesk.validation.hypotheses import load_hypotheses
from tests.test_live_engine import FakeLiveSource
from tests.test_pipeline import DAY

H = load_hypotheses()


def test_live_replay_matches_the_backtest_decision_for_decision(tmp_path):
    source = FakeLiveSource()
    cfg, model = config_for("X1", {}), Consensus(0, 0)
    live = replay_day(source, DAY, cfg, model, H, Journal(tmp_path / "j.sqlite"), indices=("NIFTY",))
    back = backtest_day(source, DAY, cfg, model, H, indices=("NIFTY",))
    assert summary(live) == summary([d for d in back if (d.index, d.at) in {(x.index, x.at) for x in live}])
    assert any(d.alert for d in live)
