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
    """The backtest starts in 2019; nothing earlier is sourced, so a backtest must not silently guess."""
    with pytest.raises(UnknownChargeSchedule):
        round_trip(60, 60, 65, exchange="NSE", day=date(2018, 12, 31))


@pytest.mark.parametrize("day, stt, nse, bse", [
    # Zerodha bulletins: 1 Apr 2023 (STT 0.05 -> 0.0625%, NSE 0.053 -> 0.05%), 1 Apr 2024 (NSE 0.05 -> 0.0495%),
    # 1 Oct 2024 (STT -> 0.1%, NSE -> 0.03503%, BSE -> 0.0325%); Budget 2026 (STT -> 0.15% from 1 Apr 2026)
    (date(2019, 1, 2), 0.0005, 0.00053, 0.000495),
    (date(2023, 3, 31), 0.0005, 0.00053, 0.000495),
    (date(2023, 4, 3), 0.000625, 0.0005, 0.000495),
    (date(2024, 4, 1), 0.000625, 0.000495, 0.000495),
    (date(2024, 10, 1), 0.001, 0.0003503, 0.000325),
    (date(2026, 4, 1), 0.0015, 0.0003553, 0.000325),
])
def test_historical_rates_switch_on_their_effective_dates(day, stt, nse, bse):
    from quantdesk.costs import schedule_for

    schedule = schedule_for(day)
    assert (schedule.stt_sell, schedule.exchange["NSE"], schedule.exchange["BSE"]) == (stt, nse, bse)


def test_unknown_exchange_is_rejected():
    with pytest.raises(ValueError):
        round_trip(60, 60, 65, exchange="MCX", day=DAY)
