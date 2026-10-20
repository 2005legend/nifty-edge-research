"""One fetcher per macro source. Each returns columns series_id, date, value
(the economic calendar returns its own columns plus series_id).

OpenBB is imported inside the fetchers, so the rest of quantdesk works without it.
"""

from datetime import date, timedelta

import pandas as pd

from quantdesk.clock import IST
from quantdesk.config import get_secret

VALUE_COLUMNS = ["series_id", "date", "value"]


def normalize_yf(frame: pd.DataFrame, series_id: str) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame(columns=VALUE_COLUMNS)
    index = frame.index
    if index.tz is None:
        index = index.tz_localize("UTC")
    dates = index.tz_convert(IST).date
    return pd.DataFrame({"series_id": series_id, "date": dates, "value": frame["Close"].to_numpy()})


def fetch_yfinance(spec: dict, start: date, end: date) -> pd.DataFrame:
    import yfinance as yf

    frame = yf.download(spec["symbol"], start=start.isoformat(), end=(end + timedelta(days=1)).isoformat(),
                        progress=False, auto_adjust=False, multi_level_index=False)
    return normalize_yf(frame, spec["id"])


def _obb():
    from openbb import obb

    return obb


def _obb_values(result, series_id: str, value_field: str | None = None) -> pd.DataFrame:
    frame = result.to_df().reset_index()
    date_col = next(c for c in frame.columns if str(c).lower() in ("date", "index"))
    if value_field is None:
        value_field = next(c for c in frame.columns if c != date_col and pd.api.types.is_numeric_dtype(frame[c]))
    out = pd.DataFrame({"series_id": series_id,
                        "date": pd.to_datetime(frame[date_col]).dt.date,
                        "value": pd.to_numeric(frame[value_field], errors="coerce")})
    return out.dropna(subset=["value"])


def _fred_ready():
    obb = _obb()
    obb.user.credentials.fred_api_key = get_secret("FRED_API_KEY")
    return obb


def fetch_fed_treasury(spec, start, end):
    result = _obb().federal_reserve.treasury_rates(start_date=start.isoformat(), end_date=end.isoformat())
    return _obb_values(result, spec["id"], spec.get("field", "year_10"))


def fetch_fred(spec, start, end):
    result = _fred_ready().fred.economy.fred_series(symbol=spec["symbol"], start_date=start.isoformat(),
                                                    end_date=end.isoformat())
    return _obb_values(result, spec["id"], spec["symbol"])


def fetch_fred_brent(spec, start, end):
    result = _fred_ready().fred.commodity.price.spot(commodity="brent", start_date=start.isoformat(),
                                                     end_date=end.isoformat())
    return _obb_values(result, spec["id"])


def fetch_oecd_cpi(spec, start, end):
    return _obb_values(_obb().oecd.cpi(country=spec["country"], start_date=start.isoformat()), spec["id"])


def fetch_oecd_gdp_real(spec, start, end):
    return _obb_values(_obb().oecd.gdp_real(country=spec["country"], start_date=start.isoformat()), spec["id"])


def fetch_oecd_rates(spec, start, end):
    result = _obb().oecd.country_interest_rates(country=spec["country"], start_date=start.isoformat())
    return _obb_values(result, spec["id"])


def fetch_imf_cpi(spec, start, end):
    return _obb_values(_obb().imf.cpi(country=spec["country"], start_date=start.isoformat()), spec["id"])


def fetch_nasdaq_calendar(spec, start, end):
    result = _obb().nasdaq.economy.calendar(start_date=start.isoformat(), end_date=(end + timedelta(days=7)).isoformat())
    frame = result.to_df().reset_index()
    frame.insert(0, "series_id", spec["id"])
    return frame


def fetch_unverified(spec, start, end):
    raise NotImplementedError(f"url unverified for source {spec['source']}")


FETCHERS = {
    "yfinance": fetch_yfinance,
    "openbb_federal_reserve_treasury": fetch_fed_treasury,
    "openbb_fred": fetch_fred,
    "openbb_fred_brent": fetch_fred_brent,
    "openbb_oecd_cpi": fetch_oecd_cpi,
    "openbb_oecd_gdp_real": fetch_oecd_gdp_real,
    "openbb_oecd_rates": fetch_oecd_rates,
    "openbb_imf_cpi": fetch_imf_cpi,
    "openbb_nasdaq_calendar": fetch_nasdaq_calendar,
    "fbil": fetch_unverified,
    "nse_index_fundamentals": fetch_unverified,
}


def fetch_intraday_yf(tickers: list[str], now) -> pd.DataFrame:
    import yfinance as yf

    frames = []
    for ticker in tickers:
        frame = yf.download(ticker, period="1d", interval="5m", progress=False, auto_adjust=False,
                            multi_level_index=False)
        if frame is None or frame.empty:
            continue
        frame = frame.reset_index().rename(columns=str.lower)
        ts_col = "datetime" if "datetime" in frame.columns else frame.columns[0]
        frames.append(pd.DataFrame({"ticker": ticker, "ts": pd.to_datetime(frame[ts_col]).dt.tz_convert(IST),
                                    "open": frame["open"], "high": frame["high"], "low": frame["low"],
                                    "close": frame["close"], "volume": frame["volume"]}))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
