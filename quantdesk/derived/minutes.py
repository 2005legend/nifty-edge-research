"""One-minute bars and the session table (R4, R8).

`minutes`: every target's Angel One candles with duplicates removed (refetched chunks overlap; the latest
file wins), only 09:15-15:29 bars kept, and `available_at` = bar start + 1 minute, because a bar is known
only when it closes. Evening (Muhurat) bars and stray off-hours prints are dropped here.

`sessions`: one row per day that has NIFTY bars, marked `regular` or `irregular`. Irregular days (weekend
special sessions, outages, late starts, short days) are excluded from signals and from band windows.
"""

from datetime import date, time

import duckdb

from quantdesk.derived.store import DerivedStore

REGULAR_SHARE = 0.95  # a regular day has at least 95% of its expected bars


def build_minutes(store, derived: DerivedStore) -> dict:
    source = (store.root / "raw" / "history_one_minute" / "**" / "*.parquet").as_posix()
    con = duckdb.connect()
    con.execute("set preserve_insertion_order = false")
    years = [y for (y,) in con.execute(
        f"select distinct year(timezone('Asia/Kolkata', ts)) from read_parquet('{source}', hive_partitioning=false) order by 1"
    ).fetchall()]
    queries = {}
    for year in years:  # one year at a time: the whole table does not fit in memory
        queries[f"year={year}"] = f"""
            with raw as (
                select target, ts, open, high, low, close, volume, filename,
                       timezone('Asia/Kolkata', ts) as local
                from read_parquet('{source}', filename=true, hive_partitioning=false, union_by_name=true)
                where ts >= timestamptz '{year}-01-01 00:00:00+05:30' and ts < timestamptz '{year + 1}-01-01 00:00:00+05:30'
            ), ranked as (
                select *, row_number() over (partition by target, ts order by filename desc) as rn from raw
            )
            select target, ts, open, high, low, close, volume,
                   ts + interval 1 minute as available_at,
                   cast(local as date) as day
            from ranked
            where rn = 1 and cast(local as time) >= time '09:15' and cast(local as time) < time '15:30'
        """
    return derived.write_parts("minutes", con, queries)


def build_sessions(derived: DerivedStore, session: dict) -> dict:
    auction = session.get("closing_auction") or {}
    since = date.fromisoformat(str(auction["since"])) if auction else date.max
    con = duckdb.connect()
    days = con.execute(f"""
        select day,
               count(*) as bars,
               min(cast(timezone('Asia/Kolkata', ts) as time)) as first_bar,
               max(cast(timezone('Asia/Kolkata', ts) as time)) as last_bar
        from read_parquet('{derived.glob("minutes")}', hive_partitioning=true)
        where target = 'NIFTY'
        group by day order by day
    """).df()
    days["day"] = days["day"].dt.date

    def kind(row) -> str:
        auction_day = row.day >= since
        expected = 361 if auction_day else 375      # 09:15-15:14 plus the 15:29 auction print, or 09:15-15:29
        last_ok = row.last_bar >= (time(15, 14) if auction_day else time(15, 29))
        regular = (row.day.weekday() < 5 and row.first_bar <= time(9, 20) and last_ok
                   and row.bars >= REGULAR_SHARE * expected)
        return "regular" if regular else "irregular"

    days["kind"] = days.apply(kind, axis=1)
    return derived.write_frame("sessions", days)
