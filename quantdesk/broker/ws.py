"""Angel One SmartWebSocketV2 wrapper: normalised ticks, staleness, reconnect + resubscribe."""

import time as _time
from dataclasses import dataclass
from datetime import datetime, timezone

from quantdesk.clock import IST

SNAP_QUOTE = 3


@dataclass(frozen=True)
class Tick:
    token: str
    exchange_type: int
    ltp: float
    exchange_ts: datetime
    received_at: datetime
    volume: int | None = None
    oi: int | None = None
    bid: float | None = None
    bid_qty: int | None = None
    ask: float | None = None
    ask_qty: int | None = None
    depth: tuple | None = None  # ((side, level, price, qty), ...) buys then sells


def _rupees(paise) -> float | None:
    return None if paise is None else float(paise) / 100.0


def _levels(side: str, rows) -> list[tuple]:
    out = []
    for level, row in enumerate(rows or [], start=1):
        out.append((side, level, _rupees(row.get("price")), int(row.get("quantity", 0))))
    return out


def normalize_tick(raw: dict, received_at: datetime) -> Tick:
    """Convert a SmartWebSocketV2 message (prices in paise, epoch ms UTC) to a Tick in rupees/IST."""
    ts_ms = raw.get("exchange_timestamp") or raw.get("last_traded_timestamp")
    exchange_ts = (datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).astimezone(IST)
                   if ts_ms else received_at)
    buys = _levels("buy", raw.get("best_5_buy_data"))
    sells = _levels("sell", raw.get("best_5_sell_data"))
    depth = tuple(buys + sells) if (buys or sells) else None
    volume = raw.get("volume_trade_for_the_day")
    oi = raw.get("open_interest")
    return Tick(
        token=str(raw.get("token", "")).strip("\x00 "),
        exchange_type=int(raw.get("exchange_type", 0)),
        ltp=_rupees(raw.get("last_traded_price")) or 0.0,
        exchange_ts=exchange_ts,
        received_at=received_at,
        volume=int(volume) if volume is not None else None,
        oi=int(oi) if oi is not None else None,
        bid=buys[0][2] if buys else None,
        bid_qty=buys[0][3] if buys else None,
        ask=sells[0][2] if sells else None,
        ask_qty=sells[0][3] if sells else None,
        depth=depth,
    )


def _token_list(tokens: dict[int, set[str] | list[str]]) -> list[dict]:
    return [{"exchangeType": int(ex), "tokens": sorted(toks)} for ex, toks in tokens.items() if toks]


class TickStream:
    def __init__(self, auth_token, api_key, client_code, feed_token, *, on_tick, on_stale, clock,
                 ws_factory, stale_seconds: int = 30, sleep=_time.sleep, max_reconnects: int = 50):
        self._args = (auth_token, api_key, client_code, feed_token)
        self._on_tick = on_tick
        self._on_stale = on_stale
        self._clock = clock
        self._ws_factory = ws_factory
        self._stale_seconds = stale_seconds
        self._sleep = sleep
        self._max_reconnects = max_reconnects
        self._subscribed: dict[int, set[str]] = {}
        self._mode = SNAP_QUOTE
        self._ws = None
        self._connected = False
        self._closing = False
        self._last_tick_at: datetime | None = None
        self._stale_reported = False

    # subscriptions --------------------------------------------------------
    def _merge(self, tokens: dict) -> dict[int, set[str]]:
        new: dict[int, set[str]] = {}
        for ex, toks in tokens.items():
            have = self._subscribed.setdefault(int(ex), set())
            fresh = {str(t) for t in toks} - have
            have.update(fresh)
            if fresh:
                new[int(ex)] = fresh
        return new

    def subscribe(self, tokens: dict, mode: int = SNAP_QUOTE) -> None:
        self._mode = mode
        if self._last_tick_at is None:
            self._last_tick_at = self._clock.now()
        new = self._merge(tokens)
        if self._connected and new:
            self._ws.subscribe("qd", self._mode, _token_list(new))

    def add_tokens(self, tokens: dict) -> None:
        self.subscribe(tokens, self._mode)

    # callbacks ------------------------------------------------------------
    def _on_open(self, wsapp) -> None:
        self._connected = True
        if self._subscribed:
            self._ws.subscribe("qd", self._mode, _token_list(self._subscribed))

    def _on_data(self, wsapp, message) -> None:
        now = self._clock.now()
        self._last_tick_at = now
        self._stale_reported = False
        self._on_tick(normalize_tick(message, received_at=now))

    def _on_close(self, wsapp) -> None:
        self._connected = False

    def _on_error(self, wsapp, error) -> None:
        self._connected = False

    def check_stale(self) -> None:
        if self._last_tick_at is None or self._stale_reported:
            return
        now = self._clock.now()
        if (now - self._last_tick_at).total_seconds() > self._stale_seconds:
            self._stale_reported = True
            self._on_stale(self._last_tick_at, now)

    # lifecycle ------------------------------------------------------------
    def run(self) -> None:
        attempt = 0
        while not self._closing and attempt <= self._max_reconnects:
            self._ws = self._ws_factory(*self._args)
            self._ws.on_open = self._on_open
            self._ws.on_data = self._on_data
            self._ws.on_close = self._on_close
            self._ws.on_error = self._on_error
            try:
                self._ws.connect()
            except Exception:  # noqa: BLE001 - any connection failure triggers a reconnect
                pass
            self._connected = False
            if self._closing:
                break
            attempt += 1
            self._sleep(min(2 ** min(attempt, 5), 30))

    def close(self) -> None:
        self._closing = True
        if self._ws is not None and hasattr(self._ws, "close_connection"):
            self._ws.close_connection()
