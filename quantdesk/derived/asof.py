"""The only way the pipeline reads history: a row is visible from its `available_at`, never before (R4).

`DerivedStore.read` returns every row a table has, so a backtest reading through it would decide at 10:00
with the 15:29 close in hand. `AsOf` adds the availability filter to every read, and `require` checks a
frame that was built in memory rather than read.
"""

from datetime import datetime

import pandas as pd

from quantdesk.derived.store import DerivedStore


class LookAheadError(RuntimeError):
    """A row that was not knowable yet reached a decision."""


class AsOf:
    def __init__(self, derived: DerivedStore, at: datetime):
        if at.tzinfo is None:
            # DuckDB would read a naive literal in the session time zone, so the same code would leak 5.5
            # hours of future on one host and none on another.
            raise ValueError(f"AsOf needs a tz-aware time, got {at!r}")
        self.derived = derived
        self.at = at

    def read(self, table: str, where: str | None = None) -> pd.DataFrame:
        known = f"available_at <= TIMESTAMPTZ '{self.at.isoformat()}'"
        return self.derived.read(table, where=f"({where}) and {known}" if where else known)

    def require(self, frame: pd.DataFrame) -> pd.DataFrame:
        late = frame["available_at"] > self.at
        if bool(late.any()):
            raise LookAheadError(f"{int(late.sum())} row(s) available at {frame.loc[late, 'available_at'].max()},"
                                 f" after {self.at.isoformat()}")
        return frame
