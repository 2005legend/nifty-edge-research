"""The verdict (spec §6.3, design §14): alert-on for the last accepted configuration in registry order, or
alert-off.

A trial is accepted when it passes `validation_pass`. A regime add-on must also beat its predecessor on
identical setups (`addon_gate`). Alert-on further needs the recorded-chain pricing check to have passed (R17,
R38). Even then, add-ons built on parameters chosen after a full-sample look stay in shadow until the clean
forward holdout confirms them (R33).
"""

import json
from datetime import date
from pathlib import Path

import pandas as pd

from quantdesk.validation.hypotheses import param
from quantdesk.validation.stats import addon_gate

ORDER = ["B0", "X1", "M1", "RV-2", "RV-1", "RV-3", "RV-4", "RV-5", "CTX", "X2"]
ADDONS = {"RV-2", "RV-1", "RV-3", "RV-4", "RV-5", "CTX"}
AFTER_LOOK = {"RV-2", "RV-3"}            # shock and slow-trend parameters were chosen after full-sample looks


def _metrics(registry, trial: str) -> dict:
    return json.loads((registry.dir / "trials" / trial / "metrics.json").read_text(encoding="utf-8"))


def _trades(registry, trial: str) -> pd.DataFrame:
    frame = pd.read_parquet(registry.dir / "trials" / trial / "trades.parquet")
    return frame[(frame.get("part") == "cpcv_median_path") & (frame["status"] == "filled")] if len(frame) else frame


def evaluate(registry, h: dict, pricing_passed: bool) -> dict:
    run = set(registry.trials_run())
    accepted: dict[str, bool] = {}
    final, reasons, previous = None, [], None
    for trial in ORDER:
        if trial not in run:
            continue
        metrics = _metrics(registry, trial)
        ok = bool(metrics.get("passed"))
        if not ok:
            failed = [k for k, v in metrics.get("gates", {}).items() if not v]
            reasons.append(f"{trial} failed: {', '.join(failed) or 'no gates recorded'}")
        if ok and trial in ADDONS and previous is not None:
            new, old = _trades(registry, trial), _trades(registry, previous)
            days = sorted(set(new["day"]) | set(old["day"]))
            gate = addon_gate(new, old, days, param(h, "gate.years"))
            ok = gate["passed"]
            if not ok:
                reasons.append(f"{trial} passed alone but did not beat {previous} on identical setups")
        accepted[trial] = ok
        if ok:
            final, previous = trial, trial
    if final is None:
        return {"status": "alert-off", "config": None, "accepted": accepted,
                "reasons": reasons or ["no trial has been run"]}
    if not pricing_passed:
        return {"status": "alert-off", "config": final, "accepted": accepted,
                "reasons": reasons + ["the recorded-chain pricing check has not passed (R17)"]}
    shadow = sorted(t for t in AFTER_LOOK if accepted.get(t))
    return {"status": "alert-on", "config": final, "accepted": accepted, "reasons": reasons,
            "shadow_until_holdout": shadow}


def write_verdict(result: dict, path: Path) -> Path:
    lines = [f"# SP2 verdict: **{result['status']}**", "",
             f"- Configuration: {result.get('config') or 'none'}",
             f"- Accepted trials: {', '.join(t for t, ok in result['accepted'].items() if ok) or 'none'}"]
    if result.get("shadow_until_holdout"):
        lines.append(f"- In shadow until the clean forward holdout (R33): {', '.join(result['shadow_until_holdout'])}")
    lines += ["", "## Reasons", ""] + [f"- {r}" for r in result["reasons"]]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
