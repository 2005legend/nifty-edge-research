"""Point-in-time Nifty 50 membership from config/nifty50_membership.yaml (R7)."""

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml

from quantdesk.config import project_root


@dataclass(frozen=True)
class Membership:
    start: date
    start_members: frozenset
    changes: tuple          # (effective date, added, removed), in date order
    aliases: dict
    no_data: frozenset

    def members_on(self, day: date) -> set[str]:
        """Members at the start of `day`, as symbols listed at the time."""
        members = set(self.start_members)
        for effective, added, removed in self.changes:
            if effective > day:
                break
            members = (members - removed) | added
        return members

    def listing(self, symbol: str) -> str:
        """Today's NSE symbol for a member listed at the time under `symbol` (same listing and token)."""
        return self.aliases.get(symbol, symbol)

    def backfill_symbols(self) -> list[str]:
        """Today's symbols of every member since `start` that still has data."""
        ever = set(self.start_members).union(*(added for _, added, _ in self.changes))
        return sorted(self.listing(s) for s in ever - self.no_data)


def load_membership(path: Path | None = None) -> Membership:
    raw = yaml.safe_load((path or project_root() / "config" / "nifty50_membership.yaml").read_text(encoding="utf-8"))
    changes = sorted((date.fromisoformat(c["effective"]), frozenset(c["add"]), frozenset(c["remove"]))
                     for c in raw["changes"])
    return Membership(date.fromisoformat(raw["start"]), frozenset(raw["start_members"]), tuple(changes),
                      dict(raw.get("aliases") or {}), frozenset(raw.get("no_data") or []))
