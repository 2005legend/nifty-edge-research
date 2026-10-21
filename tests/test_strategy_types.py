import pytest

from quantdesk.strategy.configs import config_for


def test_registry_configs_build_on_accepted_trials():
    assert config_for("B0", {}).exit_policy == "X0"
    assert config_for("B0", {}).probability == "consensus"
    assert config_for("M1", {"X1": True}).exit_policy == "X1"
    assert config_for("M1", {"X1": False}).exit_policy == "X0"
    rv1 = config_for("RV-1", {"X1": True, "RV-2": True})
    assert rv1.probability == "meta" and rv1.hurdles == frozenset({"shock", "stress"})
    assert config_for("RV-1", {"X1": True, "RV-2": False}).hurdles == frozenset({"stress"})


def test_x2_and_the_conditional_trials_have_configs():
    assert config_for("X2", {"X1": True}).exit_policy == "X2"
    assert config_for("RV-3", {"X1": True, "RV-2": True, "RV-1": False}).hurdles == frozenset({"shock", "slow_trend"})
    with pytest.raises(KeyError):
        config_for("NOPE", {})
