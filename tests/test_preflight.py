import json

from quantdesk.validation.hypotheses import load_hypotheses
from quantdesk.validation.preflight import FROZEN, PILOTS, prerequisites, preflight, run_if_met
from quantdesk.validation.registry import Registry
from tests.test_registry import Git, research

H = load_hypotheses()


def test_run_conditions():
    assert run_if_met("B0", {}, [], None, H) and run_if_met("RV-1", {}, [], None, H)
    assert run_if_met("RV-3", {"B0": True}, ["B0"], None, H)
    assert not run_if_met("RV-3", {"B0": False, "X1": False}, ["B0", "X1"], None, H)
    assert not run_if_met("RV-3", {"B0": True}, [f"T{i}" for i in range(10)], None, H)      # fewer than 4 slots left
    assert not run_if_met("RV-4", {}, [], None, H)                                       # gamma engine not built
    assert run_if_met("RV-5", {"RV-2": True, "RV-3": True}, [], None, H)
    assert not run_if_met("X2", {}, [], None, H)                                         # no owner opt-in yet


def test_ctx_follows_the_p4_report(tmp_path):
    (tmp_path / "P4.md").write_text("| ctx_runs | True |\n")
    assert run_if_met("CTX", {}, [], tmp_path, H)
    (tmp_path / "P4.md").write_text("| ctx_runs | False |\n")
    assert not run_if_met("CTX", {}, [], tmp_path, H)


def test_prerequisites_and_preflight_name_what_is_missing(tmp_path):
    res = research(tmp_path)
    pre = prerequisites("B0", {}, [], res, H)
    assert pre["run_if"] and not pre["pilots"] and not pre["pricing_check"] and not pre["d2_decided"]
    for p in PILOTS:
        (res / "pilots").mkdir(exist_ok=True)
        (res / "pilots" / f"{p}.md").write_text("ok")
    (res / "pricecheck.json").write_text(json.dumps({"passed": True}))
    (tmp_path / "config" / "frozen").mkdir(parents=True)
    for f in FROZEN:
        (tmp_path / "config" / "frozen" / f).write_text("x")
    registry = Registry(res, tmp_path, git=Git())
    registry.freeze()
    checks = preflight(tmp_path, registry, H, run_tests=lambda files: 0)
    assert checks["frozen_files"] and checks["pilots_reported"] and checks["pricing_check_passed"]
    assert checks["preregistration_frozen"] and checks["tree_clean"] and checks["lookahead_and_controls_pass"]
    assert not checks["d2_decided"] and not checks["ready_for_B0"]
