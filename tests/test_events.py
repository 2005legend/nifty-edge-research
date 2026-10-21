from datetime import date
from pathlib import Path

import pytest

from quantdesk.calendar.events import (
    EventValidationError,
    events_on,
    is_trading_day,
    load_events,
    trading_days,
)
from quantdesk.config import project_root

GOOD = '  - {date: "2026-10-20", time: null, type: holiday_nse, gate: E3, title: "Dussehra", source_url: "https://www.nseindia.com/x"}\n'


def write(tmp_path, body):
    path = tmp_path / "events.yaml"
    path.write_text("events:\n" + body, encoding="utf-8")
    return path


def test_missing_source_url_rejected_with_all_errors_listed(tmp_path):
    body = (GOOD
            + '  - {date: "2026-10-21", time: null, type: rbi_mpc, gate: E2, title: "A"}\n'
            + '  - {date: "2026-13-40", time: null, type: nonsense, gate: E9, title: "B", source_url: "http://x"}\n')
    with pytest.raises(EventValidationError) as err:
        load_events(write(tmp_path, body))
    message = str(err.value)
    assert "'A'" in message and "source_url" in message
    assert "'B'" in message and "type" in message and "gate" in message and "date" in message


def test_weekend_and_holiday_not_trading(tmp_path):
    events = load_events(write(tmp_path, GOOD))
    assert is_trading_day(date(2026, 10, 17), events) is False   # Saturday
    assert is_trading_day(date(2026, 10, 20), events) is False   # listed NSE holiday
    assert is_trading_day(date(2026, 10, 21), events) is True
    assert is_trading_day(date(2026, 10, 20), events, exchange="BSE") is False  # falls back to NSE list


def test_history_days_authoritative_for_past(tmp_path):
    events = load_events(write(tmp_path, GOOD))
    days = trading_days(date(2026, 10, 12), date(2026, 10, 16), events,
                        history_days={date(2026, 10, 12), date(2026, 10, 13), date(2026, 10, 15), date(2026, 10, 16)})
    assert date(2026, 10, 14) not in days
    assert days == [date(2026, 10, 12), date(2026, 10, 13), date(2026, 10, 15), date(2026, 10, 16)]


def test_events_on_returns_matching(tmp_path):
    events = load_events(write(tmp_path, GOOD))
    assert [e.title for e in events_on(date(2026, 10, 20), events)] == ["Dussehra"]


def test_seed_file_is_valid():
    events = load_events(project_root() / "config" / "events.yaml")
    assert any(e.type == "holiday_nse" for e in events)
    assert is_trading_day(date(2026, 11, 24), events) is False


def test_continuous_session_stops_at_closing_auction_from_3_aug_2026():
    """Live candles on 19 Oct 2026: Nifty 1-minute bars stop at 15:14, then a single 15:29 close bar."""
    from datetime import time

    from quantdesk.calendar.events import continuous_session
    from quantdesk.config import load_settings

    session = load_settings()["session"]
    assert continuous_session(date(2026, 10, 19), session) == (time(9, 15), time(15, 15))
    assert continuous_session(date(2026, 8, 3), session) == (time(9, 15), time(15, 15))
    assert continuous_session(date(2026, 7, 31), session) == (time(9, 15), time(15, 30))


def test_history_file_is_valid_and_marks_off_cycle_moves_unscheduled():
    events = load_events(project_root() / "config" / "events_history.yaml")
    off_cycle = {e.date for e in events if not e.scheduled}
    assert off_cycle == {date(2020, 3, 27), date(2020, 5, 22), date(2022, 5, 4)}
    assert all(e.announced_on == e.date for e in events if not e.scheduled)
    assumed = [e for e in events if e.time_assumed]
    assert assumed and all(e.time.hour == 12 for e in assumed)


def test_new_event_fields_default_to_a_scheduled_known_time(tmp_path):
    path = tmp_path / "e.yaml"
    path.write_text("events:\n  - {date: 2026-10-07, time: '10:00', type: rbi_mpc, gate: E2, title: RBI, "
                    "source_url: 'https://rbi.org.in'}\n")
    (event,) = load_events(path)
    assert event.scheduled and event.announced_on is None and not event.time_assumed
