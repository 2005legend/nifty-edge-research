from datetime import date, datetime, time, timedelta

import numpy as np
import pandas as pd
import pytest

from quantdesk.backtest.dataset import CANDIDATE_COLUMNS, SIGNAL_COLUMNS, SignalDataset
from quantdesk.clock import IST
from quantdesk.pricing.quotes import Quote
from quantdesk.strategy.gates import Helpers
from quantdesk.validation.hypotheses import load_hypotheses
from quantdesk.validation.trial import run_trial
from quantdesk.validation.verdict import evaluate, write_verdict
from tests.test_bands import make_ctx
from tests.test_registry import OK, Git, research
from quantdesk.validation.registry import Registry

H = load_hypotheses()
TODAY = date(2026, 10, 22)
SESSIONS = list(pd.bdate_range("2019-01-01", "2025-12-31").date)
SIGNAL_DAYS = SESSIONS[30::4]


def up(day):
    return day.toordinal() % 3 != 0          # two days in three run up after the signal


class KindQuotes:
    def __init__(self, frame):
        self.close = frame.set_index("ts")["close"]

    def mid(self, index, expiry, strike, kind, at, spot=None, vix=None, sigma_scale=1.0):
        s = spot if spot is not None else self.close[at - timedelta(minutes=1)]
        move = s - 22010.0 if kind == "CE" else 22010.0 - s
        return 50.0 + 0.2 * move + 0.8 * max(0.0, move)

    def quote(self, index, expiry, strike, kind, at):
        m = self.mid(index, expiry, strike, kind, at)
        return Quote(bid=round(m - 0.1, 2), ask=round(m + 0.1, 2), mid=m)


class GenericSource:
    def context(self, index, day):
        return make_ctx(np.full(375, 0.0005), open_=21980.0, prev_close=21980.0, day=day,
                        expiry_1=day + timedelta(days=2), expiry_2=day + timedelta(days=9), hard_exit=time(11, 0))

    def frame(self, ctx):
        t0 = datetime.combine(ctx.day, time(9, 50), tzinfo=IST)
        ts = [t0 + timedelta(minutes=i) for i in range(75)]
        size = 0.8 + 0.4 * (ctx.day.toordinal() % 7) / 6.0            # every day moves a little differently
        step = size if up(ctx.day) else -size
        # flat until 10:03, so a 3-minute-late order is still inside the chase cap, then the day's move
        close = [22010.0 if t < t0 + timedelta(minutes=13) else 22010.0 + step * (i - 12) for i, t in enumerate(ts)]
        return pd.DataFrame({"ts": ts, "close": close, "vwap": 21995.0, "upper": 21991.0, "lower": 21969.0})

    def helpers(self, ctx, frame):
        return Helpers(clock=None, surface=None, quotes=KindQuotes(frame))

    def record_signal(self, day, raw):
        pass


def dataset():
    rng = np.random.default_rng(0)
    rows, cands = [], []
    for i, day in enumerate(SIGNAL_DAYS):
        sid = f"NIFTY-{day:%Y%m%d}1000"
        at = datetime.combine(day, time(10, 0), tzinfo=IST)
        tech = (1.0 if up(day) else -1.0) + rng.normal(0, 0.3)
        rows.append({"signal_id": sid, "day": day, "index": "NIFTY", "at": at, "side": "long", "ref_close": 22010.0,
                     "upper": 21991.0, "lower": 21969.0, "vwap": 21995.0, "stop_level": 21995.0, "b": 15.0,
                     "target_level": 22044.5, "failed": None, "technical": tech, "options": 0.0, "macro": 0.0,
                     "har_pct": 0.5, "dte": 2, "label": int(up(day)), "delta_event": 0.0, "delta_shock": 0.0,
                     "delta_stress": 0.0, "lot": 50, "vix_prev_close": 12.0 + (i % 3), "weekday": day.weekday(),
                     "expiry_day": False})
        cands.append({"signal_id": sid, "index": "NIFTY", "expiry": day + timedelta(days=2), "strike": 22000.0,
                      "kind": "CE", "lot": 50, "ask": 50.1, "delta": 0.45, "gain": 900.0, "loss": 300.0})
    return SignalDataset(pd.DataFrame(rows).reindex(columns=SIGNAL_COLUMNS),
                         pd.DataFrame(cands).reindex(columns=CANDIDATE_COLUMNS))


@pytest.fixture(scope="module")
def outcome(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("trial")
    registry = Registry(research(tmp), tmp, git=Git())
    registry.freeze()
    metrics = run_trial("B0", registry, dataset(), GenericSource(), H, TODAY, {}, OK, "data1", SESSIONS)
    return registry, metrics


def test_a_trial_runs_every_split_and_records_one_row(outcome):
    registry, metrics = outcome
    assert registry.trials_run() == ["B0"]
    assert set(metrics["gates"]) == {"trades_per_fold", "t", "walk_forward_positive", "years", "dsr", "pbo",
                                     "permutation", "delay_3", "post_publication"}
    assert metrics["pbo"] is None                      # one trial: PBO does not apply
    assert metrics["n_trials_for_dsr"] == 46 + 1
    assert (registry.dir / "trials" / "B0" / "models.json").exists()


def test_a_planted_edge_is_found(outcome):
    _, metrics = outcome
    assert metrics["mean_net_r"] > 0 and metrics["t_stat"] > 2 and metrics["walk_forward"]["mean"] > 0
    assert metrics["permutation_p"] < 0.05


def test_a_clean_edge_passes_every_gate_and_turns_alerts_on(outcome):
    registry, metrics = outcome
    assert metrics["passed"], metrics["gates"]
    assert evaluate(registry, H, pricing_passed=True)["status"] == "alert-on"


def test_the_verdict_needs_the_pricing_check(outcome, tmp_path):
    registry, metrics = outcome
    blocked = evaluate(registry, H, pricing_passed=False)
    assert blocked["status"] == "alert-off"
    if metrics["passed"]:
        assert any("pricing" in r for r in blocked["reasons"])
    result = evaluate(registry, H, pricing_passed=True)
    assert result["status"] == ("alert-on" if metrics["passed"] else "alert-off")
    assert "SP2 verdict" in write_verdict(result, tmp_path / "VERDICT.md").read_text(encoding="utf-8")
