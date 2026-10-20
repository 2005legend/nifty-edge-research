"""Client-side rate limiting and retry with exponential backoff."""

from collections import deque
from typing import Any, Callable


class MultiWindowLimiter:
    """Allows at most (calls - 1) calls per window for every (calls, seconds) pair,
    so usage stays strictly below each published limit."""

    def __init__(self, limits, *, clock, sleep):
        self.windows = [(max(1, int(calls) - 1), float(seconds), deque()) for calls, seconds in limits]
        self.clock = clock
        self.sleep = sleep

    def acquire(self) -> None:
        while True:
            now = self.clock.now()
            wait = 0.0
            for allowed, seconds, stamps in self.windows:
                while stamps and (now - stamps[0]).total_seconds() >= seconds:
                    stamps.popleft()
                if len(stamps) >= allowed:
                    wait = max(wait, seconds - (now - stamps[0]).total_seconds())
            if wait <= 0:
                for _, _, stamps in self.windows:
                    stamps.append(now)
                return
            self.sleep(wait)


def retry(fn: Callable[[], Any], *, attempts: int, base_delay: float, max_delay: float,
          retry_on: Callable[[Exception], bool], sleep) -> Any:
    """Call fn; on an exception accepted by retry_on, sleep min(base*2**i, max) and retry."""
    for i in range(attempts):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - filtered by retry_on
            if not retry_on(exc) or i == attempts - 1:
                raise
            sleep(min(base_delay * 2 ** i, max_delay))
