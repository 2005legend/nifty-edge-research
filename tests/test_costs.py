from datetime import date

import pytest

from quantdesk.costs import UnknownChargeSchedule, round_trip

DAY = date(2026, 10, 21)


@pytest.mark.parametrize("buy, sell, qty, exchange, total", [
    # research_notes/Nifty options multifactor quant strategy/option_trade_construction.md §10
    (60, 60, 65, "NSE", 56.60),    # Nifty, flat exit
    (60, 74, 65, "NSE", 57.98),    # Nifty, target
    (60, 52, 65, "NSE", 55.38),    # Nifty, stop
    (200, 200, 20, "BSE", 56.40),  # Sensex, flat exit
    (200, 245, 20, "BSE", 57.74),  # Sensex, target
])
def test_round_trip_matches_worked_examples(buy, sell, qty, exchange, total):
    assert round_trip(buy, sell, qty, exchange=exchange, day=DAY).total == pytest.approx(total, abs=0.01)


def test_components_of_the_nifty_flat_example():
    c = round_trip(60, 60, 65, exchange="NSE", day=DAY)
    assert c.brokerage == 40.0
    assert c.stt == 6          # round(0.0015 x 3900 = 5.85), half up
    assert c.exchange == pytest.approx(2.77, abs=0.005)
    assert c.stamp == pytest.approx(0.12, abs=0.005)
    assert c.gst == pytest.approx(7.70, abs=0.005)


def test_stt_rounds_half_up_not_to_even():
    # sell 3 x 1000 = 3000 -> STT 0.0015 x 3000 = 4.5 -> 5 (Python's round() would give 4)
    assert round_trip(3, 3, 1000, exchange="NSE", day=DAY).stt == 5


def test_dates_before_the_earliest_sourced_schedule_raise():
    """Older STT and exchange rates are not sourced yet; a backtest must not silently use today's."""
    with pytest.raises(UnknownChargeSchedule):
        round_trip(60, 60, 65, exchange="NSE", day=date(2026, 3, 31))


def test_unknown_exchange_is_rejected():
    with pytest.raises(ValueError):
        round_trip(60, 60, 65, exchange="MCX", day=DAY)
