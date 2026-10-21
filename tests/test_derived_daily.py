from datetime import date, datetime

import pandas as pd

from quantdesk.clock import IST
from quantdesk.derived.daily import build_daily
from quantdesk.derived.store import DerivedStore
from quantdesk.storage import Store


def candle(day, close, target="NIFTY"):
    return pd.DataFrame({"ts": [datetime(day.year, day.month, day.day, tzinfo=IST)], "open": [1.0],
                         "high": [2.0], "low": [0.5], "close": [close], "volume": [0], "target": [target]})


def test_daily_keeps_the_latest_candle_and_stamps_16_00(tmp_path):
    raw = Store(tmp_path / "raw")
    day = date(2024, 3, 4)
    raw.append_parquet("history_one_day", day, candle(day, 1.5))
    raw.append_parquet("history_one_day", day, candle(day, 1.6))   # a later refetch, same day
    derived = DerivedStore(tmp_path / "d")
    build_daily(raw, derived)
    rows = derived.read("daily")
    assert len(rows) == 1 and rows.loc[0, "close"] == 1.6 and rows.loc[0, "day"] == day
    assert rows.loc[0, "available_at"] == pd.Timestamp(datetime(2024, 3, 4, 16, 0, tzinfo=IST))


def test_a_day_refetched_in_a_later_chunk_is_one_row(tmp_path):
    raw = Store(tmp_path / "raw")
    day = date(2024, 3, 4)
    # Overlapping backfill chunks store the same day under two folder dates; the later folder wins.
    raw.append_parquet("history_one_day", date(2024, 3, 1), candle(day, 1.5))
    raw.append_parquet("history_one_day", date(2024, 4, 1), candle(day, 1.6))
    raw.append_parquet("history_one_day", date(2024, 4, 1), candle(day, 2.6, "SENSEX"))
    derived = DerivedStore(tmp_path / "d")
    build_daily(raw, derived)
    rows = derived.read("daily")
    assert len(rows) == 2
    nifty = rows[rows.target == "NIFTY"]
    assert nifty["day"].tolist() == [day] and nifty["close"].tolist() == [1.6]
    assert rows[rows.target == "SENSEX"]["close"].tolist() == [2.6]
