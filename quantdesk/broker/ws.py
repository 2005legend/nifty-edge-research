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
    atp: float | None = None  # exchange average traded price (VWAP) for the day
    total_buy_qty: int | None = None
    total_sell_qty: int | None = None
    last_traded_qty: int | None = None
    last_traded_ts_raw: int | None = None  # as sent by the feed; unit to be confirmed live
    seq: int | None = None
    day_open: float | None = None
    day_high: float | None = None
    day_low: float | None = None
    prev_close: float | None = None


def _rupees(paise) -> float | None:
    return None if paise is None else float(paise) / 100.0


def _int(value) -> int | None:
    return None if value is None else int(value)


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
        atp=_rupees(raw.get("average_traded_price")),
        total_buy_qty=_int(raw.get("total_buy_quantity")),
        total_sell_qty=_int(raw.get("total_sell_quantity")),
        last_traded_qty=_int(raw.get("last_traded_quantity")),
        last_traded_ts_raw=_int(raw.get("last_traded_timestamp")),
        seq=_int(raw.get("sequence_number")),
        day_open=_rupees(raw.get("open_price_of_the_day")),
        day_high=_rupees(raw.get("high_price_of_the_day")),
        day_low=_rupees(raw.get("low_price_of_the_day")),
        prev_close=_rupees(raw.get("closed_price")),
    )


def _token_list(tokens: dict[int, set[str] | list[str]]) -> list[dict]:
    return [{"exchangeType": int(ex), "tokens": sorted(toks)} for ex, toks in tokens.items() if toks]


class TickStream:
    def __init__(self, auth_token, api_key, client_code, feed_token, *, on_tick, on_stale, clock,
                 ws_factory, stale_seconds: int = 30, sleep=_time.sleep, max_reconnects: int = 10_000):
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
        self._attempt = 0

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
            self._send_subscribe(new)

    def add_tokens(self, tokens: dict) -> None:
        self.subscribe(tokens, self._mode)

    # callbacks ------------------------------------------------------------
    def _send_subscribe(self, tokens: dict) -> None:
        """A failed send marks the stream disconnected; every token is resubscribed on the next open."""
        try:
            self._ws.subscribe("qd", self._mode, _token_list(tokens))
        except Exception:  # noqa: BLE001 - dead socket; the reconnect loop recovers
            self._connected = False

    def _on_open(self, wsapp) -> None:
        self._connected = True
        self._attempt = 0  # a successful connection resets the reconnect budget
        if self._subscribed:
            self._send_subscribe({ex: set(toks) for ex, toks in self._subscribed.items()})

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
        """Connect and reconnect until close(). max_reconnects caps *consecutive* failed attempts."""
        self._attempt = 0
        while not self._closing and self._attempt <= self._max_reconnects:
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
            self._attempt += 1
            self._sleep(min(2 ** min(self._attempt, 5), 30))

    def reconnect(self) -> None:
        """Drop the current connection without stopping: run() connects again and resubscribes everything.
        Used when the feed freezes while the socket stays open."""
        self._connected = False
        if self._ws is not None and hasattr(self._ws, "close_connection"):
            self._ws.close_connection()

    def close(self) -> None:
        self._closing = True
        if self._ws is not None and hasattr(self._ws, "close_connection"):
            self._ws.close_connection()
