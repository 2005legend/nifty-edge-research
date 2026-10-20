"""Wires real dependencies for the CLI. Everything is created lazily, so commands that do not
need Angel One (status, news, macro) work without broker credentials."""

import threading
import time
from dataclasses import dataclass, field
from datetime import date

import requests

from quantdesk.broker.angel import AngelClient
from quantdesk.broker.ws import TickStream
from quantdesk.calendar.events import is_trading_day, load_events
from quantdesk.clock import SystemClock
from quantdesk.config import data_dir, load_settings, project_root
from quantdesk.eod.flows import fetch_nifty50_list
from quantdesk.instruments import download_master, equity_tokens, load_master, nifty50_symbols
from quantdesk.net.http import PoliteSession
from quantdesk.storage import Store


class ThreadedStream:
    """Runs a TickStream's blocking websocket loop on a daemon thread."""

    def __init__(self, stream: TickStream):
        self.stream = stream
        self._thread: threading.Thread | None = None

    def subscribe(self, tokens):
        self.stream.subscribe(tokens)

    def add_tokens(self, tokens):
        self.stream.add_tokens(tokens)

    def start(self):
        self._thread = threading.Thread(target=self.stream.run, name="tick-stream", daemon=True)
        self._thread.start()

    def check_stale(self):
        self.stream.check_stale()

    def close(self):
        self.stream.close()


@dataclass
class App:
    settings: dict
    store: Store
    clock: SystemClock
    sleep: object
    events: list
    _client: AngelClient | None = field(default=None, repr=False)
    _master: dict = field(default_factory=dict, repr=False)

    def client(self) -> AngelClient:
        if self._client is None:
            self._client = AngelClient.from_env(self.settings)
        return self._client

    def session(self) -> PoliteSession:
        return PoliteSession(min_interval_s=self.settings["eod"]["min_request_interval_s"],
                             clock=self.clock, sleep=self.sleep)

    def is_trading_day(self, day: date) -> bool:
        return is_trading_day(day, self.events)

    def master(self, day: date):
        if day not in self._master:
            url = self.settings["angel"]["instrument_master_url"]
            path, _ = download_master(self.store, lambda u: requests.get(u, timeout=60), day, url)
            self._master[day] = load_master(path)
        return self._master[day]

    def constituents(self, day: date) -> dict[str, str]:
        folder = self.store.root / "raw" / "nifty50_list"
        files = sorted(folder.glob("*/ind_nifty50list.csv")) if folder.exists() else []
        if files:
            content = files[-1].read_bytes()
        else:
            session = self.session()
            session.bootstrap(self.settings["urls"]["nse_home"])
            content = fetch_nifty50_list(session, self.store, day, self.settings["urls"]).read_bytes()
        return equity_tokens(self.master(day), nifty50_symbols(content))

    def stream_factory(self, on_tick, on_stale) -> ThreadedStream:
        client = self.client()
        from SmartApi.smartWebSocketV2 import SmartWebSocketV2

        stream = TickStream(client.jwt_token, client.api_key, client.client_code, client.feed_token,
                            on_tick=on_tick, on_stale=on_stale, clock=self.clock,
                            ws_factory=lambda *args: SmartWebSocketV2(*args),
                            stale_seconds=self.settings["recorder"]["stale_seconds"], sleep=self.sleep)
        return ThreadedStream(stream)


def build_app(settings: dict | None = None) -> App:
    settings = settings or load_settings()
    return App(settings=settings, store=Store(data_dir()), clock=SystemClock(), sleep=time.sleep,
               events=load_events(project_root() / "config" / "events.yaml"))
