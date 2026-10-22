from datetime import date, datetime, time, timedelta

import pandas as pd
import pytest

from quantdesk.analysis.macro import (event_block, event_delta, hard_exit, macro_raw, stress_delta, stress_score,
                                      timed_event_exits, vix_block)
from quantdesk.calendar.events import Event
from quantdesk.clock import IST
from quantdesk.validation.hypotheses import load_hypotheses

H = load_hypotheses()
RBI = Event(date(2024, 4, 5), time(10, 0), "rbi_mpc", "E2", "RBI", "https://x")
UNSCHEDULED = Event(date(2022, 5, 4), time(14, 0), "rbi_mpc", "E2", "RBI", "https://x", scheduled=False)
BUDGET = Event(date(2024, 7, 23), time(11, 0), "budget", "E2", "Budget", "https://x")
ELECTION = Event(date(2024, 6, 4), None, "election_results", "E3", "Results", "https://x")
REBALANCE = Event(date(2024, 9, 27), None, "index_rebalance", "E1", "Rebalance", "https://x")


def at(d, hh, mm):
    return datetime.combine(d, time(hh, mm), tzinfo=IST)


def test_rbi_blocks_entries_for_45_minutes():
    assert event_block((RBI,), at(RBI.date, 10, 30), H) == "rbi_wait"
    assert event_block((RBI,), at(RBI.date, 10, 45), H) is None


def test_unscheduled_events_never_block_from_the_calendar():
    assert event_block((UNSCHEDULED,), at(UNSCHEDULED.date, 14, 15), H) is None


def test_budget_blocks_until_13_00_and_raises_the_hurdle():
    assert event_block((BUDGET,), at(BUDGET.date, 12, 45), H) == "budget_wait"
    assert event_block((BUDGET,), at(BUDGET.date, 13, 0), H) is None
    assert event_delta((BUDGET,), H) == pytest.approx(0.04) and event_delta((RBI,), H) == 0.0


def test_election_day_is_no_trade():
    assert event_block((ELECTION,), at(ELECTION.date, 13, 0), H) == "E3"


def test_hard_exit_is_15_00_on_expiry_and_rebalance_days():
    assert hard_exit(date(2024, 3, 5), False, (), H) == time(15, 10)
    assert hard_exit(date(2024, 3, 7), True, (), H) == time(15, 0)
    assert hard_exit(REBALANCE.date, False, (REBALANCE,), H) == time(15, 0)


def test_timed_scheduled_events_force_an_exit_five_minutes_before():
    assert timed_event_exits((RBI, UNSCHEDULED), RBI.date) == [at(RBI.date, 9, 55)]


def test_vix_block():
    assert vix_block(15.3, 14.0, 0.08) and not vix_block(15.0, 14.0, 0.08)


def stress_fixture(brent, usdinr, dgs10=None, gsec=None, dxy=None, end=date(2024, 3, 11)):
    rows = []
    for sid, values in (("brent", brent), ("usdinr", usdinr), ("dgs10", dgs10), ("india_gsec10y_price", gsec),
                        ("dxy", dxy)):
        for i, v in enumerate(values or []):
            rows.append({"series_id": sid, "date": end - timedelta(days=len(values) - 1 - i), "value": v})
    return pd.DataFrame(rows)


def test_stress_points():
    macro = stress_fixture(brent=[90, 90, 90, 90, 90, 100.0], usdinr=[83.0] * 5 + [84.3])
    assert stress_score(macro, date(2024, 3, 11)) == 1 + 2 + 2      # brent>=95, brent 5d +11%, inr 5d +1.6%


def test_stress_rates_and_dollar():
    macro = stress_fixture(brent=[80.0] * 6, usdinr=[83.0] * 6, dgs10=[4.0] * 5 + [4.2],
                           gsec=[100.0] * 5 + [98.5], dxy=[100.0] * 5 + [101.6])
    # US 10y +20bp: 1; India 10y: dy = 1.5% / 7 = 21bp: 1; DXY +1.6%: 1
    assert stress_score(macro, date(2024, 3, 11)) == 3


def test_stress_tiers_and_the_cap_before_rv1():
    assert [stress_delta(s, True, H) for s in (2, 3, 4, 5, 8)] == [0.0, 0.02, 0.02, 0.04, 0.04]
    assert stress_delta(6, False, H) == 0.02


def test_macro_raw_fades_a_post_holiday_gap_and_follows_an_fii_flip():
    flips = pd.Series([0.45, 0.47, 0.52])        # crossed 0.5 within the window -> +1
    assert macro_raw(holiday_before=True, r_on=0.004, fii_ratios=flips, window=5) == -1 + 1
    assert macro_raw(holiday_before=False, r_on=0.004, fii_ratios=pd.Series([0.6, 0.62]), window=5) == 0
