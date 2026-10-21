import copy

import pytest

from quantdesk.validation.hypotheses import HypothesesError, load_hypotheses, param, validate

NEW_KEYS = ["event.rebalance_hard_exit", "planning.stop_horizon_min", "planning.target_horizon_min",
            "fill.sign_flip_check_min", "exit.x0_stall_min", "exit.x0_deadline_min", "macro.score_terms",
            "macro.fii_flip_window", "shock.cusum_sigma_window", "shock.cusum_block", "shock.cusum_resamples",
            "clock.weight_winsor_q", "pricing.forward", "pricing.skew_floor", "pricing.skew_max_abs_z",
            "har.overnight_c", "har.percentile_min", "gate.vol_rich_reference_time", "gate.dsr_sr_sd_floor",
            "cv.embargo_both_sides", "options_score.strike_steps", "options_score.rr_delta",
            "meta.calibration_split", "alert.entry_limit_ticks", "alert.backstop_limit"]


def test_the_registered_file_is_complete():
    """research/hypotheses.yaml is the pre-registration: every value sourced, every gate fully specified."""
    assert validate(load_hypotheses()) == []


def test_plan_parameters_are_registered():
    h = load_hypotheses()
    assert [k for k in NEW_KEYS if k not in h["parameters"]] == []
    assert param(h, "planning.stop_horizon_min") == 15 and param(h, "har.percentile_min") == 60
    assert validate(h) == []


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
