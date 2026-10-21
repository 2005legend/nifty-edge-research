"""research/hypotheses.yaml: every SP2 parameter and gate, fixed before any outcome is seen (spec §6.3, §6.4).

Code reads its numbers from here through `param`, so a value lives in one place and its source and
provenance travel with it. Changing the file after the `prereg-v1` tag changes its hash, which the
trial registry refuses (M7).
"""

from pathlib import Path

import yaml

from quantdesk.config import project_root

TRIAL_CAP = 13
PROVENANCE = {"a_priori", "research_value", "design_ruling", "after_full_sample_look", "owner", "spec"}
GATE_KEYS = ("rule", "parameters", "source")
REGISTRY_KEYS = ("id", "slot", "config", "run_if")
PILOT_KEYS = ("id", "measures", "decides", "costs_trial")


class HypothesesError(KeyError):
    pass


def hypotheses_path() -> Path:
    return project_root() / "research" / "hypotheses.yaml"


def load_hypotheses(path: Path | None = None) -> dict:
    return yaml.safe_load((path or hypotheses_path()).read_text(encoding="utf-8"))


def param(h: dict, key: str):
    try:
        return h["parameters"][key]["value"]
    except KeyError:
        raise HypothesesError(f"{key} is not pre-registered in research/hypotheses.yaml") from None


def validate(h: dict) -> list[str]:
    """Problems that make the pre-registration incomplete; empty when it is complete."""
    problems = []
    params = h.get("parameters", {})
    for key, entry in params.items():
        for field in ("value", "source", "provenance"):
            if field not in entry:
                problems.append(f"parameter {key}: missing {field}")
        if entry.get("provenance") not in PROVENANCE:
            problems.append(f"parameter {key}: provenance {entry.get('provenance')!r} not in {sorted(PROVENANCE)}")
    for name, gate in h.get("gates", {}).items():
        problems += [f"gate {name}: missing {k}" for k in GATE_KEYS if k not in gate]
        problems += [f"gate {name}: unknown parameter {p}" for p in gate.get("parameters", []) if p not in params]
    registry = h.get("registry", [])
    if len(registry) > TRIAL_CAP:
        problems.append(f"registry has {len(registry)} entries, over the cap of {TRIAL_CAP}")
    ids = [entry.get("id") for entry in registry]
    if len(ids) != len(set(ids)):
        problems.append("registry ids are not unique")
    for entry in registry:
        problems += [f"registry {entry.get('id')}: missing {k}" for k in REGISTRY_KEYS if k not in entry]
    for pilot in h.get("pilots", []):
        problems += [f"pilot {pilot.get('id')}: missing {k}" for k in PILOT_KEYS if k not in pilot]
    return problems
