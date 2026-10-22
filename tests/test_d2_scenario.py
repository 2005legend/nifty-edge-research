from quantdesk.validation.hypotheses import load_hypotheses, param
from quantdesk.validation.pilots.run import d2_scenario


def test_the_relaxed_idea_settings_skip_named_gates_only():
    from dataclasses import replace

    from quantdesk.strategy.configs import config_for
    from quantdesk.strategy.gates import first_failed_gate
    from quantdesk.strategy.meta import Consensus
    from quantdesk.strategy.pipeline import decide
    from quantdesk.validation.pilots.run import IDEAS_RELAXED, with_values
    from tests.test_pipeline import AT, TODAY, setup

    h = load_hypotheses()
    ctx, frame, helpers = setup()
    signal = replace(decide(ctx, frame, AT, config_for("B0", {}), Consensus(0, 0), helpers, h, TODAY).signal, b=0.0)
    assert first_failed_gate(signal, ctx, frame, helpers, h) == "stop_fit"
    skipping = with_values(h, {"gate.skip": ["stop_fit"]})
    assert first_failed_gate(signal, ctx, frame, helpers, skipping) != "stop_fit"
    relaxed = with_values(h, IDEAS_RELAXED)
    assert param(relaxed, "strike.gain_loss_min") == 1.0 and "room_in_time" in param(relaxed, "gate.skip")


def test_the_d2_scenario_is_15k_with_a_600_stop_and_leaves_the_registered_values_alone():
    h = load_hypotheses()
    s = d2_scenario(h)
    assert (param(s, "account.capital"), param(s, "account.risk_rupees"), param(s, "account.premium_budget")) == \
        (15000, 600, 14500)
    assert param(h, "account.risk_rupees") == 400 and param(h, "account.premium_budget") == 9500
