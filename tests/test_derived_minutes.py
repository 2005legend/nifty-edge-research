from datetime import date, datetime, timedelta

import pandas as pd

from quantdesk.clock import IST
from quantdesk.derived.minutes import build_minutes, build_sessions
from quantdesk.derived.store import DerivedStore
from quantdesk.storage import Store


def bars(target, day, start="09:15", n=375, every=1):
    t0 = datetime.combine(day, datetime.strptime(start, "%H:%M").time(), tzinfo=IST)
    ts = [t0 + timedelta(minutes=i * every) for i in range(n)]
    return pd.DataFrame({"ts": ts, "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 10, "target": target})


def test_minutes_are_deduplicated_session_filtered_and_stamped(tmp_path):
    raw = Store(tmp_path / "raw")
    day = date(2024, 3, 4)
    raw.append_parquet("history_one_minute", day, bars("NIFTY", day))
    raw.append_parquet("history_one_minute", day, bars("NIFTY", day, n=10))            # a refetched chunk
    raw.append_parquet("history_one_minute", day, bars("SHRIRAMFIN", day, start="04:18", n=1))
    raw.append_parquet("history_one_minute", day, bars("NIFTY", day, start="18:00", n=60))  # an evening session
    derived = DerivedStore(tmp_path / "derived")
    build_minutes(raw, derived)
    minutes = derived.read("minutes")
    assert len(minutes) == 375 and set(minutes["target"]) == {"NIFTY"}
    first = minutes.sort_values("ts").iloc[0]
    assert first["available_at"] - first["ts"] == pd.Timedelta(minutes=1)  # a bar is known when it closes (R4)
    assert (minutes["day"] == day).all()


def test_sessions_mark_special_and_short_days_irregular(tmp_path):
    raw = Store(tmp_path / "raw")
    regular, short, weekend, late = date(2024, 3, 4), date(2021, 2, 24), date(2024, 3, 2), date(2026, 7, 23)
    missing_open = date(2022, 1, 4)                                                      # Angel lacks the 09:15 bar
    raw.append_parquet("history_one_minute", missing_open, bars("NIFTY", missing_open, start="09:16", n=374))
    auction = date(2026, 10, 19)
    raw.append_parquet("history_one_minute", regular, bars("NIFTY", regular))
    raw.append_parquet("history_one_minute", short, bars("NIFTY", short, n=145))        # the 2021 outage
    raw.append_parquet("history_one_minute", weekend, bars("NIFTY", weekend))           # a Saturday session
    raw.append_parquet("history_one_minute", late, bars("NIFTY", late, start="10:31", n=299))
    after = bars("NIFTY", auction, n=360)
    raw.append_parquet("history_one_minute", auction, pd.concat([after, bars("NIFTY", auction, start="15:29", n=1)]))
    derived = DerivedStore(tmp_path / "derived")
    build_minutes(raw, derived)
    build_sessions(derived, {"closing_auction": {"start": "15:15", "since": "2026-08-03"}})
    sessions = derived.read("sessions").set_index("day")
    assert sessions.loc[regular, "kind"] == "regular"
    assert sessions.loc[auction, "kind"] == "regular"
    assert sessions.loc[missing_open, "kind"] == "regular"
    assert sessions.loc[short, "kind"] == "irregular"
    assert sessions.loc[weekend, "kind"] == "irregular"
    assert sessions.loc[late, "kind"] == "irregular"


def test_candles_stamped_mid_minute_are_put_on_their_minute(tmp_path):
    """UPL's 2019-2021 candles carry the last trade's second (09:15:58): each is still that minute's bar."""
    raw = Store(tmp_path / "raw")
    day = date(2019, 1, 1)
    t0 = datetime(2019, 1, 1, 9, 15, 58, tzinfo=IST)
    bars_ = pd.DataFrame({"ts": [t0, t0 + timedelta(minutes=1)], "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0,
                          "volume": 10, "target": "UPL"})
    raw.append_parquet("history_one_minute", day, bars_)
    derived = DerivedStore(tmp_path / "derived")
    build_minutes(raw, derived)
    stamps = sorted(derived.read("minutes")["ts"])
    assert stamps == [pd.Timestamp(datetime(2019, 1, 1, 9, 15, tzinfo=IST)), pd.Timestamp(datetime(2019, 1, 1, 9, 16, tzinfo=IST))]
