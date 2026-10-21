from datetime import date, datetime, timedelta

import pandas as pd
import pytest

from quantdesk.clock import IST
from quantdesk.derived.asof import AsOf, LookAheadError
from quantdesk.derived.store import DerivedStore

T0 = datetime(2024, 3, 4, 10, 0, tzinfo=IST)


def test_rows_from_the_future_are_never_returned(tmp_path):
    derived = DerivedStore(tmp_path)
    derived.write_frame("x", pd.DataFrame({"v": [1, 2], "available_at": [T0, T0 + timedelta(minutes=1)]}))
    assert AsOf(derived, T0).read("x")["v"].tolist() == [1]


def test_require_raises_on_a_future_row(tmp_path):
    frame = pd.DataFrame({"available_at": [T0 + timedelta(seconds=1)]})
    with pytest.raises(LookAheadError):
        AsOf(DerivedStore(tmp_path), T0).require(frame)


def test_require_returns_a_frame_that_is_already_known(tmp_path):
    frame = pd.DataFrame({"v": [1], "available_at": [T0]})
    assert AsOf(DerivedStore(tmp_path), T0).require(frame) is frame


def test_a_caller_clause_cannot_leak_future_rows_through_an_or(tmp_path):
    derived = DerivedStore(tmp_path)
    derived.write_frame("x", pd.DataFrame({
        "day": [date(2024, 3, 1), date(2024, 3, 2)], "v": [1, 2],
        "available_at": [T0, T0 + timedelta(minutes=1)]}))
    rows = AsOf(derived, T0).read("x", where="day = '2024-03-01' or day = '2024-03-02'")
    assert rows["v"].tolist() == [1]


def test_a_naive_reading_time_is_refused(tmp_path):
    with pytest.raises(ValueError):
        AsOf(DerivedStore(tmp_path), datetime(2024, 3, 4, 10, 0))
