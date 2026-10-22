import numpy as np
import pandas as pd
import pytest

from quantdesk.validation.stats import addon_gate, pbo, permutation_p, post_publication_ratio, t_stat


def test_pbo_is_about_half_on_noise_and_near_zero_for_one_dominant_trial():
    rng = np.random.default_rng(0)
    noise = rng.normal(0, 1, (1000, 20))
    assert 0.3 < pbo(noise, S=10) < 0.7
    dominant = noise.copy()
    dominant[:, 3] += 0.5
    assert pbo(dominant, S=10) < 0.1


def test_pbo_needs_two_trials():
    assert pbo(np.zeros((100, 1)), S=10) is None


def test_permutation_detects_skill_and_not_its_absence():
    actual, mirror = np.ones(60), -np.ones(60)
    buckets = np.repeat(np.arange(6), 10)
    assert permutation_p(actual, mirror, buckets, rounds=1000, seed=1) < 0.01
    same = np.random.default_rng(2).normal(size=60)
    assert permutation_p(same, same, buckets, rounds=200, seed=1) > 0.5


def test_post_publication_ratio():
    assert post_publication_ratio(0.2, 0.08) == pytest.approx(0.4)
    assert np.isnan(post_publication_ratio(-0.1, 0.1))


def test_addon_gate_compares_on_identical_setups():
    days = list(pd.bdate_range("2020-01-01", "2025-12-31").date)
    rng = np.random.default_rng(3)
    ids = [f"s{i}" for i in range(600)]
    sig_days = [days[i * 2] for i in range(600)]
    old = pd.DataFrame({"signal_id": ids, "day": sig_days, "r": rng.normal(0, 1, 600)})
    better = old.assign(r=old["r"] + 0.3)
    out = addon_gate(better, old, days, years=[2020, 2021, 2022, 2023, 2024, 2025])
    assert out["passed"] and out["paired_t"] > 1
    assert not addon_gate(old, better, days, years=[2020, 2021, 2022, 2023, 2024, 2025])["passed"]


def test_t_stat():
    assert t_stat(np.array([1.0, 1.0, 1.0])) != t_stat(np.array([1.0, 1.1, 0.9]))
