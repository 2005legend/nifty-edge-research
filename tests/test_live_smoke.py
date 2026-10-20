"""Live checks against Angel One. Run only with real credentials in .env:

    .venv/Scripts/python -m pytest -m live -v

Skipped by default (pyproject addopts "-m 'not live'").
"""

import threading
import time
from datetime import date, datetime, timedelta

import pytest

import quantdesk.config as config
from quantdesk.app import build_app
from quantdesk.clock import IST

pytestmark = pytest.mark.live


@pytest.fixture(scope="module")
def app():
    from dotenv import load_dotenv  # conftest disables the automatic .env load; live tests need it

    load_dotenv(config.project_root() / ".env", override=False)
    application = build_app()
    application.client().login()
    return application


def last_trading_day(app) -> date:
    day = datetime.now(IST).date() - timedelta(days=1)
    while not app.is_trading_day(day):
        day -= timedelta(days=1)
    return day


def test_live_login(app):
    assert app.client().profile().get("name")


def test_live_master_index_tokens(app):
    master = app.master(datetime.now(IST).date())
    for spec in app.settings["angel"]["index_tokens"].values():
        assert (master["token"] == spec["token"]).any()
    nifty = master[(master["name"] == "NIFTY") & (master["instrumenttype"] == "OPTIDX")]
    sensex = master[(master["name"] == "SENSEX") & (master["instrumenttype"] == "OPTIDX")]
    assert set(nifty["lotsize"]) == {65}
    assert set(sensex["lotsize"]) == {20}
    assert (nifty["strike"] % 50 == 0).all()


def test_live_index_ltp_used_at_recorder_start(app):
    """The recorder plans each chain from this exact call; a wrong symbol loses that index's options for the day."""
    plausible = {"NIFTY": (10_000, 60_000), "SENSEX": (30_000, 200_000), "INDIAVIX": (5, 100)}
    for name, spec in app.settings["angel"]["index_tokens"].items():
        price = app.client().ltp(spec["exchange"], spec["symbol"], spec["token"])
        low, high = plausible[name]
        assert low < price < high, f"{name}: {price}"


def test_live_candles_one_day(app):
    day = last_trading_day(app)
    start = datetime(day.year, day.month, day.day, 9, 15, tzinfo=IST)
    frame = app.client().candles("NSE", "99926000", "ONE_MINUTE", start, start + timedelta(hours=6, minutes=15))
    assert len(frame) == 375


def test_live_ws_tick_scale(app):
    """One SnapQuote tick for the current Nifty future must be within 2% of the REST last price."""
    day = datetime.now(IST).date()
    if not app.is_trading_day(day) or not (9 * 60 + 15 <= datetime.now(IST).hour * 60 + datetime.now(IST).minute < 15 * 60 + 30):
        pytest.skip("market closed: websocket check needs a live session")
    from quantdesk.instruments import current_future

    future = current_future(app.master(day), "NIFTY", day)
    rest_ltp = app.client().ltp("NFO", future["symbol"], future["token"])
    got = []
    stream = app.stream_factory(on_tick=got.append, on_stale=lambda *a: None)
    stream.subscribe({2: [future["token"]]})
    stream.start()
    deadline = time.time() + 20
    while not got and time.time() < deadline:
        time.sleep(0.5)
    stream.close()
    assert got, "no tick received in 20 s"
    assert abs(got[0].ltp / rest_ltp - 1) < 0.02
