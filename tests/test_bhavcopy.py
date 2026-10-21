from datetime import date, datetime
from pathlib import Path

import pytest

from quantdesk.clock import IST
from quantdesk.config import load_settings
from quantdesk.eod.bhavcopy import (
    NotPublishedError,
    backfill_bhavcopy,
    fetch_nse_fo_bhavcopy,
    parse_fo_bhavcopy,
)
from quantdesk.net.http import BadDownloadError, PoliteSession
from quantdesk.storage import Store
from tests.fakes import FakeClock, FakeHttp, FakeSleep

FIX = Path(__file__).parent / "fixtures"
DAY = date(2026, 10, 19)
URLS = load_settings()["urls"]


def nse_url(day):
    return URLS["nse_fo_bhavcopy"].format(yyyymmdd=day.strftime("%Y%m%d"))


def session_with(routes):
    clock = FakeClock(datetime(2026, 10, 19, 19, 0, tzinfo=IST))
    sleep = FakeSleep(clock)
    http = FakeHttp(routes, clock=clock)
    return PoliteSession(min_interval_s=0.0, clock=clock, sleep=sleep, http=http), http, sleep


def test_parse_nse_udiff_columns_and_types():
    frame = parse_fo_bhavcopy(FIX / "nse_fo_udiff_sample.zip")
    assert len(frame) == 4
    ce = frame[(frame["symbol"] == "NIFTY") & (frame["instrument"] == "IDO") & (frame["option_type"] == "CE")].iloc[0]
    assert ce["strike"] == 22550.0
    assert ce["expiry"] == date(2026, 10, 20)
    assert ce["oi"] == 150000
    assert ce["settle"] == 120.5
    assert ce["date"] == date(2026, 10, 19)


def test_parse_bse_csv_same_schema():
    nse = parse_fo_bhavcopy(FIX / "nse_fo_udiff_sample.zip")
    bse = parse_fo_bhavcopy(FIX / "bse_fo_udiff_sample.csv")
    assert list(nse.columns) == list(bse.columns)
    assert set(bse["symbol"]) == {"SENSEX"}


def test_html_block_page_raises_bad_download_and_writes_nothing(tmp_path):
    store = Store(tmp_path)
    session, _, _ = session_with({nse_url(DAY): (200, (FIX / "nse_block_page.html").read_bytes())})
    with pytest.raises(BadDownloadError):
        fetch_nse_fo_bhavcopy(session, store, DAY, URLS)
    assert not (tmp_path / "raw" / "nse_fo").exists()


def test_404_raises_not_published(tmp_path):
    session, _, _ = session_with({})
    with pytest.raises(NotPublishedError):
        fetch_nse_fo_bhavcopy(session, Store(tmp_path), DAY, URLS)


def test_fetch_saves_raw_and_reuses_existing(tmp_path):
    store = Store(tmp_path)
    content = (FIX / "nse_fo_udiff_sample.zip").read_bytes()
    session, http, _ = session_with({nse_url(DAY): (200, content)})
    path = fetch_nse_fo_bhavcopy(session, store, DAY, URLS)
    assert path.read_bytes() == content
    fetch_nse_fo_bhavcopy(session, store, DAY, URLS)
    assert http.requested.count(nse_url(DAY)) == 1


def test_backfill_skips_existing_and_records_status(tmp_path):
    store = Store(tmp_path)
    d1, d2, d3 = date(2026, 10, 15), date(2026, 10, 16), date(2026, 10, 19)
    store.write_raw("nse_fo", d1, f"BhavCopy_NSE_FO_{d1:%Y%m%d}.csv.zip", b"PK\x03\x04old")
    content = (FIX / "nse_fo_udiff_sample.zip").read_bytes()
    session, _, sleep = session_with({nse_url(d3): (200, content)})
    status = backfill_bhavcopy(session, store, [d1, d2, d3], URLS, exchange="NSE")
    assert status == {d1: "skipped_existing", d2: "not_published", d3: "ok"}


def test_non_zip_nse_body_rejected(tmp_path):
    store = Store(tmp_path)
    session, _, _ = session_with({nse_url(DAY): (200, b'{"error": "try later"}')})
    with pytest.raises(BadDownloadError):
        fetch_nse_fo_bhavcopy(session, store, DAY, URLS)
    assert not (tmp_path / "raw" / "nse_fo").exists()


def test_bse_body_without_udiff_header_rejected(tmp_path):
    from quantdesk.eod.bhavcopy import fetch_bse_fo_bhavcopy

    url = URLS["bse_fo_bhavcopy"].format(yyyymmdd=DAY.strftime("%Y%m%d"))
    session, _, _ = session_with({url: (200, b"Sorry, file not found\r\n")})
    with pytest.raises(BadDownloadError):
        fetch_bse_fo_bhavcopy(session, Store(tmp_path), DAY, URLS)
    assert not (tmp_path / "raw" / "bse_fo").exists()


def test_backfill_continues_after_a_network_error(tmp_path):
    """Backlog 5: one requests exception aborted a multi-hour backfill."""
    from datetime import date as _date

    from quantdesk.config import load_settings
    from quantdesk.net.http import PoliteSession
    from quantdesk.storage import Store
    from tests.fakes import FakeClock, FakeHttp, FakeSleep

    urls = load_settings()["urls"]
    d1, d2 = _date(2026, 10, 15), _date(2026, 10, 16)
    zipped = (Path(__file__).parent / "fixtures" / "nse_fo_udiff_sample.zip").read_bytes()
    clock = FakeClock(datetime(2026, 10, 20, 19, 0, tzinfo=IST))
    http = FakeHttp({urls["nse_fo_bhavcopy"].format(yyyymmdd="20261015"): ConnectionError("reset"),
                     urls["nse_fo_bhavcopy"].format(yyyymmdd="20261016"): (200, zipped)}, clock=clock)
    session = PoliteSession(min_interval_s=0.0, clock=clock, sleep=FakeSleep(clock), http=http)
    status = backfill_bhavcopy(session, Store(tmp_path), [d1, d2], urls, exchange="NSE")
    assert status == {d1: "failed: ConnectionError", d2: "ok"}
