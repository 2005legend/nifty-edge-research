"""Daily and intraday macro collection. A failing series never stops the others."""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

import pandas as pd

from quantdesk.config import MissingSecretError, get_secret
from quantdesk.macro.sources import FETCHERS, fetch_intraday_yf
from quantdesk.net.ratelimit import retry
from quantdesk.storage import Store

SPECIAL_KINDS = {"econ_calendar": "econ_calendar", "nifty_fundamentals": "index_fundamentals"}


@dataclass
class MacroReport:
    status: dict = field(default_factory=dict)


def _has_fred_key() -> bool:
    try:
        get_secret("FRED_API_KEY")
        return True
    except MissingSecretError:
        return False


def run_macro_daily(day: date, *, store: Store, fetchers: dict = FETCHERS, settings: dict, sleep,
                    start: date | None = None) -> MacroReport:
    macro = settings["macro"]
    default_lookback = macro.get("daily_lookback_days", 10)
    fred_sources = set(macro.get("fred_sources", ["openbb_fred", "openbb_fred_brent"]))
    report = MacroReport()
    for spec in macro["series"]:
        series_start = start or day - timedelta(days=spec.get("lookback_days", default_lookback))
        if spec["source"] in fred_sources and not _has_fred_key():
            report.status[spec["id"]] = "missing_key"
            continue
        fetcher = fetchers.get(spec["source"])
        if fetcher is None:
            report.status[spec["id"]] = "failed"
            continue
        try:
            frame = retry(lambda f=fetcher, s=spec, st=series_start: f(s, st, day), attempts=3, base_delay=2,
                          max_delay=8,
                          retry_on=lambda e: not isinstance(e, NotImplementedError), sleep=sleep)
        except Exception:  # noqa: BLE001 - recorded as failed, others continue
            report.status[spec["id"]] = "failed"
            continue
        if frame is None or frame.empty:
            report.status[spec["id"]] = "empty"
            continue
        store.append_parquet(SPECIAL_KINDS.get(spec["id"], "macro_daily"), day, frame)
        report.status[spec["id"]] = "ok"
    return report


def run_macro_intraday(now: datetime, *, store: Store, fetch_intraday=fetch_intraday_yf, settings: dict) -> MacroReport:
    tickers = settings["macro"]["intraday_tickers"]
    report = MacroReport()
    try:
        frame = fetch_intraday(tickers, now)
    except Exception:  # noqa: BLE001
        return MacroReport(status={t: "failed" for t in tickers})
    present = set(frame["ticker"]) if not frame.empty else set()
    for ticker in tickers:
        report.status[ticker] = "ok" if ticker in present else "failed"
    if not frame.empty:
        store.append_parquet("macro_intraday", now.date(), frame[frame["ticker"].isin(tickers)])
    return report
