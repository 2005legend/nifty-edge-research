"""Combinatorial purged cross-validation and the walk-forward split (spec §6.3, design §14, R34).

- Groups are half-years of 2019-2023 (10 groups).
- Every pair of groups is tested once (45 splits).
- The other groups train, minus 20 sessions on each side of each test group: the features look back 14-20
  sessions, so a shorter embargo would let training and test overlap.
- Each group is tested in 9 splits, which make 9 backtest paths.
"""

from dataclasses import dataclass
from datetime import date
from itertools import combinations


@dataclass(frozen=True)
class Split:
    test_groups: tuple
    train: list
    test: list


def half_year_groups(days: list[date]) -> list[list[date]]:
    groups: dict = {}
    for d in sorted(days):
        groups.setdefault((d.year, 1 if d.month <= 6 else 2), []).append(d)
    return [groups[k] for k in sorted(groups)]


def cpcv_splits(groups: list[list[date]], k: int = 2, embargo: int = 20) -> list[Split]:
    days = [d for g in groups for d in g]
    order = {d: i for i, d in enumerate(days)}
    out = []
    for test_groups in combinations(range(len(groups)), k):
        banned = set()
        for g in test_groups:
            first, last = order[groups[g][0]], order[groups[g][-1]]
            banned.update(range(max(0, first - embargo), min(len(days), last + embargo + 1)))
        test = [d for g in test_groups for d in groups[g]]
        train = [d for i, d in enumerate(days) if i not in banned]
        if train:
            out.append(Split(tuple(test_groups), train, test))
    return out


def paths(splits: list[Split], n_groups: int) -> list[list[tuple[int, int]]]:
    """Path j takes, for each group, the j-th split (in split order) that tests it."""
    by_group = {g: [i for i, s in enumerate(splits) if g in s.test_groups] for g in range(n_groups)}
    n_paths = min(len(v) for v in by_group.values())
    return [[(g, by_group[g][j]) for g in range(n_groups)] for j in range(n_paths)]


def walk_forward(days: list[date], train_end: date, test_start: date, test_end: date, embargo: int) -> Split:
    before = [d for d in sorted(days) if d <= train_end]
    test = [d for d in sorted(days) if test_start <= d <= test_end]
    return Split(("WF",), before[:-embargo] if embargo else before, test)
