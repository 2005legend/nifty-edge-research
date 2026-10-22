from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from quantdesk.clock import IST
from quantdesk.pricing.clock import Clock
from quantdesk.pricing.precheck import candle_records, pick_contracts, run_precheck
from quantdesk.pricing.quotes import ModelQuotes
from quantdesk.pricing.surface import Surface
from quantdesk.validation.hypotheses import load_hypotheses

H = load_hypotheses()
DAY = date(2026, 10, 14)
EXPIRY = date(2026, 10, 20)


def master():
    rows = []
    for expiry in (EXPIRY, date(2026, 10, 27), date(2026, 11, 3), date(2026, 11, 10)):
        for strike in range(24800, 25250, 50):
            for side in ("CE", "PE"):
                rows.append({"name": "NIFTY", "instrumenttype": "OPTIDX", "exch_seg": "NFO", "expiry": expiry,
                             "strike": float(strike), "symbol": f"NIFTY{expiry:%d%b%y}{strike}{side}".upper(),
                             "token": f"{expiry:%m%d}{strike}{side}", "lotsize": 75, "tick_size": 0.05})
    return pd.DataFrame(rows)


def test_contracts_are_the_strikes_around_the_money_for_the_next_expiries():
    picked = pick_contracts(master(), "NIFTY", DAY, spot=25010.0, width=2, n_expiries=3)
    assert {c["expiry"] for c in picked} == {EXPIRY, date(2026, 10, 27), date(2026, 11, 3)}
    assert sorted({c["strike"] for c in picked}) == [24900.0, 24950.0, 25000.0, 25050.0, 25100.0]
    assert len(picked) == 3 * 5 * 2 and all(c["exchange"] == "NFO" for c in picked)


def _market():
    days = tuple(DAY + timedelta(d) for d in range(40) if (DAY + timedelta(d)).weekday() < 5)
    clock = Clock(np.full(375, 1 / 375), 0.3, 0.2, 0.2, days)
    surface = Surface(r_dte={d: 1.0 for d in range(10)}, b1=0.0, b2=0.0, floor=0.5, gamma_dn=0.0, gamma_up=0.0)
    ts = [datetime(2026, 10, 14, 9, 15, tzinfo=IST) + timedelta(minutes=i) for i in range(375)]
    close = 25000.0 + 40 * np.sin(np.arange(375) / 30.0)
    frame = pd.DataFrame({"ts": ts, "close": close, "vix": 13.0})
    return clock, surface, {"NIFTY": frame}


def test_candles_become_records_with_the_spot_of_their_minute():
    clock, surface, frames = _market()
    contract = {"token": "1", "underlying": "NIFTY", "expiry": EXPIRY, "strike": 25000.0, "side": "CE"}
    ts = frames["NIFTY"]["ts"][:3]
    candles = pd.DataFrame({"ts": ts, "open": 1.0, "high": 1.0, "low": 1.0, "close": [100.0, 101.0, 102.0],
                            "volume": 75, "token": "1"})
    rec = candle_records(candles, [contract], frames)
    assert list(rec["mid"]) == [100.0, 101.0, 102.0] and (rec["bid"] == rec["ask"]).all()
    assert rec["spot"].iloc[1] == pytest.approx(frames["NIFTY"]["close"].iloc[1])


def test_prices_the_model_itself_made_score_an_error_of_zero():
    clock, surface, frames = _market()
    quotes = ModelQuotes(frames, surface, clock, H)
    contract = {"token": "1", "underlying": "NIFTY", "expiry": EXPIRY, "strike": 25000.0, "side": "CE"}
    ts = list(frames["NIFTY"]["ts"][:-1])
    closes = [quotes.mid("NIFTY", EXPIRY, 25000.0, "CE", t + timedelta(minutes=1)) for t in ts]
    candles = pd.DataFrame({"ts": ts, "open": closes, "high": closes, "low": closes, "close": closes,
                            "volume": 75, "token": "1"})
    errors, summary = run_precheck(candles, [contract], frames, clock, surface, H)
    assert len(errors) > 0 and summary["median_error"] == pytest.approx(0.0, abs=1e-9)
    assert summary["by_horizon"]["15"] == pytest.approx(0.0, abs=1e-9) and summary["days"] == 1
