from datetime import datetime

import pandas as pd
import pytest

from quantdesk.analysis.vwap import vwap_proxy
from quantdesk.clock import IST


def test_vwap_weights_index_typical_price_by_member_traded_value():
    ts = [datetime(2024, 3, 4, 9, 15 + i, tzinfo=IST) for i in range(3)]
    bars = pd.DataFrame({"ts": ts, "high": [101.0, 103.0, 105.0], "low": [99.0, 101.0, 103.0],
                         "close": [100.0, 102.0, 104.0]})
    out = vwap_proxy(bars, pd.Series([1.0, 3.0, 0.0], index=ts))
    assert out["vwap"].tolist() == pytest.approx([100.0, (100 + 3 * 102) / 4, (100 + 3 * 102) / 4])
    assert out["vwap_sd"].iloc[1] == pytest.approx(((1 * (100 - 101.5) ** 2 + 3 * (102 - 101.5) ** 2) / 4) ** 0.5)


def test_no_traded_value_at_the_open_falls_back_to_the_typical_price():
    ts = [datetime(2024, 3, 4, 9, 15, tzinfo=IST), datetime(2024, 3, 4, 9, 16, tzinfo=IST)]
    bars = pd.DataFrame({"ts": ts, "high": [101.0, 104.0], "low": [99.0, 102.0], "close": [100.0, 103.0]})
    out = vwap_proxy(bars, pd.Series(dtype=float))
    assert out["vwap"].tolist() == [100.0, 100.0] and out["vwap_sd"].tolist() == [0.0, 0.0]
