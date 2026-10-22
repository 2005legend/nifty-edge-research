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


def test_network_error_is_retried_hourly(tmp_path):
    """Backlog 5: a timeout or reset at 19:00 was final for the day; it is now retried like 'not published'."""
    content = (FIX / "fao_participant_oi_sample.csv").read_bytes()

    def participant(clock):
        return ConnectionError("connection reset") if clock.now().hour < 20 else (200, content)

    report, sleep = make_run(tmp_path, participant)
    assert report.status["participant_oi"] == "ok"
    assert 3600 in sleep.calls


def test_block_page_is_retried_hourly(tmp_path):
    content = (FIX / "fao_participant_oi_sample.csv").read_bytes()

    def participant(clock):
        return (200, b"<html><body>Access Denied</body></html>") if clock.now().hour < 20 else (200, content)

    report, _ = make_run(tmp_path, participant)
    assert report.status["participant_oi"] == "ok"


def test_failure_still_present_at_deadline_keeps_its_reason(tmp_path):
    report, _ = make_run(tmp_path, ConnectionError("connection reset"))
    assert report.status["participant_oi"] == "failed: ConnectionError"


def test_rerun_does_not_duplicate_vix_daily(tmp_path):
    make_run(tmp_path, (200, (FIX / "fao_participant_oi_sample.csv").read_bytes()))
    make_run(tmp_path, (200, (FIX / "fao_participant_oi_sample.csv").read_bytes()))
    assert len(Store(tmp_path).read("vix_daily", DAY)) == 1


def test_without_angel_client_vix_is_skipped_and_nse_files_still_download(tmp_path):
    clock = FakeClock(datetime(2026, 10, 19, 19, 0, tzinfo=IST))
    sleep = FakeSleep(clock)
    http = FakeHttp(routes((200, (FIX / "fao_participant_oi_sample.csv").read_bytes())), clock=clock)
    session = PoliteSession(min_interval_s=0.0, clock=clock, sleep=sleep, http=http)
    report = run_eod(DAY, session=session, store=Store(tmp_path), client=None, clock=clock,
                     sleep=sleep, settings=SETTINGS, until=time(23, 0))
    assert report.status["vix_daily"] == "skipped: no Angel One credentials"
    assert report.status["nse_fo"] == "ok" and report.status["participant_oi"] == "ok"


def test_participant_oi_backfill_skips_existing_and_records_status(tmp_path):
    from quantdesk.eod.flows import backfill_participant_oi

    store = Store(tmp_path)
    urls = load_settings()["urls"]
    body = (Path(__file__).parent / "fixtures" / "fao_participant_oi_sample.csv").read_bytes()
    day1, day2, day3 = date(2019, 1, 1), date(2019, 1, 2), date(2019, 1, 3)
    store.write_raw("participant_oi", day1, "fao_participant_oi_01012019.csv", body)
    http = FakeHttp({urls["nse_participant_oi"].format(ddmmyyyy="02012019"): (200, body),
                     urls["nse_participant_oi"].format(ddmmyyyy="03012019"): ConnectionError("reset")})
    status = backfill_participant_oi(http, store, [day1, day2, day3], urls)
    assert status == {day1: "skipped_existing", day2: "ok", day3: "failed: ConnectionError"}
    assert store.raw_exists("participant_oi", day2, "fao_participant_oi_02012019.csv")


def test_participant_numbers_with_indian_thousands_separators(tmp_path):
    """Some 2019-2020 files quote FII figures as "10,02,064.00"; derive stopped on one (22 Oct 2026)."""
    path = tmp_path / "fao_participant_oi_12122019.csv"
    path.write_text(
        "Participant wise Open Interest (no. of contracts) in Equity Derivatives as on Dec 12 2019,,,\n"
        "Client Type,Future Index Long,Future Index Short,Future Stock Long\n"
        "Client,132884,121478,852086\n"
        'FII,"80,776.00","85,065.00","10,02,064.00"\n')
    frame = parse_participant_oi(path)
    assert fii_index_futures_long_ratio(frame) == round(80776 / (80776 + 85065), 6)
    assert frame.loc[frame.client_type == "FII", "future_stock_long"].iloc[0] == 1002064.0
