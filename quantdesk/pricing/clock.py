"""The business-time clock (design §7, R15): one regular session is 1.0 unit of time.

An Indian index option does not age in calendar time. Almost nothing happens overnight except a jump, a
weekend day counts for less than a session, and inside a session the opening and closing minutes carry far
more variance than lunchtime. The clock turns two moments into the amount of market time between them, and
that is the T Black-76 sees: sigma_bt is quoted per sqrt(session unit), so sigma * sqrt(BT) is the variance
of the move (design §7).

A clock is frozen. `config/frozen/clock_v1.yaml` holds the 375 minute weights and the three gap thetas,
fitted once on 2019-2022 by `quantdesk/pricing/clockfit.py` and never refit inside a trial (M6). `sessions`
is not part of the file: it comes from the derived `sessions` table, so one frozen clock spans any sample.
"""

from bisect import bisect_left
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path

import numpy as np
import yaml

OPEN = time(9, 15)
MINUTES = 375  # 09:15 to 15:30, settings session.minutes; the length is part of the frozen file's contract


@dataclass(frozen=True, eq=False)  # eq=False: an ndarray field has no scalar ==, so clocks compare by identity
class Clock:
    """The frozen weights, and the sessions they are counted over."""

    minute_weights: np.ndarray
    theta_night: float
    theta_weekend_day: float
    theta_holiday: float
    sessions: tuple

    def __post_init__(self):
        weights = np.asarray(self.minute_weights, dtype=float)
        if weights.shape != (MINUTES,):
            raise ValueError(f"a clock needs {MINUTES} minute weights, got {weights.shape}")
        if abs(weights.sum() - 1.0) > 1e-9:
            raise ValueError(f"the minute weights must sum to 1, got {weights.sum()!r}")
        sessions = tuple(sorted(self.sessions))
        object.__setattr__(self, "minute_weights", weights)
        object.__setattr__(self, "sessions", sessions)
        object.__setattr__(self, "_elapsed", np.concatenate([[0.0], np.cumsum(weights)]))
        gaps = _gap_weights(sessions, self.theta_night, self.theta_weekend_day, self.theta_holiday)
        object.__setattr__(self, "_closed", np.concatenate([[0.0], np.cumsum(gaps + 1.0)]))

    def w_done(self, at: datetime) -> float:
        """The share of `at`'s session already elapsed: 0 before 09:15, 1 at or after 15:30."""
        elapsed = _minutes_since_open(_aware(at))
        if elapsed <= 0.0:
            return 0.0
        if elapsed >= MINUTES:
            return 1.0
        slot = int(elapsed)  # the minutes already closed, plus this minute's share of its own weight
        return float(self._elapsed[slot] + (elapsed - slot) * self.minute_weights[slot])

    def bt(self, t0: datetime, t1: datetime) -> float:
        """Business time from t0 to t1 in session units (design §7). Both ends must be session days."""
        t0, t1 = _aware(t0), _aware(t1)
        if t1 < t0:
            raise ValueError(f"bt needs t0 before t1, got {t0} then {t1}")
        i, j = self._session_index(t0.date()), self._session_index(t1.date())
        return float(self._closed[j] - self._closed[i] + self.w_done(t1) - self.w_done(t0))

    def _session_index(self, day: date) -> int:
        at = bisect_left(self.sessions, day)
        if at == len(self.sessions) or self.sessions[at] != day:
            raise ValueError(f"{day} is not a session on this clock; roll the endpoint to a session first")
        return at


def _aware(at: datetime) -> datetime:
    if at.tzinfo is None:
        raise ValueError(f"the clock needs a tz-aware time, got {at!r}")
    return at


def _minutes_since_open(at: datetime) -> float:
    return (at - datetime.combine(at.date(), OPEN, tzinfo=at.tzinfo)).total_seconds() / 60.0


def _gap_weights(sessions: tuple, theta_night: float, theta_weekend_day: float, theta_holiday: float) -> np.ndarray:
    """theta_n + theta_w*W + theta_h*H for each pair of consecutive sessions."""
    weekend, holiday = gap_days(sessions)
    return theta_night + theta_weekend_day * weekend + theta_holiday * holiday


def gap_days(sessions) -> tuple[np.ndarray, np.ndarray]:
    """(weekend days, weekday holidays) strictly between each pair of consecutive sessions.

    Every day strictly between two consecutive sessions is not a session, so the weekday ones are holidays
    and the rest are weekend days. `clockfit` fits the weights of these same two counts, so the clock and
    its fit cannot drift apart on what a gap is made of.
    """
    days = tuple(sorted(sessions))
    weekend = []
    for a, b in zip(days, days[1:]):
        span = (b - a).days
        weekend.append(sum(1 for offset in range(1, span) if (a + timedelta(days=offset)).weekday() >= 5))
    weekend = np.array(weekend, dtype=float)
    spans = np.array([(b - a).days for a, b in zip(days, days[1:])], dtype=float)
    return weekend, spans - 1.0 - weekend


def save_clock(path: Path, clock: Clock, meta: dict) -> None:
    """Write the frozen file: the weights, the three thetas, and `meta`'s audit fields (design §7)."""
    payload = {"minute_weights": [float(weight) for weight in clock.minute_weights],
               "theta_night": float(clock.theta_night),
               "theta_weekend_day": float(clock.theta_weekend_day),
               "theta_holiday": float(clock.theta_holiday),
               **meta}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def load_clock(path: Path, sessions) -> Clock:
    """Read the frozen file. `sessions` comes from the derived table, not from the file."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return Clock(np.asarray(raw["minute_weights"], dtype=float), theta_night=float(raw["theta_night"]),
                 theta_weekend_day=float(raw["theta_weekend_day"]), theta_holiday=float(raw["theta_holiday"]),
                 sessions=tuple(sessions))
