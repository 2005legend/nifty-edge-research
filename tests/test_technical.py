from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from quantdesk.analysis.technical import technical_raw, technical_score
from quantdesk.analysis.zscore import causal_z, z_refs_for
from quantdesk.clock import IST
from quantdesk.strategy.types import Signal, ZRef
from quantdesk.validation.hypotheses import load_hypotheses

H = load_hypotheses()


def test_causal_z_uses_only_the_reference_and_winsorises():
    assert causal_z(3.0, ZRef(1.0, 1.0, 100), min_n=60, winsor=3.0) == 2.0
    assert causal_z(10.0, ZRef(0.0, 1.0, 100), min_n=60, winsor=3.0) == 3.0
    assert causal_z(1.0, ZRef(0.0, 1.0, 59), min_n=60, winsor=3.0) is None
    assert causal_z(1.0, None, min_n=60, winsor=3.0) is None
    assert causal_z(1.0, ZRef(0.0, 0.0, 100), min_n=60, winsor=3.0) is None


def test_z_refs_keep_the_last_window_sessions():
    hist = pd.DataFrame({"day": pd.date_range("2024-01-01", periods=300).date, "check": "10:00",
                         "feature": "adv_share", "value": np.arange(300.0)})
    ref = z_refs_for(hist, window=250)[("adv_share", "10:00")]
    assert ref.n == 250 and ref.mean == pytest.approx(np.arange(50.0, 300.0).mean())
    assert ref.sd == pytest.approx(np.arange(50.0, 300.0).std(ddof=1))


SIG_LONG = Signal("NIFTY", datetime(2024, 3, 4, 10, 0, tzinfo=IST), "long", 100.5, 100.2, 99.8, 100.1, 100.2, 0.3, 101.19)


def test_technical_raw_is_long_aligned_and_flips_for_shorts():
    row = pd.Series({"close": 100.5, "vwap": 100.1, "adv_share": 0.2, "above_share": 0.7, "top5_ret": 0.001})
    raw = technical_raw(row, SIG_LONG, nearest_dist=0.6)
    assert raw == pytest.approx({"loc_vwap": 0.4 / 0.3, "loc_level": 2.0, "adv_share": 0.2,
                                 "above_share": 0.2, "top5_ret": 0.001})
    short = Signal(**{**SIG_LONG.__dict__, "side": "short"})
    assert technical_raw(row, short, nearest_dist=0.6)["adv_share"] == -0.2


def test_technical_score_is_the_mean_of_location_and_confirmation():
    refs = {(f, "10:00"): ZRef(0.0, 1.0, 100) for f in ("loc_vwap", "loc_level", "adv_share", "above_share", "top5_ret")}
    raw = {"loc_vwap": 1.0, "loc_level": 3.0, "adv_share": 0.0, "above_share": 0.3, "top5_ret": 0.6}
    assert technical_score(raw, refs, "10:00", H) == pytest.approx(((1.0 + 3.0) / 2 + (0.0 + 0.3 + 0.6) / 3) / 2)


def test_an_undefined_z_makes_the_score_undefined():
    refs = {(f, "10:00"): ZRef(0.0, 1.0, 10) for f in ("loc_vwap", "loc_level", "adv_share", "above_share", "top5_ret")}
    raw = {"loc_vwap": 1.0, "loc_level": 3.0, "adv_share": 0.0, "above_share": 0.3, "top5_ret": 0.6}
    assert technical_score(raw, refs, "10:00", H) is None


def test_no_level_in_reach_caps_the_level_feature():
    row = pd.Series({"close": 100.5, "vwap": 100.1, "adv_share": 0.2, "above_share": 0.7, "top5_ret": 0.001})
    assert technical_raw(row, SIG_LONG, nearest_dist=np.inf)["loc_level"] == 3.0
