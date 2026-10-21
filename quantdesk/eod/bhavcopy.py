"""NSE and BSE F&O bhavcopy: fetch, parse, backfill.

NSE days from 8 Jul 2024 come in UDiFF format; earlier days only in the old layout from the historical
archive. Both parse to the same columns, and both report volume in contracts (checked live 21 Oct 2026).
BSE files before UDiFF are not covered.
"""

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
UDIFF_FROM = date(2024, 7, 8)
LEGACY_MAP = {"TIMESTAMP": "date", "SYMBOL": "symbol", "INSTRUMENT": "instrument", "EXPIRY_DT": "expiry",
              "STRIKE_PR": "strike", "OPTION_TYP": "option_type", "OPEN": "open", "HIGH": "high", "LOW": "low",
              "CLOSE": "close", "SETTLE_PR": "settle", "OPEN_INT": "oi", "CHG_IN_OI": "chg_oi",
              "CONTRACTS": "volume"}
LEGACY_INSTRUMENTS = {"FUTIDX": "IDF", "OPTIDX": "IDO", "FUTSTK": "STF", "OPTSTK": "STO"}


class NotPublishedError(RuntimeError):
    """The exchange has not published the file yet (HTTP 404)."""


def _candidates(exchange: str, day: date, urls: dict) -> list[tuple[str, str]]:
    """(raw file name, url) to try in order: the old NSE archive first for days before UDiFF."""
    _, url_key, name_fmt = SOURCES[exchange]
    udiff = (name_fmt.format(d=day), urls[url_key].format(yyyymmdd=day.strftime("%Y%m%d")))
    if exchange == "NSE" and day < UDIFF_FROM:
        mon = day.strftime("%b").upper()
        legacy_url = urls["nse_fo_bhavcopy_legacy"].format(yyyy=day.year, mon=mon, dd=f"{day:%d}")
        return [(f"fo{day:%d}{mon}{day:%Y}bhav.csv.zip", legacy_url), udiff]
    return [udiff]


def _existing(store: Store, day: date, urls: dict, exchange: str) -> Path | None:
    source = SOURCES[exchange][0]
    for name, _ in _candidates(exchange, day, urls):
        if store.raw_exists(source, day, name):
            return store.raw_path(source, day, name)
    return None


def _fetch(session, store: Store, day: date, urls: dict, exchange: str) -> Path:
    source = SOURCES[exchange][0]
    existing = _existing(store, day, urls, exchange)
    if existing is not None:
        return existing
    candidates = _candidates(exchange, day, urls)
    for i, (name, url) in enumerate(candidates):
        response = session.get(url)
        if response.status_code == 404:
            if i < len(candidates) - 1:
                continue  # try the other layout
            raise NotPublishedError(f"{exchange} F&O bhavcopy for {day} not published")
        if response.status_code != 200:
            raise BadDownloadError(f"{exchange} F&O bhavcopy for {day}: HTTP {response.status_code}")
        if not _looks_valid(exchange, response.content):
            raise BadDownloadError(f"{exchange} F&O bhavcopy for {day}: body is not a bhavcopy file")
        return store.write_raw(source, day, name, response.content)
    raise NotPublishedError(f"{exchange} F&O bhavcopy for {day} not published")


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
    if "INSTRUMENT" in raw.columns:  # NSE layout before July 2024
        frame = raw[list(LEGACY_MAP)].rename(columns=LEGACY_MAP)
        code = frame["instrument"].str.strip()
        frame["instrument"] = code.map(LEGACY_INSTRUMENTS).fillna(code)
        frame["underlying"] = ""
        futures = frame["instrument"].isin(["IDF", "STF"])
        frame.loc[futures, "strike"] = ""
        frame["option_type"] = frame["option_type"].str.strip().replace("XX", "")
        date_format = "%d-%b-%Y"
    else:
        frame = raw[list(UDIFF_MAP)].rename(columns=UDIFF_MAP)
        date_format = None
    for column in ("date", "expiry"):
        frame[column] = pd.to_datetime(frame[column].str.strip(), format=date_format, errors="coerce").dt.date
    for column in ("strike", "open", "high", "low", "close", "settle", "underlying"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    for column in ("oi", "chg_oi", "volume"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0).astype("int64")
    frame["option_type"] = frame["option_type"].str.strip().replace("", None)
    return frame[COLUMNS]


def backfill_bhavcopy(session, store: Store, trading_days: Iterable[date], urls: dict,
                      exchange: str = "NSE") -> dict[date, str]:
    status: dict[date, str] = {}
    for day in trading_days:
        if _existing(store, day, urls, exchange) is not None:
            status[day] = "skipped_existing"
            continue
        try:
            _fetch(session, store, day, urls, exchange)
            status[day] = "ok"
        except NotPublishedError:
            status[day] = "not_published"
        except BadDownloadError:
            status[day] = "bad_download"
        except (ConnectionError, TimeoutError, OSError) as exc:  # one network error never ends the run
            status[day] = f"failed: {type(exc).__name__}"
    return status
