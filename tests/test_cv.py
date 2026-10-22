from datetime import date

import pandas as pd

from quantdesk.validation.cv import cpcv_splits, half_year_groups, paths, walk_forward

DAYS = list(pd.bdate_range("2019-02-11", "2023-12-29").date)


def test_ten_half_year_groups_and_45_splits():
    groups = half_year_groups(DAYS)
    assert len(groups) == 10 and groups[0][0] == date(2019, 2, 11) and groups[-1][-1] == date(2023, 12, 29)
    splits = cpcv_splits(groups, k=2, embargo=20)
    assert len(splits) == 45


def test_the_embargo_removes_20_sessions_on_both_sides_of_each_test_group():
    groups = half_year_groups(DAYS)
    split = [s for s in cpcv_splits(groups, k=2, embargo=20) if s.test_groups == (2, 7)][0]
    order = {d: i for i, d in enumerate(DAYS)}
    train = set(split.train)
    for g in (2, 7):
        first, last = order[groups[g][0]], order[groups[g][-1]]
        assert not any(DAYS[i] in train for i in range(first - 20, first))
        assert not any(DAYS[i] in train for i in range(last + 1, min(last + 21, len(DAYS))))
        assert DAYS[first - 21] in train
    assert not set(split.test) & train


def test_nine_paths_each_testing_every_group_once():
    groups = half_year_groups(DAYS)
    splits = cpcv_splits(groups, k=2, embargo=20)
    ps = paths(splits, len(groups))
    assert len(ps) == 9
    for path in ps:
        assert sorted(g for g, _ in path) == list(range(10))
        assert all(g in splits[s].test_groups for g, s in path)


def test_walk_forward_trains_before_and_tests_after():
    days = list(pd.bdate_range("2019-02-11", "2025-12-31").date)
    split = walk_forward(days, train_end=date(2023, 12, 31), test_start=date(2024, 1, 1), test_end=date(2025, 12, 31),
                         embargo=20)
    assert max(split.train) < min(split.test) and min(split.test) >= date(2024, 1, 1)
    gap = len([d for d in days if max(split.train) < d < min(split.test)])
    assert gap == 20
