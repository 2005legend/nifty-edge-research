"""Pure aggregation of ticks into 1-minute bars, option snapshots and depth rows."""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

from quantdesk.broker.ws import Tick

BAR_COLUMNS = ["minute", "token", "open", "high", "low", "close", "volume", "n_ticks"]
SNAPSHOT_COLUMNS = ["minute", "token", "ltp", "bid", "bid_qty", "ask", "ask_qty", "volume", "oi",
                    "zero_quote", "exchange_ts", "received_at"]
DEPTH_COLUMNS = ["minute", "token", "side", "level", "price", "qty"]
INDEX_JUMP_LIMIT = 0.05


def is_bad_tick(tick: Tick, last_ltp: float | None, is_index: bool) -> str | None:
    if tick.ltp is None or tick.ltp <= 0:
        return "non_positive"
    if tick.bid and tick.ask and tick.bid > 0 and tick.ask > 0 and tick.bid > tick.ask:
        return "crossed"
    if is_index and last_ltp and abs(tick.ltp / last_ltp - 1) > INDEX_JUMP_LIMIT:
        return "index_jump"
    return None


@dataclass
class FlushResult:
    bars: pd.DataFrame
    snapshots: pd.DataFrame
    depth: pd.DataFrame
    dropped: dict = field(default_factory=dict)
    zero_quotes: int = 0
    crossed: int = 0


class MinuteAggregator:
    def __init__(self, option_tokens: set[str], depth_tokens: set[str], index_tokens: set[str]):
        self.option_tokens = set(option_tokens)
        self.depth_tokens = set(depth_tokens)
        self.index_tokens = set(index_tokens)
        self._buckets: dict[datetime, dict[str, list[Tick]]] = defaultdict(lambda: defaultdict(list))
        self._last_ltp: dict[str, float] = {}
        self._last_volume: dict[str, int] = {}
        self._dropped: dict[str, int] = defaultdict(int)

    def add_tokens(self, option_tokens: set[str] = frozenset(), depth_tokens: set[str] = frozenset()) -> None:
        self.option_tokens |= set(option_tokens)
        self.depth_tokens |= set(depth_tokens)

    def add(self, tick: Tick) -> str | None:
        reason = is_bad_tick(tick, self._last_ltp.get(tick.token), tick.token in self.index_tokens)
        if reason:
            self._dropped[reason] += 1
            return reason
        self._last_ltp[tick.token] = tick.ltp
        minute = tick.exchange_ts.replace(second=0, microsecond=0)
        self._buckets[minute][tick.token].append(tick)
        return None

    def _bar(self, minute, token, ticks: list[Tick]) -> dict:
        prices = [t.ltp for t in ticks]
        volumes = [t.volume for t in ticks if t.volume is not None]
        volume = None
        if volumes:
            base = self._last_volume.get(token, volumes[0])
            volume = max(0, volumes[-1] - base)
            self._last_volume[token] = volumes[-1]
        return {"minute": minute, "token": token, "open": prices[0], "high": max(prices),
                "low": min(prices), "close": prices[-1], "volume": volume, "n_ticks": len(ticks)}

    def flush(self, minute_end: datetime) -> FlushResult:
        bars, snaps, depth = [], [], []
        zero_quotes = 0
        for minute in sorted(m for m in self._buckets if m < minute_end):
            for token, ticks in self._buckets.pop(minute).items():
                last = ticks[-1]
                if token in self.option_tokens:
                    zero = not last.bid and not last.ask
                    zero_quotes += int(zero)
                    snaps.append({"minute": minute, "token": token, "ltp": last.ltp, "bid": last.bid,
                                  "bid_qty": last.bid_qty, "ask": last.ask, "ask_qty": last.ask_qty,
                                  "volume": last.volume, "oi": last.oi, "zero_quote": zero,
                                  "exchange_ts": last.exchange_ts, "received_at": last.received_at})
                else:
                    bars.append(self._bar(minute, token, ticks))
                if token in self.depth_tokens and last.depth:
                    for side, level, price, qty in last.depth:
                        depth.append({"minute": minute, "token": token, "side": side,
                                      "level": level, "price": price, "qty": qty})
        dropped = dict(self._dropped)
        self._dropped.clear()
        return FlushResult(bars=pd.DataFrame(bars, columns=BAR_COLUMNS),
                           snapshots=pd.DataFrame(snaps, columns=SNAPSHOT_COLUMNS),
                           depth=pd.DataFrame(depth, columns=DEPTH_COLUMNS),
                           dropped=dropped, zero_quotes=zero_quotes,
                           crossed=dropped.get("crossed", 0))
