import copy

import pytest

from quantdesk.validation.hypotheses import HypothesesError, load_hypotheses, param, validate


def test_the_registered_file_is_complete():
    """research/hypotheses.yaml is the pre-registration: every value sourced, every gate fully specified."""
    assert validate(load_hypotheses()) == []


def test_a_parameter_without_provenance_is_a_problem():
    h = copy.deepcopy(load_hypotheses())
    del h["parameters"]["h1.band_v"]["provenance"]
    assert any("h1.band_v" in p and "provenance" in p for p in validate(h))


def test_a_gate_naming_an_unknown_parameter_is_a_problem():
    h = copy.deepcopy(load_hypotheses())
    h["gates"]["stop_fit"]["parameters"].append("no.such.param")
    assert any("no.such.param" in p for p in validate(h))


def test_the_registry_cannot_exceed_the_trial_cap():
    h = copy.deepcopy(load_hypotheses())
    extra = dict(h["registry"][0], id="EXTRA")
    h["registry"] += [extra] * 3
    assert any("cap" in p for p in validate(h))


def test_param_returns_the_value_and_refuses_unknown_keys():
    h = load_hypotheses()
    assert param(h, "h1.band_v") == 1.0
    with pytest.raises(HypothesesError):
        param(h, "h1.no_such_value")
