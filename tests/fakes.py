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


class FakeSleep:
    """Callable that records requested sleeps and advances the fake clock."""

    def __init__(self, clock: FakeClock):
        self.clock = clock
        self.calls: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)
        if seconds > 0:
            self.clock.advance(seconds)
