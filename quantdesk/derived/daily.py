"""Official daily OHLC (design §5, table `daily`).

Angel One's ONE_DAY candles are the official session open, high, low and close, which the noise band needs
as its anchors: the band is gap-adjusted around the official open and the prior official close, not around
whatever the first and last 1-minute bars happen to print.

Chunks refetch overlapping ranges, so the same (target, day) can arrive in several files. The latest file
wins, exactly as in `minutes`. A day's official figures are published after the close, so `available_at` is
16:00 IST on the day itself (design §4).
"""

import duckdb

from quantdesk.derived.store import DerivedStore


def build_daily(store, derived: DerivedStore) -> dict:
    source = (store.root / "raw" / "history_one_day" / "**" / "*.parquet").as_posix()
    con = duckdb.connect()
    return derived.write_query("daily", con, f"""
        with raw as (
            select target, ts, open, high, low, close, filename,
                   cast(timezone('Asia/Kolkata', ts) as date) as day
            from read_parquet('{source}', filename=true, hive_partitioning=false, union_by_name=true)
        ), ranked as (
            select *, row_number() over (partition by target, day order by filename desc) as rn from raw
        )
        select target, day, open, high, low, close,
               (day + time '16:00') at time zone 'Asia/Kolkata' as available_at
        from ranked
        where rn = 1
        order by target, day
    """)
