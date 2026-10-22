"""Prerequisites for a trial, and the pre-flight checklist before B0 (R36, R37, R38).

A trial runs only when all of these hold:
- the pilots it depends on have reported
- the owner has made the D2 choice
- the recorded-chain pricing check has passed
- the trial's own run condition holds

Pre-flight adds:
- the frozen files are present
- the pre-registration is frozen and tagged
- the tree is clean
- the look-ahead test and both controls pass
"""

import json
from pathlib import Path

from quantdesk.validation.hypotheses import TRIAL_CAP, HypothesesError, param

PILOTS = ("CLOCK", "P1", "P2", "P4", "P9", "P10", "D2")
FROZEN = ("clock_v1.yaml", "surface_v1.yaml", "shock_v1.yaml")
ALWAYS = {"B0", "X1", "M1", "RV-2", "RV-1"}
TEST_FILES = ("tests/test_truncation.py", "tests/test_controls.py", "tests/test_engine.py", "tests/test_trial.py")


def _p4_ctx_runs(pilots_dir: Path) -> bool:
    path = pilots_dir / "P4.md"
    return path.exists() and "| ctx_runs | True |" in path.read_text(encoding="utf-8")


def _owner(h: dict, key: str):
    try:
        return param(h, key)
    except HypothesesError:
        return None


def run_if_met(trial_id: str, accepted: dict, trials_run: list, pilots_dir: Path, h: dict) -> bool:
    remaining = TRIAL_CAP - len(trials_run)
    if trial_id in ALWAYS:
        return True
    if trial_id == "RV-3":
        return bool(accepted.get("B0") or accepted.get("X1")) and remaining >= 4
    if trial_id in ("RV-4", "ROD"):
        return False                       # the gamma engine (P3) is not built; it runs only if it validates
    if trial_id == "RV-5":
        return sum(bool(accepted.get(t)) for t in ("RV-2", "RV-3", "RV-4")) >= 2
    if trial_id == "CTX":
        return _p4_ctx_runs(pilots_dir) and remaining >= 3
    if trial_id == "X2":
        return _owner(h, "owner.x2_opt_in") is True
    return False


def pricing_passed(research_dir: Path) -> bool:
    path = research_dir / "pricecheck.json"
    return path.exists() and bool(json.loads(path.read_text(encoding="utf-8")).get("passed"))


def prerequisites(trial_id: str, accepted: dict, trials_run: list, research_dir: Path, h: dict) -> dict[str, bool]:
    pilots_dir = research_dir / "pilots"
    return {"pilots": all((pilots_dir / f"{p}.md").exists() for p in PILOTS),
            "d2_decided": _owner(h, "owner.d2_choice") is not None,
            "pricing_check": pricing_passed(research_dir),
            "run_if": run_if_met(trial_id, accepted, trials_run, pilots_dir, h)}


def preflight(project: Path, registry, h: dict, run_tests) -> dict[str, bool]:
    research = project / "research"
    frozen = project / "config" / "frozen"
    prereg = research / "prereg.json"
    checks = {"frozen_files": all((frozen / f).exists() for f in FROZEN),
              "pilots_reported": all((research / "pilots" / f"{p}.md").exists() for p in PILOTS),
              "d2_decided": _owner(h, "owner.d2_choice") is not None,
              "pricing_check_passed": pricing_passed(research),
              "preregistration_frozen": prereg.exists() and
                  json.loads(prereg.read_text(encoding="utf-8")).get("hypotheses_hash") == registry.hypotheses_hash(),
              "tree_clean": not registry.git(["status", "--porcelain"]),
              "lookahead_and_controls_pass": run_tests(list(TEST_FILES)) == 0}
    checks["ready_for_B0"] = all(checks.values())
    return checks
