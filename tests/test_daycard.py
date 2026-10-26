import math
from datetime import timedelta

import numpy as np
import pytest

from quantdesk.strategy.daycard import DayLoader
from quantdesk.validation.hypotheses import load_hypotheses
from tests.derived_fixture import build, clock_for, flat_surface

H = load_hypotheses()


@pytest.fixture(scope="module")
def loader(tmp_path_factory):
    derived, days = build(tmp_path_factory.mktemp("d"), n_days=30)
    return DayLoader(derived, clock_for(days), flat_surface(), H, events=[]), days


def test_the_day_card_uses_only_what_was_known_by_0916(loader):
    dl, days = loader
    day = days[-1]
    ctx = dl.day_context("NIFTY", day)
    assert ctx.prev_close == pytest.approx(dl.daily["NIFTY"].loc[days[-2], "close"])
    assert ctx.open == pytest.approx(float(dl.bars("NIFTY", day)["open"].iloc[0]))   # the first bar, not daily
    assert ctx.expiry_1 >= day and ctx.lot_1 == 50
    assert ctx.har_pct is None                       # far fewer than 60 earlier forecasts
    assert ctx.session_kind == "regular" and ctx.hard_exit.hour == 15


def test_the_band_needs_fourteen_earlier_sessions_of_the_same_type(loader):
    dl, days = loader
    early, late = dl.band_sigma("NIFTY", days[5]), dl.band_sigma("NIFTY", days[-1])
    assert np.isnan(early).all()
    nonexpiry_before = [d for d in days[:-1] if not dl.is_expiry_day("NIFTY", d)]
    assert len(nonexpiry_before) >= 14 and not np.isnan(late[30])


def test_tampering_with_the_days_daily_open_does_not_move_the_context(loader):
    dl, days = loader
    day = days[-1]
    before = dl.day_context("NIFTY", day).open
    dl.daily["NIFTY"].loc[day, "open"] = 999.0
    assert dl.day_context("NIFTY", day).open == before


def test_minute_frame_has_vwap_bands_and_breadth(loader):
    dl, days = loader
    ctx = dl.day_context("NIFTY", days[-1])
    frame = dl.minute_frame(ctx)
    assert len(frame) == 375 and frame["vwap"].notna().all() and frame["upper"].iloc[60] > frame["lower"].iloc[60]
    assert frame["adv_share"].notna().all() and frame["atm_premium"].iloc[30] > 0


def test_z_refs_use_earlier_sessions_only(loader):
    dl, days = loader
    refs = dl.z_refs("NIFTY", days[-1])
    ref = refs[("adv_share", "10:00")]
    assert ref.n == len(days) - 1
    dl.record_signal(days[-1], {"loc_vwap": 1.0, "loc_level": 2.0})
    assert ("loc_vwap", "*") not in dl.z_refs("NIFTY", days[-1])         # a same-day signal is not a reference
    assert dl.z_refs("NIFTY", days[-1] + timedelta(days=1)).get(("loc_vwap", "*")).n == 1


def test_one_missing_breadth_value_does_not_poison_a_years_reference(loader):
    """2021: one NaN top5_ret in the 250-session window made the mean NaN, so no 2021 signal had a technical score."""
    dl, days = loader
    real = dl.breadth_at_checks

    def with_a_gap(day):
        out = dict(real(day))
        if day == days[3]:
            out[("adv_share", "10:00")] = float("nan")
        return out

    dl.breadth_at_checks = with_a_gap
    ref = dl.z_refs("NIFTY", days[-1])[("adv_share", "10:00")]
    assert ref.n == len(days) - 2 and ref.mean == ref.mean and ref.sd == ref.sd      # NaN-free, one fewer value
    dl.breadth_at_checks = real


def test_the_spike_reference_needs_fourteen_earlier_sessions(loader):
    dl, days = loader
    assert dl.day_context("NIFTY", days[10]).spike_ref is None
    ref = dl.day_context("NIFTY", days[-1]).spike_ref
    assert ref is not None and np.nanmedian(ref[1:]) > 0
