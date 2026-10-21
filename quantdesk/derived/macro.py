"""Macro series with the moment each becomes knowable (design §4, §5; R5).

A value dated d is not knowledge at d: FRED publishes late, US and Asian closes land after the Indian open,
and OECD/IMF monthly releases come weeks after the period they describe. Each series therefore carries its
own lag, and `available_at` is the first moment the real system could have used the row. A series with no
lag rule raises rather than defaulting, so a newly added series cannot silently enter the backtest as if it
had been known on the day.
"""

from datetime import date, datetime, time, timedelta

import duckdb
import pandas as pd

from quantdesk.clock import IST
from quantdesk.derived.store import DerivedStore

_FRED = ("dgs10", "dexinus", "brent_fred")
_GLOBAL = ("brent", "usdinr", "dxy", "es", "nq", "spx", "us10y", "n225", "hsi", "kospi")
_INDIA = ("nifty_yf", "sensex_yf", "banknifty_yf", "indiavix_yf")
_MONTHLY = ("india_cpi_oecd", "india_gdp_oecd", "india_rates_oecd", "india_cpi_imf")
_NSE_INDEX = ("nifty_fundamentals", "india_gsec10y_price")

#: series_id -> (calendar days after the value's own date, IST clock time)
MACRO_LAGS: dict[str, tuple[int, time]] = {
    **{s: (2, time(9, 0)) for s in _FRED},
    **{s: (1, time(9, 0)) for s in _GLOBAL},
    **{s: (0, time(16, 0)) for s in _INDIA},
    **{s: (60, time(9, 0)) for s in _MONTHLY},
    **{s: (0, time(20, 0)) for s in _NSE_INDEX},
}


def available_at(series_id: str, d: date) -> datetime:
    days, at = MACRO_LAGS[series_id]
    return datetime.combine(d + timedelta(days=days), at, tzinfo=IST)


def build_macro(store, derived: DerivedStore) -> dict:
    source = (store.root / "raw" / "macro_daily" / "**" / "*.parquet").as_posix()
    con = duckdb.connect()
    # The collector runs twice a day, so one (series, date) can be stored several times under one folder
    # date. Ordering by the file path picks the latest fetch, deterministically, as `minutes` and `daily` do.
    rows = con.execute(f"""
        select series_id, date, value
        from (
            select *, row_number() over (partition by series_id, date order by filename desc) as rn
            from read_parquet('{source}', filename=true, hive_partitioning=false, union_by_name=true)
        )
        where rn = 1
        order by series_id, date
    """).df()
    rows["date"] = rows["date"].dt.date
    rows["available_at"] = pd.Series([available_at(s, d) for s, d in zip(rows["series_id"], rows["date"])],
                                     index=rows.index)
    return derived.write_frame("macro", rows)
