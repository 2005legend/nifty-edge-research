import copy
from datetime import date
from pathlib import Path

import pytest

from quantdesk.config import load_settings
from quantdesk.instruments import load_master
from quantdesk.recorder.plan import plan_subscriptions, recenter

FIXTURE = Path(__file__).parent / "fixtures" / "master_small.json"
TODAY = date(2026, 10, 19)
SPOTS = {"NIFTY": 22550.0, "SENSEX": 73400.0}
CONSTITUENTS = {"RELIANCE": "2885", "HDFCBANK": "1333", "INFY": "1594"}


@pytest.fixture(scope="module")
def master():
    return load_master(FIXTURE)


def option_tokens(plan):
    return set(plan.option_meta["token"])


def test_plan_counts_and_depth(master):
    plan = plan_subscriptions(master, SPOTS, TODAY, CONSTITUENTS, load_settings())
    meta = plan.option_meta
    for underlying in ("NIFTY", "SENSEX"):
        sub = meta[meta["underlying"] == underlying]
        assert sub["expiry"].nunique() == 2
        assert sub["strike"].nunique() == 31
        assert len(sub) == 31 * 2 * 2
    assert len(plan.depth_tokens) == 7 * 2 * 2
    assert plan.reduced is False
    assert plan.width == 15
    assert {"99926000", "99919000", "99926017"} <= plan.index_tokens
    assert plan.count() == 31 * 2 * 2 * 2 + 3 + 2 + 3
    assert set(plan.tokens) == {1, 2, 3, 4}


def test_plan_reduces_width_when_over_budget(master):
    settings = copy.deepcopy(load_settings())
    settings["recorder"]["max_tokens_per_connection"] = 200
    plan = plan_subscriptions(master, SPOTS, TODAY, CONSTITUENTS, settings)
    assert plan.width == 10
    assert plan.reduced is True
    assert plan.count() <= 200


def test_recenter_adds_only_when_moved_more_than_5_strikes(master):
    settings = load_settings()
    plan = plan_subscriptions(master, SPOTS, TODAY, CONSTITUENTS, settings)
    before = option_tokens(plan)

    same_plan, added = recenter(plan, {"NIFTY": 22550 + 5 * 50, "SENSEX": 73400.0}, master, settings)
    assert added == {}

    new_plan, added = recenter(plan, {"NIFTY": 22550 + 6 * 50, "SENSEX": 73400.0}, master, settings)
    added_tokens = {t for toks in added.values() for t in toks}
    assert added_tokens
    assert not (added_tokens & before)
    assert before <= option_tokens(new_plan)
    meta = new_plan.option_meta
    new_strikes = set(meta[meta["token"].isin(added_tokens)]["strike"])
    assert min(new_strikes) > 22550 + 15 * 50


def test_recenter_stays_within_the_token_budget(master):
    """Backlog 13: a recentre added strikes without re-checking max_tokens_per_connection."""
    import copy

    settings = copy.deepcopy(load_settings())
    plan = plan_subscriptions(master, SPOTS, TODAY, CONSTITUENTS, settings)
    settings["recorder"]["max_tokens_per_connection"] = plan.count() + 2
    new_atm = 22550 + 6 * 50
    new_plan, added = recenter(plan, {"NIFTY": new_atm, "SENSEX": 73400.0}, master, settings)
    added_tokens = {t for toks in added.values() for t in toks}
    assert new_plan.count() <= settings["recorder"]["max_tokens_per_connection"]
    assert len(added_tokens) == 2
    meta = new_plan.option_meta
    kept = meta[meta["token"].isin(added_tokens)]
    # The new chain's first strike outside the old one (22550 + 16 steps) is nearest the new ATM: CE and PE.
    assert set(kept["strike"]) == {22550 + 16 * 50}
    assert set(kept["side"]) == {"CE", "PE"}
