from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from quantdesk.storage import RawExistsError, Store

DAY = date(2026, 10, 20)


def test_write_raw_refuses_overwrite(tmp_path):
    store = Store(tmp_path)
    path = store.write_raw("nse_fo", DAY, "bhav.zip", b"abc")
    assert path.read_bytes() == b"abc"
    assert store.raw_exists("nse_fo", DAY, "bhav.zip")
    with pytest.raises(RawExistsError):
        store.write_raw("nse_fo", DAY, "bhav.zip", b"abc")


def test_append_parquet_twice_reads_both(tmp_path):
    store = Store(tmp_path)
    store.append_parquet("bars", DAY, pd.DataFrame({"x": [1, 2]}))
    store.append_parquet("bars", DAY, pd.DataFrame({"x": [3, 4, 5]}))
    assert len(store.read("bars", DAY)) == 5


def test_read_returns_empty_frame_when_kind_missing(tmp_path):
    frame = Store(tmp_path).read("nothing")
    assert isinstance(frame, pd.DataFrame)
    assert frame.empty


def test_connect_exposes_view_per_kind(tmp_path):
    store = Store(tmp_path)
    store.append_parquet("bars", DAY, pd.DataFrame({"x": [1, 2]}))
    store.append_parquet("news", DAY, pd.DataFrame({"title": ["a"]}))
    con = store.connect()
    assert con.sql("select count(*) from bars").fetchone()[0] == 2
    assert con.sql("select count(*) from news").fetchone()[0] == 1


def test_report_round_trip(tmp_path):
    store = Store(tmp_path)
    store.write_report("eod", DAY, {"a": 1})
    assert store.read_report("eod", DAY) == {"a": 1}
    assert store.read_report("eod", date(2026, 1, 1)) is None


def test_failed_parquet_write_leaves_no_partial_part(tmp_path, monkeypatch):
    store = Store(tmp_path)

    def broken(self, path, *args, **kwargs):
        Path(path).write_bytes(b"PAR1 truncated")
        raise OSError("killed mid-write")

    monkeypatch.setattr(pd.DataFrame, "to_parquet", broken)
    with pytest.raises(OSError):
        store.append_parquet("bars", DAY, pd.DataFrame({"x": [1]}))
    monkeypatch.undo()
    assert not list((tmp_path / "raw" / "bars").rglob("*.parquet"))
    store.append_parquet("bars", DAY, pd.DataFrame({"x": [1]}))
    assert len(store.read("bars", DAY)) == 1


def test_read_keeps_the_datas_own_date_column(tmp_path):
    """Live 21 Oct 2026: macro rows for 15-19 Oct all read back dated 21 Oct, because the folder name
    date=2026-10-21 overrode the data's own 'date' column."""
    store = Store(tmp_path)
    frame = pd.DataFrame({"series_id": ["x", "x"], "date": [date(2026, 10, 15), date(2026, 10, 16)],
                          "value": [1.0, 2.0]})
    store.append_parquet("macro_daily", date(2026, 10, 21), frame)
    out = store.read("macro_daily")
    assert sorted(pd.to_datetime(out["date"]).dt.date) == [date(2026, 10, 15), date(2026, 10, 16)]
    assert set(pd.to_datetime(out["stored_on"]).dt.date) == {date(2026, 10, 21)}
    view = store.connect().sql("select date, stored_on from macro_daily order by date").df()
    assert list(pd.to_datetime(view["date"]).dt.date) == [date(2026, 10, 15), date(2026, 10, 16)]


def test_kinds_without_a_date_column_still_get_the_folder_date(tmp_path):
    store = Store(tmp_path)
    store.append_parquet("bars", date(2026, 10, 21), pd.DataFrame({"token": ["1"], "close": [1.0]}))
    out = store.read("bars")
    assert list(pd.to_datetime(out["date"]).dt.date) == [date(2026, 10, 21)]
    assert "stored_on" not in out.columns
