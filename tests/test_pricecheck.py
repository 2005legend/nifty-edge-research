from datetime import date, datetime, timedelta

import pandas as pd
import pytest

from quantdesk.clock import IST
from quantdesk.pricing.pricecheck import check_result, price_errors
from quantdesk.validation.hypotheses import load_hypotheses

H = load_hypotheses()
DAY = date(2026, 10, 27)


def recorded(mids):
    """One NIFTY call, snapshots every minute from 09:30, mid = bid/ask midpoint; spot 22000 throughout."""
    start = datetime.combine(DAY, datetime.min.time(), tzinfo=IST) + timedelta(hours=9, minutes=30)
    rows = [{"minute": start + timedelta(minutes=i), "token": "1", "bid": m - 0.5, "ask": m + 0.5, "spot": 22000.0,
             "underlying": "NIFTY", "expiry": date(2026, 10, 27), "strike": 22000.0, "side": "CE"}
            for i, m in enumerate(mids)]
    return pd.DataFrame(rows)


def mid_lookup(frame):
    table = {(r.minute + timedelta(minutes=1)): (r.bid + r.ask) / 2 for r in frame.itertuples()}
    return lambda index, expiry, strike, kind, at: table[at]


def test_a_perfect_model_has_zero_error():
    rec = recorded([100.0 + 0.1 * i for i in range(360)])
    errors = price_errors(rec, mid_lookup(rec), horizons=[15, 30, 60, "exit"], is_expiry_day={DAY: True})
    assert len(errors) > 0 and errors["err"].median() == 0.0


def test_errors_use_a_two_tick_floor():
    rec = recorded([100.0] * 360)                                    # the market did not move
    model = lambda index, expiry, strike, kind, at: 100.0 + (0.05 if at.minute == 0 and at.hour == 10 else 0.0)
    errors = price_errors(rec, model, horizons=[15], is_expiry_day={DAY: False})
    row = errors[(errors.check == datetime(2026, 10, 27, 9, 45, tzinfo=IST))].iloc[0]
    assert row["err"] == pytest.approx(0.05 / 0.10)


def test_too_few_sessions_is_not_a_pass():
    errors = pd.DataFrame({"err": [0.0] * 50})
    out = check_result(errors, {"NIFTY": {"sessions": 10, "expiry_days": 2}, "SENSEX": {"sessions": 10, "expiry_days": 2}}, H)
    assert out["enough_data"] is False and out["passed"] is False and out["median_error"] == 0.0


def test_enough_data_and_a_small_error_passes():
    errors = pd.DataFrame({"err": [0.1] * 50})
    out = check_result(errors, {"NIFTY": {"sessions": 15, "expiry_days": 4}, "SENSEX": {"sessions": 16, "expiry_days": 4}}, H)
    assert out["passed"] is True
