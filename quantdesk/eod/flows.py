"""Participant-wise OI, FII/DII cash flows, Nifty 50 list, and the end-of-day run."""

import io
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pandas as pd

from quantdesk.clock import IST
from quantdesk.eod.bhavcopy import NotPublishedError, fetch_bse_fo_bhavcopy, fetch_nse_fo_bhavcopy
from quantdesk.net.http import BadDownloadError, looks_like_html
from quantdesk.storage import Store

RETRY_EVERY_S = 3600
ITEMS = ["nse_fo", "bse_fo", "participant_oi", "fii_dii", "vix_daily", "nifty50_list"]


@dataclass
class EodReport:
    status: dict = field(default_factory=dict)


def _download(session, store: Store, day: date, source: str, name: str, url: str,
              must_contain: bytes) -> Path:
    if store.raw_exists(source, day, name):
        return store.raw_path(source, day, name)
    response = session.get(url)
    if response.status_code == 404:
        raise NotPublishedError(f"{source} for {day} not published")
    if response.status_code != 200:
        raise BadDownloadError(f"{source} for {day}: HTTP {response.status_code}")
    if not response.content or looks_like_html(response.content) or must_contain not in response.content[:4096]:
        raise BadDownloadError(f"{source} for {day}: got an HTML page, not data")
    return store.write_raw(source, day, name, response.content)


def fetch_participant_oi(session, store: Store, day: date, urls: dict) -> Path:
    stamp = day.strftime("%d%m%Y")
    return _download(session, store, day, "participant_oi", f"fao_participant_oi_{stamp}.csv",
                     urls["nse_participant_oi"].format(ddmmyyyy=stamp), must_contain=b"Client Type")


def _snake(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")


def parse_participant_oi(path: Path) -> pd.DataFrame:
    lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    frame = pd.read_csv(io.StringIO("\n".join(lines[1:])))
    frame.columns = [_snake(c) for c in frame.columns]
    frame["client_type"] = frame["client_type"].astype(str).str.strip()
    return frame


def fii_index_futures_long_ratio(frame: pd.DataFrame) -> float:
    fii = frame[frame["client_type"] == "FII"].iloc[0]
    long, short = float(fii["future_index_long"]), float(fii["future_index_short"])
    return round(long / (long + short), 6)


def fetch_fii_dii(session, store: Store, day: date, urls: dict) -> Path:
    """NSE serves only the latest day's figures; a response for another day counts as not published."""
    if store.raw_exists("fii_dii", day, "fiidii.json"):
        return store.raw_path("fii_dii", day, "fiidii.json")
    response = session.get(urls["nse_fii_dii"])
    if response.status_code != 200 or looks_like_html(response.content):
        raise BadDownloadError(f"FII/DII: HTTP {response.status_code}")
    rows = json.loads(response.content)
    dates = {datetime.strptime(r["date"], "%d-%b-%Y").date() for r in rows}
    if day not in dates:
        raise NotPublishedError(f"FII/DII for {day} not published yet")
    return store.write_raw("fii_dii", day, "fiidii.json", response.content)


def parse_fii_dii(path: Path) -> pd.DataFrame:
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    out = []
    for r in rows:
        category = "FII" if "FII" in r["category"].upper() else "DII"
        out.append({"date": datetime.strptime(r["date"], "%d-%b-%Y").date(), "category": category,
                    "buy": float(r["buyValue"]), "sell": float(r["sellValue"]), "net": float(r["netValue"])})
    return pd.DataFrame(out)


def fetch_nifty50_list(session, store: Store, day: date, urls: dict) -> Path:
    return _download(session, store, day, "nifty50_list", "ind_nifty50list.csv", urls["nse_nifty50_list"],
                     must_contain=b"Symbol")


def _vix_daily(client, store: Store, day: date, settings: dict) -> None:
    if not store.read("vix_daily", day).empty:
        return  # already stored by an earlier run
    spec = settings["angel"]["index_tokens"]["INDIAVIX"]
    start = datetime.combine(day, time(0, 0), tzinfo=IST)
    frame = client.candles(spec["exchange"], spec["token"], "ONE_DAY", start, start + timedelta(hours=23, minutes=59))
    if frame is None or frame.empty:
        raise NotPublishedError("India VIX daily candle not available yet")
    store.append_parquet("vix_daily", day, frame)


def run_eod(day: date, *, session, store: Store, client, clock, sleep, settings: dict, until: time) -> EodReport:
    urls = settings["urls"]
    actions = {
        "nse_fo": lambda: fetch_nse_fo_bhavcopy(session, store, day, urls),
        "bse_fo": lambda: fetch_bse_fo_bhavcopy(session, store, day, urls),
        "participant_oi": lambda: fetch_participant_oi(session, store, day, urls),
        "fii_dii": lambda: fetch_fii_dii(session, store, day, urls),
        "vix_daily": lambda: _vix_daily(client, store, day, settings),
        "nifty50_list": lambda: fetch_nifty50_list(session, store, day, urls),
    }
    deadline = datetime.combine(day, until, tzinfo=IST)
    report = EodReport()
    try:
        session.bootstrap(urls["nse_home"])
    except Exception:  # noqa: BLE001 - cookies are best effort
        pass
    pending = list(ITEMS)
    if client is None:  # only the VIX daily candle needs an Angel One login
        pending.remove("vix_daily")
        report.status["vix_daily"] = "skipped: no Angel One credentials"
    reason: dict[str, str] = {}
    while True:
        still = []
        for item in pending:
            try:
                actions[item]()
                report.status[item] = "ok"
            # Not published yet, an exchange block page, or a network error: all retried hourly.
            except NotPublishedError:
                still.append(item)
                reason[item] = "not_published"
            except BadDownloadError:
                still.append(item)
                reason[item] = "bad_download"
            except (ConnectionError, TimeoutError, OSError) as exc:  # requests' errors are OSErrors
                still.append(item)
                reason[item] = f"failed: {type(exc).__name__}"
            except Exception as exc:  # noqa: BLE001 - one item never stops the others
                report.status[item] = f"failed: {type(exc).__name__}"
        pending = still
        if not pending or clock.now() + timedelta(seconds=RETRY_EVERY_S) > deadline:
            break
        sleep(RETRY_EVERY_S)
    for item in pending:
        report.status[item] = reason.get(item, "not_published")
    return report


def backfill_participant_oi(session, store: Store, days, urls: dict) -> dict[date, str]:
    """NSE's participant-wise OI files for past days (the FII-flip context, spec §5A.2); files on disk are kept."""
    status: dict[date, str] = {}
    for day in days:
        stamp = day.strftime("%d%m%Y")
        if store.raw_exists("participant_oi", day, f"fao_participant_oi_{stamp}.csv"):
            status[day] = "skipped_existing"
            continue
        try:
            fetch_participant_oi(session, store, day, urls)
            status[day] = "ok"
        except NotPublishedError:
            status[day] = "not_published"
        except BadDownloadError:
            status[day] = "bad_download"
        except (ConnectionError, TimeoutError, OSError) as exc:  # one network error never ends the run
            status[day] = f"failed: {type(exc).__name__}"
    return status
