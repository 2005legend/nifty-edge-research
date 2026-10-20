from datetime import date, datetime, time
from pathlib import Path

import pandas as pd

from quantdesk.clock import IST
from quantdesk.config import load_settings
from quantdesk.eod.flows import (
    fii_index_futures_long_ratio,
    parse_fii_dii,
    parse_participant_oi,
    run_eod,
)
from quantdesk.net.http import PoliteSession
from quantdesk.storage import Store
from tests.fakes import FakeClock, FakeHttp, FakeSleep

FIX = Path(__file__).parent / "fixtures"
DAY = date(2026, 10, 19)
SETTINGS = load_settings()
URLS = SETTINGS["urls"]


class FakeVixClient:
    def candles(self, exchange, token, interval, start, end):
        return pd.DataFrame({"ts": [start], "open": [14.5], "high": [15.4], "low": [13.5],
                             "close": [14.77], "volume": [0]})


def routes(participant_route):
    return {
        URLS["nse_fo_bhavcopy"].format(yyyymmdd="20261019"): (200, (FIX / "nse_fo_udiff_sample.zip").read_bytes()),
        URLS["bse_fo_bhavcopy"].format(yyyymmdd="20261019"): (200, (FIX / "bse_fo_udiff_sample.csv").read_bytes()),
        URLS["nse_participant_oi"].format(ddmmyyyy="19102026"): participant_route,
        URLS["nse_fii_dii"]: (200, (FIX / "fiidii_sample.json").read_bytes()),
        URLS["nse_nifty50_list"]: (200, (FIX / "ind_nifty50list_sample.csv").read_bytes()),
    }


def make_run(tmp_path, participant_route):
    clock = FakeClock(datetime(2026, 10, 19, 19, 0, tzinfo=IST))
    sleep = FakeSleep(clock)
    if callable(participant_route):
        route = lambda url: participant_route(clock)  # noqa: E731
    else:
        route = participant_route
    http = FakeHttp(routes(route), clock=clock)
    session = PoliteSession(min_interval_s=0.0, clock=clock, sleep=sleep, http=http)
    report = run_eod(DAY, session=session, store=Store(tmp_path), client=FakeVixClient(), clock=clock,
                     sleep=sleep, settings=SETTINGS, until=time(23, 0))
    return report, sleep


def test_parse_participant_oi_rows_and_ratio():
    frame = parse_participant_oi(FIX / "fao_participant_oi_sample.csv")
    assert list(frame["client_type"]) == ["Client", "DII", "FII", "Pro", "TOTAL"]
    assert "future_index_long" in frame.columns
    assert fii_index_futures_long_ratio(frame) == 0.30


def test_parse_fii_dii_net_values():
    frame = parse_fii_dii(FIX / "fiidii_sample.json")
    fii = frame[frame["category"] == "FII"].iloc[0]
    dii = frame[frame["category"] == "DII"].iloc[0]
    assert fii["net"] == -4699.25
    assert dii["buy"] == 20493.12
    assert fii["date"] == DAY


def test_run_eod_retries_not_published_until_deadline(tmp_path):
    content = (FIX / "fao_participant_oi_sample.csv").read_bytes()

    def participant(clock):
        return (200, content) if clock.now().hour >= 21 else (404, b"")

    report, sleep = make_run(tmp_path, participant)
    assert report.status["participant_oi"] == "ok"
    assert [s for s in sleep.calls if s >= 3600] == [3600, 3600]
    assert all(report.status[k] == "ok" for k in ("nse_fo", "bse_fo", "fii_dii", "vix_daily", "nifty50_list"))


def test_run_eod_marks_missing_after_deadline(tmp_path):
    report, _ = make_run(tmp_path, (404, b""))
    assert report.status["participant_oi"] == "not_published"
    assert report.status["nse_fo"] == "ok"


def test_participant_body_without_header_is_bad_download(tmp_path):
    report, _ = make_run(tmp_path, (200, b"Service temporarily unavailable"))
    assert report.status["participant_oi"] == "bad_download"
    assert not (tmp_path / "raw" / "participant_oi").exists()
