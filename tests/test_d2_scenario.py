from quantdesk.validation.hypotheses import load_hypotheses, param
from quantdesk.validation.pilots.run import d2_scenario


def test_the_d2_scenario_is_15k_with_a_600_stop_and_leaves_the_registered_values_alone():
    h = load_hypotheses()
    s = d2_scenario(h)
    assert (param(s, "account.capital"), param(s, "account.risk_rupees"), param(s, "account.premium_budget")) == \
        (15000, 600, 14500)
    assert param(h, "account.risk_rupees") == 400 and param(h, "account.premium_budget") == 9500
