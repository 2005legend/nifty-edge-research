from datetime import datetime, timedelta

import numpy as np
import pytest

from quantdesk.clock import IST
from quantdesk.live.monitor import cusum_alarm
from quantdesk.live.run import (cusum_threshold, kill_params, rebuild_on_change, run_loop, set_env_value,
                                verdict_mode)

START = datetime(2026, 10, 23, 9, 10, tzinfo=IST)


def test_mode_comes_from_the_verdict_file(tmp_path):
    assert verdict_mode(tmp_path) == "shadow"
    (tmp_path / "VERDICT.md").write_text("# SP2 verdict: **alert-off**\n")
    assert verdict_mode(tmp_path) == "shadow"
    (tmp_path / "VERDICT.md").write_text("# SP2 verdict: **alert-on**\n")
    assert verdict_mode(tmp_path) == "live"


def _run_length(r, target, k, h, rng, cap=5000):
    draws = rng.choice(r, size=cap)
    s = 0.0
    for i, x in enumerate(draws):
        s = max(0.0, s + (target - x) - k)
        if s > h:
            return i + 1
    return cap


def test_the_cusum_threshold_gives_about_one_false_alarm_per_250_trades():
    r = np.random.default_rng(1).normal(0.3, 1.5, 400)
    target, k = 0.3 - 0.5 * 0.3, 0.5 * 0.5 * 0.3
    h = cusum_threshold(r, target, k, arl=250, paths=400, seed=0)
    rng = np.random.default_rng(99)
    arl = np.mean([_run_length(r, target, k, h, rng) for _ in range(400)])
    assert 180 <= arl <= 350
    assert not cusum_alarm(np.full(50, r.mean()), target, k, h)


def test_kill_params_come_from_the_validated_trades():
    r = np.random.default_rng(2).normal(0.4, 1.2, 300)
    p = kill_params(r)
    assert p["mu0"] == pytest.approx(r.mean()) and p["sigma"] == pytest.approx(r.std(ddof=1))
    assert p["breakeven"] == 0.0 and p["cusum_h"] > 0


def test_the_source_is_rebuilt_only_when_the_recorder_files_change():
    keys = iter([3, 3, 4])
    built = []
    make = rebuild_on_change(lambda now: next(keys), lambda now: built.append(now) or len(built))
    assert make(START) == 1 and make(START + timedelta(seconds=5)) == 1
    assert make(START + timedelta(seconds=10)) == 2 and len(built) == 2


def test_the_loop_waits_for_the_start_steps_until_the_end_and_survives_errors():
    clock = {"now": START - timedelta(minutes=2)}
    steps, errors = [], []

    def step(now):
        steps.append(now)
        if len(steps) == 3:
            raise ValueError("bad bar")

    def sleep(seconds):
        clock["now"] += timedelta(seconds=seconds)

    n = run_loop(step, lambda: clock["now"], sleep, START, START + timedelta(minutes=1), every=5,
                 on_error=lambda now, exc: errors.append(str(exc)))
    assert steps[0] >= START and steps[-1] <= START + timedelta(minutes=1)
    assert n == len(steps) == 13 and errors == ["bad bar"]


def test_env_values_are_replaced_or_appended_without_touching_other_lines(tmp_path):
    env = tmp_path / ".env"
    env.write_text("A=1\nTELEGRAM_CHAT_ID=old\nB=2\n", encoding="utf-8")
    set_env_value(env, "TELEGRAM_CHAT_ID", "12345")
    assert env.read_text(encoding="utf-8") == "A=1\nTELEGRAM_CHAT_ID=12345\nB=2\n"
    set_env_value(env, "NEW", "x")
    assert env.read_text(encoding="utf-8").endswith("B=2\nNEW=x\n")


def test_the_cap_calendar_is_the_whole_year():
    from datetime import date

    from quantdesk.calendar.events import Event
    from quantdesk.live.run import year_sessions

    days = year_sessions(date(2026, 3, 10), [Event(date(2026, 12, 25), None, "holiday_nse", "none", "Christmas", "")])
    assert days[0] == date(2026, 1, 1) and days[-1] == date(2026, 12, 31) and date(2026, 12, 25) not in days
