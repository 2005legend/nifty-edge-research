from datetime import date
from pathlib import Path

import pytest

from quantdesk.instruments import (
    atm_strike,
    chain_tokens,
    current_future,
    download_master,
    equity_tokens,
    load_master,
    nifty50_symbols,
    option_expiries,
)
from quantdesk.storage import Store

FIXTURE = Path(__file__).parent / "fixtures" / "master_small.json"


@pytest.fixture(scope="module")
def master():
    return load_master(FIXTURE)


def test_load_master_scales_strike_and_tick(master):
    row = master[master["symbol"] == "NIFTY20OCT2622550CE"].iloc[0]
    assert row["strike"] == 22550.0
    assert row["tick_size"] == 0.05
    assert row["lotsize"] == 65
    assert row["expiry"] == date(2026, 10, 20)


def test_option_expiries_nearest_two(master):
    assert option_expiries(master, "NIFTY", date(2026, 10, 19)) == [date(2026, 10, 20), date(2026, 10, 27)]
    assert option_expiries(master, "SENSEX", date(2026, 10, 19)) == [date(2026, 10, 22), date(2026, 10, 29)]


def test_holiday_shifted_expiry_taken_from_master(master):
    assert option_expiries(master, "NIFTY", date(2026, 11, 20))[0] == date(2026, 11, 23)


def test_chain_tokens_width_uses_listed_strikes(master):
    chain = chain_tokens(master, "NIFTY", date(2026, 10, 20), atm=22550, width=2)
    assert list(chain["strike"]) == [22450, 22500, 22550, 22600, 22650]
    assert chain["ce_token"].notna().all() and chain["pe_token"].notna().all()
    assert set(chain["lotsize"]) == {65}


def test_atm_strike_nearest():
    strikes = [22500, 22550, 22600]
    assert atm_strike(22574, strikes) == 22550
    assert atm_strike(22576, strikes) == 22600


def test_current_future_nearest_unexpired(master):
    assert current_future(master, "NIFTY", date(2026, 10, 19))["symbol"] == "NIFTY27OCT26FUT"
    assert current_future(master, "SENSEX", date(2026, 10, 19))["exch_seg"] == "BFO"


def test_equity_tokens_and_nifty50_symbols(master):
    csv_bytes = b"Company Name,Industry,Symbol,Series,ISIN Code\nReliance,Oil,RELIANCE,EQ,X\nInfosys,IT,INFY,EQ,Y\n"
    symbols = nifty50_symbols(csv_bytes)
    assert symbols == ["RELIANCE", "INFY"]
    assert equity_tokens(master, symbols) == {"RELIANCE": "2885", "INFY": "1594"}


def test_download_master_falls_back_to_previous_cache(tmp_path):
    store = Store(tmp_path)
    store.write_raw("instruments", date(2026, 10, 19), "master.json", FIXTURE.read_bytes())

    def failing_get(url):
        raise ConnectionError("down")

    path, is_fallback = download_master(store, failing_get, date(2026, 10, 20), url="https://example/master.json")
    assert is_fallback is True
    assert path.parent.name == "2026-10-19"


def test_download_master_saves_today(tmp_path):
    store = Store(tmp_path)

    class Response:
        status_code = 200
        content = FIXTURE.read_bytes()

    path, is_fallback = download_master(store, lambda url: Response(), date(2026, 10, 20), url="https://example/m.json")
    assert is_fallback is False
    assert store.raw_exists("instruments", date(2026, 10, 20), "master.json")
