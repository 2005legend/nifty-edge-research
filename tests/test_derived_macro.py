from datetime import date, datetime, time

import pandas as pd
import pytest
import yaml

from quantdesk.clock import IST
from quantdesk.config import project_root
from quantdesk.derived.macro import MACRO_LAGS, available_at, build_macro
from quantdesk.derived.store import DerivedStore
from quantdesk.storage import Store


def test_lags_follow_design_section_4():
    assert available_at("dgs10", date(2026, 10, 16)) == datetime(2026, 10, 18, 9, 0, tzinfo=IST)
    assert available_at("spx", date(2026, 10, 16)) == datetime(2026, 10, 17, 9, 0, tzinfo=IST)
    assert available_at("n225", date(2026, 10, 16)) == datetime(2026, 10, 17, 9, 0, tzinfo=IST)
    assert available_at("indiavix_yf", date(2026, 10, 16)) == datetime(2026, 10, 16, 16, 0, tzinfo=IST)
    assert available_at("india_cpi_oecd", date(2026, 8, 1)) == datetime(2026, 9, 30, 9, 0, tzinfo=IST)
    # The NSE index file is published the same evening (design §4); the stress score reads the G-sec price.
    assert available_at("india_gsec10y_price", date(2026, 10, 16)) == datetime(2026, 10, 16, 20, 0, tzinfo=IST)
    with pytest.raises(KeyError):
        available_at("no_such_series", date(2026, 10, 16))


def test_every_series_the_collector_stores_is_classified():
    """A new series must be given a lag before it can enter the table, not default to something guessed."""
    settings = yaml.safe_load((project_root() / "config" / "settings.yaml").read_text(encoding="utf-8"))
    stored = {s["id"] for s in settings["macro"]["series"]} - {"econ_calendar"}
    assert sorted(stored - set(MACRO_LAGS)) == []
    assert all(isinstance(lag[1], time) for lag in MACRO_LAGS.values())


def test_a_refetched_value_replaces_the_older_one(tmp_path):
    raw = Store(tmp_path / "raw")
    raw.append_parquet("macro_daily", date(2026, 10, 17), pd.DataFrame(
        {"series_id": ["brent"], "date": [date(2026, 10, 16)], "value": [90.0]}))
    raw.append_parquet("macro_daily", date(2026, 10, 18), pd.DataFrame(
        {"series_id": ["brent"], "date": [date(2026, 10, 16)], "value": [91.0]}))
    derived = DerivedStore(tmp_path / "d")
    build_macro(raw, derived)
    rows = derived.read("macro")
    assert rows["value"].tolist() == [91.0]
    assert rows["available_at"].tolist() == [pd.Timestamp(datetime(2026, 10, 17, 9, 0, tzinfo=IST))]


def test_a_second_fetch_on_the_same_day_also_wins(tmp_path):
    """The collector runs at 07:30 and 18:30, so both store under one folder date; the later file wins."""
    raw = Store(tmp_path / "raw")
    day = date(2026, 10, 16)
    for value in (90.0, 92.5):
        raw.append_parquet("macro_daily", day, pd.DataFrame(
            {"series_id": ["brent"], "date": [day], "value": [value]}))
    derived = DerivedStore(tmp_path / "d")
    build_macro(raw, derived)
    rows = derived.read("macro")
    assert rows["value"].tolist() == [92.5] and rows["date"].tolist() == [day]
