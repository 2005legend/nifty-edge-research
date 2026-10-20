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


class FakeResponse:
    def __init__(self, status_code: int, content: bytes, url: str = ""):
        self.status_code = status_code
        self.content = content
        self.url = url
        self.text = content.decode("utf-8", errors="replace")

    def json(self):
        import json

        return json.loads(self.content)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeHttp:
    """Stands in for requests.Session. `routes` maps url -> (status, bytes) or an Exception,
    or a callable(url) returning one of those."""

    def __init__(self, routes: dict, clock=None):
        self.routes = routes
        self.clock = clock
        self.requested: list[str] = []
        self.request_times: list = []
        self.headers: dict = {}

    def get(self, url, **kwargs):
        self.requested.append(url)
        if self.clock is not None:
            self.request_times.append(self.clock.now())
        route = self.routes.get(url)
        if callable(route) and not isinstance(route, Exception):
            route = route(url)
        if route is None:
            return FakeResponse(404, b"not found", url)
        if isinstance(route, Exception):
            raise route
        status, content = route
        return FakeResponse(status, content, url)


class FakeSmartConnect:
    """Mimics SmartApi.SmartConnect responses (dicts with status/data/errorcode)."""

    def __init__(self, api_key=None, *, login_responses=None, candle_responses=None, ltp_value=22550.0):
        self.api_key = api_key
        self.login_calls: list[tuple] = []
        self.candle_calls: list[dict] = []
        self.login_responses = list(login_responses or [])
        self.candle_responses = list(candle_responses or [])
        self.ltp_value = ltp_value

    def generateSession(self, client_code, pin, totp):
        self.login_calls.append((client_code, pin, totp))
        if self.login_responses:
            return self.login_responses.pop(0)
        return {"status": True, "data": {"jwtToken": "jwt-1", "refreshToken": "ref-1", "feedToken": "feed-1"}}

    def getfeedToken(self):
        return "feed-1"

    def getProfile(self, refresh_token):
        return {"status": True, "data": {"name": "TEST USER", "clientcode": "X1"}}

    def ltpData(self, exchange, tradingsymbol, symboltoken):
        return {"status": True, "data": {"ltp": self.ltp_value}}

    def getCandleData(self, params):
        self.candle_calls.append(dict(params))
        if self.candle_responses:
            response = self.candle_responses.pop(0)
            if isinstance(response, Exception):
                raise response
            if callable(response):
                return response(params)
            return response
        return {"status": True, "data": []}


class FakeWs:
    """One fake websocket connection. Plays a script on connect():
    dict -> delivered to on_data; callable -> called with this ws; "drop" -> on_close then return."""

    def __init__(self, script):
        self.script = list(script)
        self.subscribe_calls: list[tuple] = []
        self.on_open = self.on_data = self.on_error = self.on_close = None
        self.closed = False

    def connect(self):
        self.on_open(self)
        for item in self.script:
            if item == "drop":
                self.on_close(self)
                return
            if callable(item):
                item(self)
            else:
                self.on_data(self, item)

    def subscribe(self, correlation_id, mode, token_list):
        self.subscribe_calls.append((correlation_id, mode, token_list))

    def close_connection(self):
        self.closed = True


class FakeStream:
    """ws_factory for TickStream: hands out one FakeWs per connection attempt."""

    def __init__(self, scripts):
        self.scripts = list(scripts)
        self.connections: list[FakeWs] = []

    def __call__(self, *args, **kwargs):
        ws = FakeWs(self.scripts.pop(0) if self.scripts else [])
        self.connections.append(ws)
        return ws


class ScriptedStream:
    """Recorder-facing stream double. Ticks (quantdesk Tick objects) are delivered when the
    fake clock passes their exchange_ts; deliver_until() is driven by ScriptedSleep."""

    def __init__(self, ticks, clock, stale_seconds=30, skew_s=0.0, fail_add_tokens=False):
        self.pending = sorted(ticks, key=lambda t: t.exchange_ts)
        self.clock = clock
        self.stale_seconds = stale_seconds
        self.skew_s = skew_s  # PC clock ahead of the exchange by this many seconds
        self.fail_add_tokens = fail_add_tokens
        self.subscribed_at = None
        self.on_tick = self.on_stale = None
        self.subscribed: list[dict] = []
        self.added: list[dict] = []
        self.started = False
        self.closed = False
        self._last = None
        self._stale_reported = False

    def bind(self, on_tick, on_stale):
        self.on_tick, self.on_stale = on_tick, on_stale
        return self

    def subscribe(self, tokens):
        self.subscribed.append(tokens)
        self.subscribed_at = self.subscribed_at or self.clock.now()
        self._last = self.clock.now()

    def add_tokens(self, tokens):
        if self.fail_add_tokens:
            raise ConnectionError("socket closed")
        self.added.append(tokens)

    def start(self):
        self.started = True

    def deliver_until(self, now):
        while self.pending and self.pending[0].exchange_ts + timedelta(seconds=self.skew_s) <= now:
            tick = self.pending.pop(0)
            self._last = tick.exchange_ts
            self._stale_reported = False
            self.on_tick(tick)

    def check_stale(self):
        if self._last is None or self._stale_reported:
            return
        now = self.clock.now()
        if (now - self._last).total_seconds() > self.stale_seconds:
            self._stale_reported = True
            self.on_stale(self._last, now)

    def close(self):
        self.closed = True


class ScriptedSleep:
    """Advances the fake clock in small steps, delivering scripted ticks as time passes."""

    def __init__(self, clock, stream_holder: dict):
        self.clock = clock
        self.holder = stream_holder

    def __call__(self, seconds):
        end = self.clock.now() + timedelta(seconds=seconds)
        while self.clock.now() < end:
            step = min(1.0, (end - self.clock.now()).total_seconds())
            self.clock.advance(step)
            stream = self.holder.get("stream")
            if stream is not None and stream.on_tick is not None:
                stream.deliver_until(self.clock.now())


class FakeSleep:
    """Callable that records requested sleeps and advances the fake clock."""

    def __init__(self, clock: FakeClock):
        self.clock = clock
        self.calls: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)
        if seconds > 0:
            self.clock.advance(seconds)
