from datetime import date, datetime, timedelta

import pandas as pd

from quantdesk.clock import IST
from quantdesk.recorder.bars import BAR_COLUMNS
from quantdesk.recorder.catchup import catch_up
from quantdesk.storage import Store

DAY = date(2026, 10, 26)
OPEN = datetime(2026, 10, 26, 9, 15, tzinfo=IST)


class Candles:
    def __init__(self, fail=()):
        self.asked, self.fail = [], set(fail)

    def candles(self, exchange, token, interval, start, end):
        self.asked.append((exchange, token, interval, start, end))
        if token in self.fail:
            raise ConnectionError("candle API down")
        ts = pd.date_range(OPEN, end, freq="1min", tz=IST)          # the API also returns the current minute
        return pd.DataFrame({"ts": ts, "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.5,
                             "volume": 0 if token.startswith("999") else 500})


def test_a_late_start_fetches_the_missed_minutes_as_recorded_bars(tmp_path):
    store, client = Store(tmp_path), Candles(fail={"2885"})
    now = datetime(2026, 10, 26, 10, 14, 30, tzinfo=IST)
    n = catch_up(client, store, DAY, [("NSE", "99926000"), ("NSE", "1922"), ("NSE", "2885")], OPEN, now)
    bars = store.read("bars", DAY)
    assert list(bars.columns[: len(BAR_COLUMNS)]) == BAR_COLUMNS
    assert set(bars["token"]) == {"99926000", "1922"}                      # a failing token is skipped
    assert bars["minute"].min() == OPEN and bars["minute"].max() == datetime(2026, 10, 26, 10, 13, tzinfo=IST)
    assert n == len(bars) == 2 * 59 and client.asked[0][2] == "ONE_MINUTE"
    assert (bars.loc[bars["token"] == "1922", "volume"] == 500).all()


def test_an_on_time_start_fetches_nothing(tmp_path):
    client = Candles()
    assert catch_up(client, Store(tmp_path), DAY, [("NSE", "99926000")], OPEN, OPEN + timedelta(seconds=50)) == 0
    assert client.asked == []
