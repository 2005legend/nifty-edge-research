import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from quantdesk.validation.registry import Registry, RegistryRefusal

REAL = Path(__file__).resolve().parents[1] / "research" / "hypotheses.yaml"
HEADER = "trial_id,run_at,commit,hypotheses_hash,data_hash,config,cumulative_trials,n_trades,mean_net_r,t_stat,dsr,pbo,verdict,notes\n"
OK = {"pilots": True, "pricing_check": True, "run_if": True}


class Git:
    def __init__(self, dirty=""):
        self.dirty = dirty

    def __call__(self, args):
        return self.dirty if args[0] == "status" else "abc1234"


def research(tmp_path, frozen=True):
    d = tmp_path / "research"
    d.mkdir(parents=True)
    h = yaml.safe_load(REAL.read_text(encoding="utf-8"))
    h["frozen"] = frozen
    (d / "hypotheses.yaml").write_text(yaml.safe_dump(h, sort_keys=False), encoding="utf-8")
    (d / "experiments.csv").write_text(HEADER, encoding="utf-8")
    return d


def frozen_registry(tmp_path, git=None):
    reg = Registry(research(tmp_path), tmp_path, git=git or Git())
    reg.freeze()
    return reg


def test_a_frozen_registry_issues_a_ticket_and_records_one_row(tmp_path):
    reg = frozen_registry(tmp_path)
    ticket = reg.issue_ticket("B0", data_hash="d1", prerequisites=OK)
    assert ticket.trial_id == "B0" and ticket.cumulative_trials == 1 and ticket.commit == "abc1234"
    trades = pd.DataFrame({"r": [0.5, -1.0]})
    reg.record(ticket, {"n_trades": 2, "mean_net_r": -0.25}, trades, pd.DataFrame({"r": [0.0]}), {})
    assert reg.trials_run() == ["B0"]
    assert (tmp_path / "research" / "trials" / "B0" / "metrics.json").exists()


def test_a_trial_runs_once(tmp_path):
    reg = frozen_registry(tmp_path)
    reg.record(reg.issue_ticket("B0", "d1", OK), {}, pd.DataFrame(), pd.DataFrame(), {})
    with pytest.raises(RegistryRefusal, match="already"):
        reg.issue_ticket("B0", "d1", OK)


def test_unknown_ids_and_unmet_prerequisites_are_refused(tmp_path):
    reg = frozen_registry(tmp_path)
    with pytest.raises(RegistryRefusal, match="not in"):
        reg.issue_ticket("Z9", "d1", OK)
    with pytest.raises(RegistryRefusal, match="pricing_check"):
        reg.issue_ticket("B0", "d1", {**OK, "pricing_check": False})


def test_an_unfrozen_or_edited_preregistration_is_refused(tmp_path):
    reg = Registry(research(tmp_path, frozen=False), tmp_path, git=Git())
    with pytest.raises(RegistryRefusal, match="frozen"):
        reg.freeze()
    reg2 = frozen_registry(tmp_path / "b")
    path = tmp_path / "b" / "research" / "hypotheses.yaml"
    path.write_text(path.read_text(encoding="utf-8") + "\n# edited\n", encoding="utf-8")
    with pytest.raises(RegistryRefusal, match="changed"):
        reg2.issue_ticket("B0", "d1", OK)


def test_a_dirty_tree_is_refused(tmp_path):
    reg = frozen_registry(tmp_path, git=Git(dirty=" M quantdesk/x.py"))
    with pytest.raises(RegistryRefusal, match="dirty"):
        reg.issue_ticket("B0", "d1", OK)


def test_the_cap_of_13_is_enforced(tmp_path):
    reg = frozen_registry(tmp_path)
    rows = "".join(f"T{i},x,c,h,d,cfg,{i + 1},0,0,0,0,0,,\n" for i in range(13))
    (tmp_path / "research" / "experiments.csv").write_text(HEADER + rows, encoding="utf-8")
    with pytest.raises(RegistryRefusal, match="cap"):
        reg.issue_ticket("B0", "d1", OK)
