"""NSE and BSE F&O bhavcopy (UDiFF format): fetch, parse, backfill."""

import io
import zipfile
from datetime import date
from pathlib import Path
from typing import Iterable

import pandas as pd

from quantdesk.net.http import BadDownloadError, looks_like_html
from quantdesk.storage import Store

COLUMNS = ["date", "symbol", "instrument", "expiry", "strike", "option_type", "open", "high", "low",
           "close", "settle", "underlying", "oi", "chg_oi", "volume"]
UDIFF_MAP = {"TradDt": "date", "TckrSymb": "symbol", "FinInstrmTp": "instrument", "XpryDt": "expiry",
             "StrkPric": "strike", "OptnTp": "option_type", "OpnPric": "open", "HghPric": "high",
             "LwPric": "low", "ClsPric": "close", "SttlmPric": "settle", "UndrlygPric": "underlying",
             "OpnIntrst": "oi", "ChngInOpnIntrst": "chg_oi", "TtlTradgVol": "volume"}
SOURCES = {"NSE": ("nse_fo", "nse_fo_bhavcopy", "BhavCopy_NSE_FO_{d:%Y%m%d}.csv.zip"),
           "BSE": ("bse_fo", "bse_fo_bhavcopy", "BhavCopy_BSE_FO_{d:%Y%m%d}.csv")}


class NotPublishedError(RuntimeError):
    """The exchange has not published the file yet (HTTP 404)."""


def _fetch(session, store: Store, day: date, urls: dict, exchange: str) -> Path:
    source, url_key, name_fmt = SOURCES[exchange]
    name = name_fmt.format(d=day)
    if store.raw_exists(source, day, name):
        return store.raw_path(source, day, name)
    response = session.get(urls[url_key].format(yyyymmdd=day.strftime("%Y%m%d")))
    if response.status_code == 404:
        raise NotPublishedError(f"{exchange} F&O bhavcopy for {day} not published")
    if response.status_code != 200:
        raise BadDownloadError(f"{exchange} F&O bhavcopy for {day}: HTTP {response.status_code}")
    if not _looks_valid(exchange, response.content):
        raise BadDownloadError(f"{exchange} F&O bhavcopy for {day}: body is not a bhavcopy file")
    return store.write_raw(source, day, name, response.content)


def _looks_valid(exchange: str, content: bytes) -> bool:
    """Positive check, because raw files are immutable: a wrong body saved once would block the real file."""
    if not content or looks_like_html(content):
        return False
    if exchange == "NSE":
        return content[:2] == b"PK"  # NSE serves a zip
    return content.lstrip(b"\xef\xbb\xbf \r\n").startswith(b"TradDt")  # BSE serves the UDiFF CSV


def fetch_nse_fo_bhavcopy(session, store: Store, day: date, urls: dict) -> Path:
    return _fetch(session, store, day, urls, "NSE")


def fetch_bse_fo_bhavcopy(session, store: Store, day: date, urls: dict) -> Path:
    return _fetch(session, store, day, urls, "BSE")


def parse_fo_bhavcopy(path: Path) -> pd.DataFrame:
    path = Path(path)
    data = path.read_bytes()
    if data[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            data = zf.read(zf.namelist()[0])
    raw = pd.read_csv(io.BytesIO(data), dtype=str, keep_default_na=False)
    raw.columns = [c.strip() for c in raw.columns]
    frame = raw[list(UDIFF_MAP)].rename(columns=UDIFF_MAP)
    for column in ("date", "expiry"):
        frame[column] = pd.to_datetime(frame[column].str.strip(), errors="coerce").dt.date
    for column in ("strike", "open", "high", "low", "close", "settle", "underlying"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    for column in ("oi", "chg_oi", "volume"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0).astype("int64")
    frame["option_type"] = frame["option_type"].str.strip().replace("", None)
    return frame[COLUMNS]


def backfill_bhavcopy(session, store: Store, trading_days: Iterable[date], urls: dict,
                      exchange: str = "NSE") -> dict[date, str]:
    status: dict[date, str] = {}
    source, _, name_fmt = SOURCES[exchange]
    for day in trading_days:
        if store.raw_exists(source, day, name_fmt.format(d=day)):
            status[day] = "skipped_existing"
            continue
        try:
            _fetch(session, store, day, urls, exchange)
            status[day] = "ok"
        except NotPublishedError:
            status[day] = "not_published"
        except BadDownloadError:
            status[day] = "bad_download"
    return status
