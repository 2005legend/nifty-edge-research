from datetime import date, timedelta

import pandas as pd
import pytest

from quantdesk.backtest.dataset import build_dataset
from quantdesk.backtest.engine import NoTicketError, month_quota, run_trial_split
from quantdesk.strategy.configs import config_for
from quantdesk.strategy.meta import Consensus
from quantdesk.validation.hypotheses import load_hypotheses
from quantdesk.validation.registry import TrialTicket
from tests.test_dataset import FakeSource
from tests.test_pipeline import AT, DAY, TODAY

H = load_hypotheses()
TICKET = TrialTicket("B0", 1, "now", "abc", "h", "d", 1)
SESSIONS = list(pd.bdate_range("2024-01-01", "2024-12-31").date)


def dataset_with_a_second_signal():
    source = FakeSource()
    ds = build_dataset(source, [DAY], {"NIFTY": DAY}, H, TODAY)
    first = ds.signals.iloc[0]
    later = first.copy()
    later["signal_id"], later["at"] = "NIFTY-later", first["at"] + timedelta(minutes=15)
    ds.signals = pd.concat([ds.signals, later.to_frame().T], ignore_index=True)
    extra = ds.candidates.copy()
    extra["signal_id"] = "NIFTY-later"
    ds.candidates = pd.concat([ds.candidates, extra], ignore_index=True)
    return ds, source


def test_no_pnl_without_a_ticket():
    ds, source = dataset_with_a_second_signal()
    with pytest.raises(NoTicketError):
        run_trial_split(ds, {DAY}, config_for("B0", {}), Consensus(0, 0), source, H, TODAY, 0, None, SESSIONS)


def test_one_trade_a_day_and_the_rest_are_capped_with_zero_r():
    ds, source = dataset_with_a_second_signal()
    trades = run_trial_split(ds, {DAY}, config_for("B0", {}), Consensus(0, 0), source, H, TODAY, 0, TICKET, SESSIONS)
    by_id = trades.set_index("signal_id")
    first = ds.signals.iloc[0]["signal_id"]
    assert by_id.loc[first, "status"] == "filled" and by_id.loc["NIFTY-later", "status"] == "cap"
    assert by_id.loc["NIFTY-later", "r"] == 0.0 and by_id.loc[first, "r"] == pytest.approx(by_id.loc[first, "pnl"] / 400)


def test_a_failed_gate_is_a_zero_r_row():
    ds, source = dataset_with_a_second_signal()
    ds.signals.loc[ds.signals["signal_id"] == "NIFTY-later", "failed"] = "room_to_run"
    trades = run_trial_split(ds, {DAY}, config_for("B0", {}), Consensus(0, 0), source, H, TODAY, 0, TICKET, SESSIONS)
    assert trades.set_index("signal_id").loc["NIFTY-later", "status"] == "room_to_run"


def test_month_quota_is_pro_rata_of_100():
    days = SESSIONS
    march = [d for d in days if d.month == 3]
    assert month_quota(date(2024, 3, 5), days, 100) == -(-100 * len(march) // len(days))
