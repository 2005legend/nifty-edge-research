"""The trial registry (spec §6.3, R32-R34): the only door to P&L on historical data.

A trial runs once, under its pre-registered id, with a ticket that records:
- the commit
- the hash of research/hypotheses.yaml
- the data hash

Every run is one row of research/experiments.csv, and its trades, daily R and models are saved under
research/trials/<id>/. The cumulative trial count is what the deflated Sharpe ratio and PBO are computed with,
together with the 46 earlier looks.

The registry refuses when:
- the cap of 13 is reached
- the id is unknown or has already run
- the pre-registration is unfrozen, or differs from the copy frozen at prereg-v1
- the git tree is dirty
- a prerequisite is unmet: pilots, pricing check, or the trial's run condition
"""

import csv
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd
import subprocess
import yaml

from quantdesk.clock import IST
from quantdesk.validation.hypotheses import TRIAL_CAP

FIELDS = ["trial_id", "run_at", "commit", "hypotheses_hash", "data_hash", "config", "cumulative_trials", "n_trades",
          "mean_net_r", "t_stat", "dsr", "pbo", "verdict", "notes"]


class RegistryRefusal(RuntimeError):
    pass


@dataclass(frozen=True)
class TrialTicket:
    trial_id: str
    slot: int
    issued_at: str
    commit: str
    hypotheses_hash: str
    data_hash: str
    cumulative_trials: int


def _default_git(repo: Path):
    def run(args: list[str]) -> str:
        return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=False).stdout.strip()
    return run


class Registry:
    def __init__(self, research_dir: Path, repo_dir: Path, git=None):
        self.dir = Path(research_dir)
        self.git = git or _default_git(Path(repo_dir))

    @property
    def _yaml(self) -> Path:
        return self.dir / "hypotheses.yaml"

    def hypotheses_hash(self) -> str:
        text = self._yaml.read_bytes().replace(b"\r\n", b"\n")
        return hashlib.sha256(text).hexdigest()[:16]

    def _hypotheses(self) -> dict:
        return yaml.safe_load(self._yaml.read_text(encoding="utf-8"))

    def freeze(self) -> dict:
        """Record the frozen pre-registration's hash (the prereg-v1 moment). The YAML must say frozen: true."""
        if self._hypotheses().get("frozen") is not True:
            raise RegistryRefusal("research/hypotheses.yaml is not frozen: set `frozen: true` before tagging prereg-v1")
        record = {"hypotheses_hash": self.hypotheses_hash(), "commit": self.git(["rev-parse", "HEAD"]),
                  "frozen_at": datetime.now(IST).isoformat(timespec="seconds"), "tag": "prereg-v1"}
        (self.dir / "prereg.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
        return record

    def _rows(self) -> list[dict]:
        path = self.dir / "experiments.csv"
        if not path.exists():
            return []
        with open(path, encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))

    def trials_run(self) -> list[str]:
        return [row["trial_id"] for row in self._rows()]

    def issue_ticket(self, trial_id: str, data_hash: str, prerequisites: dict[str, bool]) -> TrialTicket:
        h = self._hypotheses()
        entries = {e["id"]: e for e in h.get("registry", [])}
        if trial_id not in entries:
            raise RegistryRefusal(f"{trial_id} is not in the pre-registered registry")
        done = self.trials_run()
        if trial_id in done:
            raise RegistryRefusal(f"{trial_id} has already run; a re-run needs a reserve slot")
        if len(done) >= TRIAL_CAP:
            raise RegistryRefusal(f"the cap of {TRIAL_CAP} trials is reached")
        if h.get("frozen") is not True:
            raise RegistryRefusal("research/hypotheses.yaml is not frozen")
        prereg = self.dir / "prereg.json"
        if not prereg.exists():
            raise RegistryRefusal("no prereg.json: freeze the pre-registration (prereg-v1) first")
        if json.loads(prereg.read_text(encoding="utf-8"))["hypotheses_hash"] != self.hypotheses_hash():
            raise RegistryRefusal("research/hypotheses.yaml changed after prereg-v1")
        if self.git(["status", "--porcelain"]):
            raise RegistryRefusal("the git tree is dirty: commit first, so the ticket names the code that ran")
        unmet = [name for name, ok in prerequisites.items() if not ok]
        if unmet:
            raise RegistryRefusal(f"prerequisites not met: {', '.join(unmet)}")
        return TrialTicket(trial_id, int(entries[trial_id]["slot"]), datetime.now(IST).isoformat(timespec="seconds"),
                           self.git(["rev-parse", "HEAD"]), self.hypotheses_hash(), data_hash, len(done) + 1)

    def record(self, ticket: TrialTicket, metrics: dict, trades: pd.DataFrame, daily_r: pd.DataFrame,
               models: dict) -> Path:
        folder = self.dir / "trials" / ticket.trial_id
        folder.mkdir(parents=True, exist_ok=True)
        trades.to_parquet(folder / "trades.parquet")
        daily_r.to_parquet(folder / "daily_r.parquet")
        (folder / "metrics.json").write_text(json.dumps({"ticket": asdict(ticket), **metrics}, indent=2, default=str),
                                             encoding="utf-8")
        (folder / "models.json").write_text(json.dumps(models, indent=2, default=str), encoding="utf-8")
        row = {"trial_id": ticket.trial_id, "run_at": datetime.now(IST).isoformat(timespec="seconds"),
               "commit": ticket.commit, "hypotheses_hash": ticket.hypotheses_hash, "data_hash": ticket.data_hash,
               "config": metrics.get("config", ""), "cumulative_trials": ticket.cumulative_trials,
               **{k: metrics.get(k, "") for k in ("n_trades", "mean_net_r", "t_stat", "dsr", "pbo", "verdict", "notes")}}
        path = self.dir / "experiments.csv"
        with open(path, "a", encoding="utf-8", newline="") as f:
            csv.DictWriter(f, fieldnames=FIELDS).writerow(row)
        return folder
