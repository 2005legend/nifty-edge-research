from datetime import date, datetime, timedelta

import pandas as pd
import pytest

from quantdesk.clock import IST
from quantdesk.derived.members import build_members_minute, member_breadth
from quantdesk.derived.store import DerivedStore
from quantdesk.validation.hypotheses import load_hypotheses, param

OPEN = datetime(2023, 1, 2, 9, 15, tzinfo=IST)
TOP_N = param(load_hypotheses(), "gate.breadth_top_n")


def bars(sym, closes, opens=None, vols=None, start=OPEN):
    n = len(closes)
    return pd.DataFrame({"target": sym, "ts": [start + timedelta(minutes=i) for i in range(n)],
                         "open": opens or closes, "high": closes, "low": closes, "close": closes,
                         "volume": vols or [100] * n})


def test_breadth_counts_traded_value_and_top5():
    day = pd.concat([bars("A", [10.0, 11.0]), bars("B", [20.0, 19.0]), bars("C", [5.0])])  # C trades once
    out = member_breadth(day, members={"A", "B", "C", "HDFC"}, prior_value={"A": 9e9, "B": 1e9, "C": 1.0},
                         top_n=TOP_N)
    second = out.iloc[1]
    assert second["members_total"] == 4 and second["members_present"] == 2   # HDFC has no data; C missing
    assert second["tv"] == 11.0 * 100 + 19.0 * 100
    assert (second["adv"], second["dec"]) == (1, 1)                           # A up, B down, C flat (carried)
    expected_top5 = (9e9 * (11 / 10 - 1) + 1e9 * (19 / 20 - 1) + 1.0 * 0) / (9e9 + 1e9 + 1.0)
    assert second["top5_ret"] == pytest.approx(expected_top5)


def test_a_late_start_minute_without_volume_counts_as_no_traded_value():
    """26 Oct 2026: the recorder started at 10:14, so each stock's first minute had no volume (pandas NA)."""
    day = bars("A", [10.0, 11.0], vols=[None, 100])
    day["volume"] = day["volume"].astype("Int64")
    out = member_breadth(day, members={"A"}, prior_value={"A": 1.0}, top_n=TOP_N)
    assert out.iloc[0]["tv"] == 0.0 and out.iloc[0]["above_vwap"] == 0
    assert out.iloc[1]["tv"] == pytest.approx(11.0 * 100) and out.iloc[1]["adv"] == 1


def test_a_member_without_data_is_counted_not_filled():
    out = member_breadth(bars("A", [10.0]), members={"A", "HDFC"}, prior_value={"A": 1.0}, top_n=TOP_N)
    assert out.iloc[0]["members_present"] == 1 and out.iloc[0]["members_total"] == 2


class TwoMembers:
    """A membership that never changes, so the test can pin the previous-session rule on its own."""

    def members_on(self, day):
        return {"A", "B"}

    def listing(self, symbol):
        return symbol

    def backfill_symbols(self):
        return ["A", "B"]


def test_the_top5_weights_come_from_the_previous_session(tmp_path):
    derived = DerivedStore(tmp_path)
    days = [date(2023, 1, 2), date(2023, 1, 3)]
    derived.write_frame("sessions", pd.DataFrame({"day": days, "kind": "regular", "bars": 2,
                                                  "first_bar": None, "last_bar": None}))
    minutes = pd.concat([
        bars("A", [10.0, 10.0]), bars("B", [20.0, 20.0], vols=[10, 10]),
        bars("A", [10.0, 11.0], start=OPEN + timedelta(days=1)),
        bars("B", [20.0, 20.0], vols=[10, 10], start=OPEN + timedelta(days=1)),
    ], ignore_index=True)
    minutes["day"] = [ts.date() for ts in minutes["ts"]]
    derived.write_frame("minutes", minutes)

    build_members_minute(derived, TwoMembers(), TOP_N)
    out = derived.read("members_minute")

    first, second = out[out["day"] == days[0]], out[out["day"] == days[1]]
    assert first["top5_ret"].isna().all()                       # nothing was traded before the first session
    # weights are the previous session's traded value: A 2 x 10 x 100, B 2 x 20 x 10
    assert second["top5_ret"].iloc[-1] == pytest.approx((2000 * 0.1 + 400 * 0.0) / 2400)
    last = second.iloc[-1]
    assert (last["members_total"], last["members_present"], last["adv"], last["above_vwap"]) == (2, 2, 1, 1)
    assert last["available_at"] == last["ts"] + pd.Timedelta(minutes=1)
    assert list(out.columns) == ["ts", "members_total", "members_present", "tv", "adv", "dec",
                                 "above_vwap", "top5_ret", "day", "available_at"]
