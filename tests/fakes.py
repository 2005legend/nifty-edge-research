"""Test doubles shared across the test suite. No network, no real time."""

from datetime import datetime, timedelta


class FakeClock:
    def __init__(self, start: datetime):
        self._now = start

    def now(self) -> datetime:
        return self._now

    def advance(self, seconds: float) -> "FakeClock":
        self._now = self._now + timedelta(seconds=seconds)
        return self


class FakeSleep:
    """Callable that records requested sleeps and advances the fake clock."""

    def __init__(self, clock: FakeClock):
        self.clock = clock
        self.calls: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)
        if seconds > 0:
            self.clock.advance(seconds)
