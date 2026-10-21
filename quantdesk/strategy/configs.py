"""What each registry trial runs (spec §6.3 registry, research/hypotheses.yaml `registry`).

Each trial builds on the accepted ones before it. M1 takes the exit that won (X1 if it was accepted, else
X0), and each RV trial adds its hurdle to the hurdles already accepted. `accepted` maps a trial id to whether
it passed, and only the registry fills it in, so no caller can quietly pick a configuration.
"""

from quantdesk.strategy.types import TrialConfig

HURDLE_OF = {"RV-2": "shock", "RV-1": "stress", "RV-3": "slow_trend", "RV-4": "gamma"}


def _exit(accepted: dict) -> str:
    return "X1" if accepted.get("X1") else "X0"


def _accepted_hurdles(accepted: dict) -> frozenset:
    return frozenset(h for trial, h in HURDLE_OF.items() if accepted.get(trial))


def config_for(trial_id: str, accepted: dict[str, bool]) -> TrialConfig:
    if trial_id == "B0":
        return TrialConfig("B0", "X0", "consensus")
    if trial_id == "X1":
        return TrialConfig("X1", "X1", "consensus")
    if trial_id == "M1":
        return TrialConfig("M1", _exit(accepted), "meta")
    if trial_id in HURDLE_OF:
        return TrialConfig(trial_id, _exit(accepted), "meta", _accepted_hurdles(accepted) | {HURDLE_OF[trial_id]})
    if trial_id == "RV-5":
        stress = frozenset({"stress"}) if accepted.get("RV-1") else frozenset()
        return TrialConfig("RV-5", _exit(accepted), "meta", frozenset({"shock", "slow_trend", "gamma"}) | stress)
    if trial_id == "CTX":
        return TrialConfig("CTX", _exit(accepted), "meta_ctx", _accepted_hurdles(accepted))
    if trial_id == "X2":
        return TrialConfig("X2", "X2", "meta", _accepted_hurdles(accepted))
    if trial_id == "ROD":
        return TrialConfig("ROD", "X0", "consensus", frozenset(), trigger="rod")
    raise KeyError(f"no configuration for trial {trial_id!r}; a reserve slot re-runs a named trial's configuration")
