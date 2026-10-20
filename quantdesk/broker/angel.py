"""Read-only Angel One SmartAPI client: login, last price, historical candles.

This module deliberately has no trading functions of any kind. A test enforces it.
"""

import time as _time
from datetime import datetime, time, timedelta

import pandas as pd
import pyotp

from quantdesk.clock import IST, SystemClock
from quantdesk.config import get_secret
from quantdesk.net.ratelimit import MultiWindowLimiter, retry

CANDLE_COLUMNS = ["ts", "open", "high", "low", "close", "volume"]
_RATE_CODES = {"AB1004", "AB2001"}


class LoginError(RuntimeError):
    pass


class AngelApiError(RuntimeError):
    def __init__(self, code: str, message: str):
        self.code = code or ""
        self.message = message or ""
        super().__init__(f"{self.code}: {self.message}")


def chunk_ranges(start: datetime, end: datetime, max_days: int) -> list[tuple[datetime, datetime]]:
    """Split [start, end] into contiguous chunks spanning at most max_days calendar days."""
    chunks = []
    cursor = start
    while cursor <= end:
        last_day = cursor.date() + timedelta(days=max_days - 1)
        chunk_end = datetime.combine(last_day, time(23, 59), tzinfo=cursor.tzinfo)
        chunk_end = min(chunk_end, end)
        chunks.append((cursor, chunk_end))
        cursor = datetime.combine(chunk_end.date() + timedelta(days=1), time(0, 0), tzinfo=cursor.tzinfo)
    return chunks


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, AngelApiError):
        return exc.code in _RATE_CODES or "rate" in exc.message.lower() or exc.code.startswith("5")
    return isinstance(exc, (ConnectionError, TimeoutError, OSError))


class AngelClient:
    def __init__(self, api_key: str, client_code: str, pin: str, totp_secret: str, *,
                 smart_factory, limiter: MultiWindowLimiter, clock, sleep, settings: dict):
        self._api_key = api_key
        self._client_code = client_code
        self._pin = pin
        self._totp_secret = totp_secret
        self._smart = smart_factory(api_key)
        self._limiter = limiter
        self._clock = clock
        self._sleep = sleep
        self._settings = settings
        self._tokens: dict = {}
        self._last_login: datetime | None = None
        self._last_error_code = ""

    @classmethod
    def from_env(cls, settings: dict) -> "AngelClient":
        from quantdesk.broker.sdk import smart_connect_factory

        clock = SystemClock()
        limiter = MultiWindowLimiter(settings["angel"]["rate_limits"], clock=clock, sleep=_time.sleep)
        return cls(get_secret("ANGEL_API_KEY"), get_secret("ANGEL_CLIENT_CODE"),
                   get_secret("ANGEL_PIN"), get_secret("ANGEL_TOTP_SECRET"),
                   smart_factory=smart_connect_factory, limiter=limiter,
                   clock=clock, sleep=_time.sleep, settings=settings)

    # session --------------------------------------------------------------
    @property
    def jwt_token(self) -> str | None:
        return self._tokens.get("jwtToken")

    @property
    def feed_token(self) -> str | None:
        return self._tokens.get("feedToken")

    @property
    def api_key(self) -> str:
        return self._api_key

    @property
    def client_code(self) -> str:
        return self._client_code

    def login(self) -> None:
        def attempt():
            totp = pyotp.TOTP(self._totp_secret).at(self._clock.now())
            response = self._smart.generateSession(self._client_code, self._pin, totp)
            if not response or not response.get("status"):
                raise LoginError(f"login failed ({(response or {}).get('errorcode', 'no response')})")
            return response["data"]

        data = retry(attempt, attempts=3, base_delay=2, max_delay=8,
                     retry_on=lambda e: isinstance(e, (LoginError, ConnectionError, OSError)),
                     sleep=self._sleep)
        self._tokens = dict(data)
        if not self._tokens.get("feedToken"):
            self._tokens["feedToken"] = self._smart.getfeedToken()
        self._last_login = self._clock.now()
        self._last_error_code = ""

    def ensure_session(self) -> None:
        now = self._clock.now()
        hh, mm = map(int, self._settings["angel"]["relogin_time"].split(":"))
        cutoff = datetime.combine(now.date(), time(hh, mm), tzinfo=IST)
        stale = self._last_login is None or (now >= cutoff > self._last_login)
        if stale or self._last_error_code.startswith("AG80"):
            self.login()

    def profile(self) -> dict:
        self.ensure_session()
        response = self._smart.getProfile(self._tokens.get("refreshToken"))
        return self._unwrap(response)

    # market data ----------------------------------------------------------
    def _unwrap(self, response):
        if not response or not response.get("status"):
            code = (response or {}).get("errorcode", "")
            self._last_error_code = code
            raise AngelApiError(code, (response or {}).get("message", "empty response"))
        return response.get("data")

    def _call(self, fn):
        def attempt():
            self._limiter.acquire()
            return self._unwrap(fn())

        return retry(attempt, attempts=5, base_delay=1, max_delay=16,
                     retry_on=_is_retryable, sleep=self._sleep)

    def ltp(self, exchange: str, tradingsymbol: str, token: str) -> float:
        self.ensure_session()
        data = self._call(lambda: self._smart.ltpData(exchange, tradingsymbol, token))
        return float(data["ltp"])

    def candles(self, exchange: str, token: str, interval: str,
                start: datetime, end: datetime) -> pd.DataFrame:
        self.ensure_session()
        max_days = self._settings["angel"]["candle_max_days"][interval]
        frames = []
        for chunk_start, chunk_end in chunk_ranges(start, end, max_days):
            params = {
                "exchange": exchange,
                "symboltoken": str(token),
                "interval": interval,
                "fromdate": chunk_start.strftime("%Y-%m-%d %H:%M"),
                "todate": chunk_end.strftime("%Y-%m-%d %H:%M"),
            }
            rows = self._call(lambda p=params: self._smart.getCandleData(p)) or []
            if rows:
                frames.append(pd.DataFrame(rows, columns=CANDLE_COLUMNS))
        if not frames:
            return pd.DataFrame(columns=CANDLE_COLUMNS)
        frame = pd.concat(frames, ignore_index=True)
        frame["ts"] = pd.to_datetime(frame["ts"], utc=True).dt.tz_convert(IST)
        for column in CANDLE_COLUMNS[1:]:
            frame[column] = pd.to_numeric(frame[column])
        frame = frame.drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
        return frame
