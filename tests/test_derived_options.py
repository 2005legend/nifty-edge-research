from datetime import date, datetime
from pathlib import Path

import pandas as pd

from quantdesk.clock import IST
from quantdesk.config import load_settings
from quantdesk.derived.options import (
    _frame_from_contracts,
    build_expiries,
    build_fii_ratio,
    build_options_eod,
)
from quantdesk.derived.store import DerivedStore
from quantdesk.storage import Store

FIXTURES = Path(__file__).parent / "fixtures"
DAY = date(2026, 10, 19)
NEXT = date(2026, 10, 20)
URLS = load_settings()["urls"]
MORNING = datetime(2026, 10, 20, 9, 0, tzinfo=IST)
PARTICIPANT_OI = ("Participant wise Open Interest\r\n"
                  "Client Type,Future Index Long,Future Index Short\r\n"
                  "FII,60,40\r\n")


def sessions(derived: DerivedStore, days: list[date]) -> None:
    derived.write_frame("sessions", pd.DataFrame({"day": days, "kind": "regular", "bars": 375,
                                                  "first_bar": None, "last_bar": None}))


def chains(tmp_path, days: list[date], files: list[date] | None = None) -> tuple[Store, DerivedStore]:
    """A session calendar for `days`, with one NSE and one BSE bhavcopy stored for each day in `files`."""
    store, derived = Store(tmp_path), DerivedStore(tmp_path / "derived")
    sessions(derived, days)
    for day in days if files is None else files:
        store.write_raw("nse_fo", day, f"BhavCopy_NSE_FO_{day:%Y%m%d}.csv.zip",
                        (FIXTURES / "nse_fo_udiff_sample.zip").read_bytes())
        store.write_raw("bse_fo", day, f"BhavCopy_BSE_FO_{day:%Y%m%d}.csv",
                        (FIXTURES / "bse_fo_udiff_sample.csv").read_bytes())
    return store, derived


def build(store, derived, **kwargs):
    defaults = {"nifty_from": date(2019, 2, 11), "sensex_from": date(2024, 1, 1)}
    return build_options_eod(store, derived, URLS, **(defaults | kwargs))


def test_options_eod_takes_nifty_from_nse_and_sensex_from_bse(tmp_path):
    store, derived = chains(tmp_path, [DAY, NEXT], files=[DAY])
    build(store, derived)
    rows = derived.read("options_eod")
    assert rows.groupby("symbol").size().to_dict() == {"NIFTY": 3, "SENSEX": 2}
    assert set(rows["day"]) == {DAY}
    assert set(rows["available_at"]) == {MORNING}          # next session at 09:00, not the same evening
    assert rows["traded"].all() and set(rows["lot"]) == {65}


def test_a_symbol_starts_only_on_its_first_day(tmp_path):
    store, derived = chains(tmp_path, [DAY])
    build(store, derived, sensex_from=date(2027, 1, 1))      # R11: SENSEX is traded from 2024
    assert set(derived.read("options_eod")["symbol"]) == {"NIFTY"}


def test_untraded_rows_are_flagged():
    rows = _frame_from_contracts(pd.DataFrame({"volume": [0, 5], "close": [12.0, 13.0]}))
    assert rows["traded"].tolist() == [False, True]


def test_expiries_come_from_the_previous_file_and_skip_a_missing_day(tmp_path):
    derived = DerivedStore(tmp_path)
    days = [date(2021, 3, 26), date(2021, 3, 30), date(2021, 3, 31)]       # no file for 30 March
    sessions(derived, days)
    eod = pd.DataFrame({
        "day": [date(2021, 3, 26)] * 2 + [date(2021, 3, 31)] * 2,
        "symbol": "NIFTY", "instrument": "IDO", "option_type": "CE", "strike": 14500.0,
        "expiry": [date(2021, 4, 1), date(2021, 4, 8), date(2021, 4, 1), date(2021, 4, 8)],
        "lot": 75, "volume": 10, "traded": True})
    derived.write_frame("options_eod", eod)
    build_expiries(derived)
    e = derived.read("expiries").set_index("day")
    assert e.loc[date(2021, 3, 30), "expiry_1"] == date(2021, 4, 1)    # from the 26 March file
    assert e.loc[date(2021, 3, 31), "expiry_2"] == date(2021, 4, 8)
    assert not e.loc[date(2021, 3, 31), "is_expiry_day"]


def test_the_expiry_day_flag_and_the_lot_come_from_the_chain(tmp_path):
    store, derived = chains(tmp_path, [DAY, NEXT], files=[DAY])
    build(store, derived)
    build_expiries(derived)
    e = derived.read("expiries").set_index(["day", "symbol"])
    assert e.loc[(NEXT, "NIFTY"), "expiry_1"] == NEXT              # the weekly expires that day
    assert e.loc[(NEXT, "NIFTY"), "lot_1"] == 65
    assert bool(e.loc[(NEXT, "NIFTY"), "is_expiry_day"])
    assert not bool(e.loc[(NEXT, "SENSEX"), "is_expiry_day"])


def test_fii_ratio_is_available_the_next_morning(tmp_path):
    store, derived = chains(tmp_path, [DAY, NEXT], files=[])
    store.write_raw("participant_oi", DAY, f"fao_participant_oi_{DAY:%d%m%Y}.csv",
                    PARTICIPANT_OI.encode())
    build_fii_ratio(store, derived)
    rows = derived.read("fii_ratio")
    assert rows["day"].tolist() == [DAY] and rows["ratio"].tolist() == [0.6]
    assert rows["available_at"].tolist() == [MORNING]
