from datetime import date, datetime, time, timedelta

import numpy as np
import pandas as pd
import pytest

from quantdesk.clock import IST
from quantdesk.live.source import LiveDaySource, RecordedQuotes
from quantdesk.strategy.daycard import DayLoader
from quantdesk.validation.hypotheses import load_hypotheses
from tests.derived_fixture import build, clock_for, flat_surface

H = load_hypotheses()


class OneMember:
    def members_on(self, day):
        return {"AAA", "BBB"}

    def listing(self, s):
        return s


def recorder_day(day, n=60):
    t0 = datetime.combine(day, time(9, 15), tzinfo=IST)
    ts = [t0 + timedelta(minutes=i) for i in range(n)]
    rows = []
    for token, base in (("99926000", 22100.0), ("99926017", 14.0), ("1", 100.0), ("2", 200.0)):
        for i, t in enumerate(ts):
            c = base * (1 + 0.0001 * i)
            rows.append({"minute": t, "token": token, "open": c, "high": c, "low": c, "close": c,
                         "volume": 0 if token.startswith("999") else 100})
    bars = pd.DataFrame(rows)
    snaps = pd.DataFrame({"minute": ts, "token": "555", "bid": 80.0, "ask": 80.5})
    return bars, snaps


@pytest.fixture(scope="module")
def live(tmp_path_factory):
    derived, days = build(tmp_path_factory.mktemp("d"), n_days=30)
    today = list(pd.bdate_range(days[-1] + timedelta(days=1), periods=1).date)[0]
    loader = DayLoader(derived, clock_for(days + [today]), flat_surface(), H, events=[])
    bars, snaps = recorder_day(today)
    expiry = loader.expiries.loc[("NIFTY", days[-1]), "expiry_1"]
    expiry = expiry if expiry >= today else loader.expiries.loc[("NIFTY", days[-1]), "expiry_2"]
    meta = pd.DataFrame({"token": ["555"], "underlying": ["NIFTY"], "expiry": [expiry], "strike": [22100.0],
                         "side": ["CE"], "subscribed_at": [datetime.combine(today, time(9, 0), tzinfo=IST)]})
    source = LiveDaySource(loader, today, bars, snaps, meta, {"1": "AAA", "2": "BBB"}, OneMember(), H)
    return source, today, expiry


def test_today_is_a_session_with_the_recorded_open_and_expiries(live):
    source, today, expiry = live
    ctx = source.context("NIFTY", today)
    assert ctx.day == today and ctx.open == pytest.approx(22100.0) and ctx.expiry_1 >= today
    assert today in source.loader.days and ctx.prev_close == pytest.approx(source.loader.daily["NIFTY"]["close"].iloc[-2])


def test_the_live_frame_has_vwap_and_breadth_from_the_recorder(live):
    source, today, _ = live
    ctx = source.context("NIFTY", today)
    frame = source.frame(ctx)
    assert len(frame) == 60 and frame["vwap"].notna().all() and frame["adv_share"].iloc[-1] == pytest.approx(1.0)


def test_quotes_are_the_recorded_bid_and_ask(live):
    source, today, expiry = live
    ctx = source.context("NIFTY", today)
    frame = source.frame(ctx)
    quotes = source.helpers(ctx, frame).quotes
    q = quotes.quote("NIFTY", expiry, 22100.0, "CE", datetime.combine(today, time(9, 45), tzinfo=IST))
    assert (q.bid, q.ask) == (80.0, 80.5)
    model = quotes.quote("NIFTY", expiry, 22200.0, "CE", datetime.combine(today, time(9, 45), tzinfo=IST))
    assert model.ask > model.bid > 0                     # no recorded token: the model fills in
