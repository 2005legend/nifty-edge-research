# SP1 Data Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `quantdesk` data foundation. It covers:
- Angel One read-only client
- instrument resolution
- live recorder with depth and opening-tick logging
- 1-minute history backfill
- NSE/BSE end-of-day jobs
- OpenBB/yfinance macro collector
- India news collector
- event calendar
- immutable storage
- daily health reports
- a CLI

**Architecture:**
- A plain Python package `quantdesk/`.
- Every network-facing piece takes its client, clock and sleep function as constructor arguments, so all logic runs in tests with fakes and **no test touches the network**.
- Data flows: source → `data/raw/...` (immutable, append-only Parquet parts or original files) → DuckDB views for reading.
- One opt-in `live` pytest marker covers the few smoke tests that need real credentials.

**Tech Stack:**
- Python 3.11 (existing `.venv`), pandas 3, pyarrow, duckdb, PyYAML, python-dotenv, requests, feedparser
- `smartapi-python` + `pyotp` + `websocket-client` (Angel One)
- yfinance
- OpenBB lean providers (`openbb-core`, `-fred`, `-federal-reserve`, `-oecd`, `-imf`, `-nasdaq`, `-ecb`, `-mcp-server`)
- tzdata, pytest

**Spec:** `docs/superpowers/specs/2026-10-06-nifty-sensex-options-signal-system-design.md`, section 5 (also §2 constraints, §9 open items). Decision log: `docs/decisions.md`.

## Global Constraints

- Python 3.11 on Windows 11. Use `.venv/Scripts/python`. All code must run on Windows paths.
- Timezone: every stored timestamp is timezone-aware `Asia/Kolkata` (via `zoneinfo`; `tzdata` installed). Websocket epoch milliseconds are converted to IST.
- Market session: 09:15–15:30 IST, 375 one-minute bars on a full trading day.
- **No order code anywhere.** `quantdesk/broker/` must not define or call order, modify, cancel or GTT functions. A test enforces this.
- **Secrets come only from `.env`:** `ANGEL_API_KEY`, `ANGEL_CLIENT_CODE`, `ANGEL_PIN`, `ANGEL_TOTP_SECRET`, `FRED_API_KEY`, `GROQ_API_KEY`.
  - Never log, print or commit a secret value.
  - Error messages name the variable, never its value.
- **Tests make no live network calls.** Live checks use `@pytest.mark.live` and are skipped unless `pytest -m live` is run.
- Angel One REST limits: 3 requests/second, 180/minute, 5,000/hour. Set the limiter strictly below each.
- **`data/raw/` is immutable:**
  - Original downloads are never overwritten.
  - Recorder output is written as new Parquet part files, never rewritten.
- Polite scraping of NSE/BSE: browser-like headers, a session cookie from the home page, ≥1.5 seconds between requests.
- **Expiry dates come only from the instrument master**, never from calendar arithmetic.
- **Every `config/events.yaml` entry has a `source_url`.**
- Commits use the owner's git identity with no Claude attribution or `Co-Authored-By` line (`~/.claude/CLAUDE.md`).
- `data/`, `.venv*`, `.env`, `env.txt`, `*.env` are git-ignored (already set in `.gitignore`).

## Review Focus

1. **Holiday or weekend run.** `record` started on a non-trading day exits cleanly with status `holiday` and writes nothing. Pinned in Task 9.
2. **Holiday-shifted expiry.** When Tuesday is a holiday, the Nifty weekly expires on Monday. Resolution must return the master's Monday date. Pinned in Task 6.
3. **Duplicate or concurrent run.** A second `record` while one is running must refuse with `AlreadyRunningError`, not double-write. A stale lock from a crash (owning PID dead) is cleared. Pinned in Task 9.
4. **Blocked or garbled download.** NSE/BSE often return an HTML block page with HTTP 200. It must be detected and reported as `bad_download`, never saved as raw data. Pinned in Tasks 3 and 11.
5. **Clock and epoch conversion.** Websocket exchange timestamps (epoch ms, UTC) must map to the correct IST minute even if the PC clock zone is not IST. Pinned in Task 5.

---

## File structure

```
pyproject.toml                         deps, pytest config (markers: live)
.env.example                           the six secret names, empty values
config/settings.yaml                   all tunables and URLs (no secrets)
config/events.yaml                     dated events with source_url
config/news_feeds.yaml                 RSS/GDELT feed list
quantdesk/__init__.py, __main__.py     `python -m quantdesk` → cli.main()
quantdesk/config.py                    settings + secrets loading
quantdesk/clock.py                     Clock protocol, SystemClock (IST)
quantdesk/storage.py                   raw files, Parquet parts, DuckDB views
quantdesk/net/ratelimit.py             MultiWindowLimiter, retry()
quantdesk/net/http.py                  PoliteSession, looks_like_html()
quantdesk/broker/angel.py              AngelClient (login, ltp, candles), chunk_ranges()
quantdesk/broker/ws.py                 Tick, normalize_tick(), TickStream
quantdesk/instruments.py               master download/load, expiries, chain tokens
quantdesk/recorder/bars.py             MinuteAggregator, is_bad_tick()
quantdesk/recorder/plan.py             SubscriptionPlan, plan_subscriptions(), recenter()
quantdesk/recorder/live.py             run_recording(), run lock
quantdesk/history/backfill.py          Target, default_targets(), run_backfill()
quantdesk/eod/bhavcopy.py              NSE/BSE F&O bhavcopy fetch/parse/backfill
quantdesk/eod/flows.py                 participant OI, FII/DII, run_eod()
quantdesk/macro/sources.py             fetchers per source (yfinance, OpenBB, fbil, nse)
quantdesk/macro/collect.py             run_macro_daily(), run_macro_intraday()
quantdesk/news/collect.py              poll_once(), is_price_restatement(), run_news_loop()
quantdesk/calendar/events.py           Event, load_events(), is_trading_day()
quantdesk/quality.py                   build_health_report()
quantdesk/app.py                       build_app(): wires real dependencies
quantdesk/cli.py                       argparse commands
tests/fakes.py                         FakeClock, FakeSleep, FakeSmartConnect, FakeStream, FakeHttp
tests/fixtures/                        small synthetic master JSON, bhavcopy zips, CSVs, RSS XML
tests/test_<module>.py                 one test file per module
docs/runbook.md                        daily operation + Task Scheduler setup (Task 18)
```

---

### Task 1: Project scaffold, settings, secrets, clock

**Files:**
- Create: `pyproject.toml`, `.env.example`, `config/settings.yaml`, `quantdesk/__init__.py`, `quantdesk/__main__.py`, `quantdesk/config.py`, `quantdesk/clock.py`, `tests/fakes.py`, `tests/test_config.py`

**Interfaces:**
- Produces:
  - `config.project_root() -> Path`
  - `config.load_settings(path: Path | None = None) -> dict`
  - `config.get_secret(name: str) -> str`, which raises `MissingSecretError(name)`
  - `config.data_dir() -> Path`
  - `clock.IST: ZoneInfo`
  - `clock.Clock` (Protocol: `now() -> datetime`)
  - `clock.SystemClock`
  - `tests.fakes.FakeClock(start: datetime)` with `.now()` and `.advance(seconds: float)`
  - `tests.fakes.FakeSleep(clock)`: calling it advances the clock

- [ ] **Step 1: Create `pyproject.toml`.**
  - Project `quantdesk`, `requires-python = ">=3.11"`.
  - Dependencies: `pandas>=3.0`, `pyarrow`, `duckdb`, `pyyaml`, `python-dotenv`, `requests`, `feedparser`, `yfinance`, `smartapi-python`, `pyotp`, `websocket-client`, `logzero`, `tzdata`.
  - Optional `[macro]`: `openbb-core`, `openbb-fred`, `openbb-federal-reserve`, `openbb-oecd`, `openbb-imf`, `openbb-nasdaq`, `openbb-ecb`, `openbb-mcp-server`.
  - `[dev]`: `pytest`.
  - `[tool.pytest.ini_options]`: `markers = ["live: needs real credentials/network"]`, `addopts = "-m 'not live'"`.
- [ ] **Step 2: Install.**
  - Run: `.venv/Scripts/python -m pip install -e ".[dev]"`
  - Expected: success, and `.venv/Scripts/python -c "import SmartApi, pyotp, duckdb, feedparser"` prints nothing.
  - If `smartapi-python` pins clash with pandas 3, record the clash in the commit message and pin the lowest compatible versions.
- [ ] **Step 3: Write `.env.example`** with the six names from Global Constraints, each as `NAME=` with no value. Write `config/settings.yaml` with these sections (values exactly):

```yaml
timezone: Asia/Kolkata
session: {open: "09:15", close: "15:30", minutes: 375}
paths: {data_dir: data}
angel:
  rate_limits: [[3, 1.0], [180, 60.0], [5000, 3600.0]]   # (calls, seconds); limiter uses calls-1 per window
  candle_max_days: {ONE_MINUTE: 30, THREE_MINUTE: 60, FIVE_MINUTE: 100, TEN_MINUTE: 100,
                    FIFTEEN_MINUTE: 200, THIRTY_MINUTE: 200, ONE_HOUR: 400, ONE_DAY: 2000}
  relogin_time: "08:45"
  instrument_master_url: https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json
  index_tokens: {NIFTY: {exchange: NSE, token: "99926000"}, SENSEX: {exchange: BSE, token: "99919000"},
                 INDIAVIX: {exchange: NSE, token: "99926017"}}
recorder: {strike_width: 15, fallback_width: 10, recenter_strikes: 5, depth_width: 3,
           opening_ticks: ["09:15", "09:30"], stale_seconds: 30, max_tokens_per_connection: 1000}
backfill: {minute_start: "2019-01-01", daily_start: "2015-01-01"}
eod: {retry_until: "23:00", min_request_interval_s: 1.5}
```

  Later tasks append their own sections (`urls`, `macro`, `news`).
- [ ] **Step 4: Write the failing tests** in `tests/test_config.py`:
  - `test_load_settings_reads_session_minutes`: `load_settings()["session"]["minutes"] == 375`.
  - `test_get_secret_missing_raises_with_name_only`: with `monkeypatch.delenv("ANGEL_PIN", raising=False)`, `pytest.raises(MissingSecretError, match="ANGEL_PIN")`. Then set `ANGEL_PIN=9999` and assert `"9999" not in str(MissingSecretError("ANGEL_PIN"))`.
  - `test_env_example_lists_all_secret_names_without_values`: every line in `.env.example` matches `^[A-Z_]+=$`, and the set of names equals the six names.
  - `test_fake_clock_is_ist`: `FakeClock(datetime(2026,10,20,9,15,tzinfo=IST)).advance(60).now().minute == 16`.
- [ ] **Step 5: Run** `.venv/Scripts/python -m pytest tests/test_config.py -v`. Expected: FAIL (module not found).
- [ ] **Step 6: Implement.**
  - `config.py`: `load_dotenv(project_root()/".env", override=False)` once on import of `get_secret`. Settings via `yaml.safe_load`.
  - `clock.py`: `SystemClock.now()` returns `datetime.now(IST)`.
  - `__main__.py`: `from quantdesk.cli import main; main()`. Guard the import until Task 17 by making `cli.py` a stub `def main(): raise SystemExit("cli not built yet")`.
- [ ] **Step 7: Run tests.** Expected: 4 passed.
- [ ] **Step 8: Commit** `feat: project scaffold, settings, secrets, clock`.

---

### Task 2: Storage (immutable raw files, Parquet parts, DuckDB views)

**Files:**
- Create: `quantdesk/storage.py`, `tests/test_storage.py`

**Interfaces:**
- Consumes: `config.data_dir()`
- Produces:
  - `Store(root: Path)`
  - `Store.write_raw(source: str, day: date, name: str, content: bytes) -> Path`. Writes to `root/raw/<source>/<YYYY-MM-DD>/<name>`. Raises `RawExistsError` if the file exists.
  - `Store.raw_exists(source, day, name) -> bool`
  - `Store.append_parquet(kind: str, day: date, df: pd.DataFrame) -> Path`. Writes `root/raw/<kind>/date=<YYYY-MM-DD>/part-<HHMMSSffffff>-<uuid8>.parquet`.
  - `Store.read(kind: str, day: date | None = None) -> pd.DataFrame`. DuckDB `read_parquet` over the glob, `hive_partitioning=true`.
  - `Store.connect() -> duckdb.DuckDBPyConnection`, with one view per existing kind.
  - `Store.write_report(kind: str, day: date, data: dict) -> Path`. Writes `root/reports/<kind>/<YYYY-MM-DD>.json`, overwriting is allowed because reports are derived.
  - `Store.read_report(kind: str, day: date) -> dict | None`

- [ ] **Step 1: Write the failing tests** (use `tmp_path`):
  - `test_write_raw_refuses_overwrite`: the second identical call raises `RawExistsError`.
  - `test_append_parquet_twice_reads_both`: append frames of 2 and 3 rows for `("bars", date(2026,10,20))`. `read("bars", date(2026,10,20))` has 5 rows.
  - `test_read_returns_empty_frame_when_kind_missing`: `read("nothing")` is an empty DataFrame (no exception).
  - `test_connect_exposes_view_per_kind`: after appending `bars` and `news`, `con.sql("select count(*) from bars").fetchone()[0] == 2`.
  - `test_report_round_trip`: `write_report("eod", d, {"a": 1})` then `read_report("eod", d) == {"a": 1}`. A missing report gives `None`.
- [ ] **Step 2: Run** `pytest tests/test_storage.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement `Store`.** Parquet via `df.to_parquet(path, index=False)`. Create parent dirs. Never open an existing part file for writing.
- [ ] **Step 4: Run tests.** Expected: 5 passed.
- [ ] **Step 5: Commit** `feat: immutable storage with parquet parts and duckdb views`.

---

### Task 3: Rate limiting, retry, polite HTTP

**Files:**
- Create: `quantdesk/net/__init__.py`, `quantdesk/net/ratelimit.py`, `quantdesk/net/http.py`, `tests/test_net.py`

**Interfaces:**
- Produces:
  - `MultiWindowLimiter(limits: list[tuple[int, float]], clock, sleep)` with `.acquire() -> None`. Allows at most `calls-1` per window, so it stays strictly below the published limit.
  - `retry(fn, *, attempts: int, base_delay: float, max_delay: float, retry_on: Callable[[Exception], bool], sleep) -> Any`: exponential backoff `min(base*2**i, max)`, no jitter.
  - `PoliteSession(headers: dict, min_interval_s: float, clock, sleep, http=None)` with `.bootstrap(home_url) -> None` and `.get(url, **kw) -> requests.Response`. `http` defaults to a `requests.Session`; tests pass `FakeHttp`.
  - `looks_like_html(content: bytes) -> bool`: true if the first 512 bytes, lower-cased and stripped, start with `<!doctype html` or `<html`, or contain `<html`.
  - `BadDownloadError(Exception)`

- [ ] **Step 1: Write the failing tests:**
  - `test_limiter_spaces_calls_below_3_per_second`: with `FakeClock` and `FakeSleep`, 10 `acquire()` calls under limits `[[3,1.0]]` advance the clock by ≥ 4.0 seconds (2 per second).
  - `test_retry_backoff_sequence`: `fn` fails 3 times then returns 7. `retry(..., attempts=5, base_delay=1, max_delay=4)` returns 7 and the recorded sleeps are `[1, 2, 4]`.
  - `test_retry_gives_up_and_reraises`: always failing, `attempts=3` re-raises the last exception after sleeps `[1, 2]`.
  - `test_polite_session_min_interval`: two `get()` calls are ≥1.5 s apart on the fake clock.
  - `test_looks_like_html_detects_block_page` [Review Focus 4]: `b"\r\n<!DOCTYPE html><html>Access Denied"` → True. `b"PK\x03\x04"` → False. `b"TradDt,BizDt"` → False.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement.** The limiter keeps a deque of timestamps per window.
- [ ] **Step 4: Run.** Expected: 5 passed.
- [ ] **Step 5: Commit** `feat: rate limiter, retry, polite http`.

---

### Task 4: Angel One REST client (read-only)

**Files:**
- Create: `quantdesk/broker/__init__.py`, `quantdesk/broker/angel.py`, `tests/test_angel.py`
- Modify: `tests/fakes.py` (add `FakeSmartConnect`)

**Interfaces:**
- Consumes: `MultiWindowLimiter`, `retry`, `get_secret`, settings `angel.*`
- Produces:
  - `chunk_ranges(start: datetime, end: datetime, max_days: int) -> list[tuple[datetime, datetime]]`
  - `AngelClient(api_key, client_code, pin, totp_secret, *, smart_factory, limiter, clock, sleep, settings)`, with:
    - `.login() -> None`
    - `.ensure_session() -> None`
    - `.ltp(exchange: str, tradingsymbol: str, token: str) -> float`
    - `.candles(exchange: str, token: str, interval: str, start: datetime, end: datetime) -> pd.DataFrame` with columns `ts` (IST-aware), `open`, `high`, `low`, `close`, `volume`
    - `.profile() -> dict`
    - properties `.jwt_token`, `.feed_token`
  - `LoginError`, `AngelApiError(code: str, message: str)`
  - `AngelClient.from_env(settings) -> AngelClient`

- [ ] **Step 1: Write the failing tests:**
  - `test_chunk_ranges_30_day_minute_chunks`: 2026-01-01 → 2026-03-15 at 30 days gives 3 contiguous, non-overlapping chunks. First is Jan 1 → Jan 30 23:59; last ends Mar 15.
  - `test_login_uses_totp_and_stores_tokens`: `FakeSmartConnect` records the `generateSession(client_code, pin, totp)` args. The totp equals `pyotp.TOTP(secret).now()` at the fake time, and `.feed_token` is the fake's value.
  - `test_login_retries_three_times_then_raises`: the fake returns `{"status": False}` each time → `LoginError` after 3 attempts.
  - `test_candles_chunked_rate_limited_and_concatenated`: a 65-day ONE_MINUTE request makes 3 `getCandleData` calls. Result rows are sorted, de-duplicated on `ts`, and `ts.dt.tz` is IST.
  - `test_candles_retries_on_rate_error`: the first call raises `AngelApiError("AB1004", "exceeding access rate")`, the second succeeds → one backoff sleep.
  - `test_no_order_methods_exist`: no public name of `AngelClient` matches `re.compile(r"order|place|modify|cancel|gtt", re.I)`, and the source of `quantdesk/broker/angel.py` does not contain `placeOrder`.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement.**
  - `smart_factory(api_key)` returns a `SmartConnect`. Candle params `{"exchange", "symboltoken", "interval", "fromdate": "%Y-%m-%d %H:%M", "todate": ...}`.
  - Parse the response `data` rows `[ts_str, o, h, l, c, v]` with `pd.to_datetime(...).dt.tz_convert(IST)`.
  - `ensure_session()` re-logs in when the last login was before today's `relogin_time` or when the last error code starts with `AG80`.
- [ ] **Step 4: Run.** Expected: 6 passed.
- [ ] **Step 5: Commit** `feat: read-only Angel One REST client`.

---

### Task 5: Websocket stream wrapper and tick normalisation

**Files:**
- Create: `quantdesk/broker/ws.py`, `tests/test_ws.py`
- Modify: `tests/fakes.py` (add `FakeStream`)

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) Tick`, fields: `token: str`, `exchange_type: int`, `ltp: float`, `exchange_ts: datetime`, `received_at: datetime`, `volume: int | None`, `oi: int | None`, `bid: float | None`, `bid_qty: int | None`, `ask: float | None`, `ask_qty: int | None`, `depth: tuple | None` (5 buys and 5 sells as `(price, qty)` pairs)
  - `normalize_tick(raw: dict, received_at: datetime) -> Tick`. Prices from the v2 binary feed are in paise, so divide by 100. `exchange_timestamp` epoch ms (UTC) converts to IST.
  - `TickStream(auth_token, api_key, client_code, feed_token, *, on_tick, on_stale, clock, ws_factory, stale_seconds)` with:
    - `.subscribe(tokens: dict[int, list[str]], mode: int = 3) -> None` (exchange types: 1 nse_cm, 2 nse_fo, 3 bse_cm, 4 bse_fo; mode 3 = SnapQuote)
    - `.add_tokens(tokens) -> None`
    - `.check_stale() -> None`
    - `.run() -> None`
    - `.close() -> None`
  - Reconnects with backoff and re-subscribes every token ever subscribed.

- [ ] **Step 1: Write the failing tests:**
  - `test_normalize_tick_converts_paise_and_epoch` [Review Focus 5]: raw `{"token": "43210", "exchange_type": 2, "last_traded_price": 1234550, "exchange_timestamp": 1792561500000, ...}` gives `ltp == 12345.50`. `exchange_ts == datetime(2026,10,20,9,15, tzinfo=IST)`, using the epoch for 2026-10-20 03:45:00Z computed in the test via `datetime(2026,10,20,3,45,tzinfo=timezone.utc).timestamp()*1000`. The result holds even when `TZ` is set to `America/New_York` via monkeypatch.
  - `test_normalize_tick_depth_five_levels`: a raw dict with `best_5_buy_data` and `best_5_sell_data` gives `depth` of length 2×5 with prices in rupees, and `bid`/`ask` equal to the top levels.
  - `test_stale_fires_after_30_seconds_without_ticks`: with `FakeClock` and a `FakeStream` that emits nothing for 31 s, `check_stale()` calls `on_stale` once. A tick resets it.
  - `test_reconnect_resubscribes_all_tokens`: `FakeStream` drops the connection after `subscribe` and `add_tokens`. After reconnect, the subscribe calls cover the union of tokens.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement.** `ws_factory` returns a `SmartWebSocketV2`-compatible object with `on_data`, `on_open`, `on_close`, `on_error`, `connect()` and `subscribe(correlation_id, mode, token_list)`. The `token_list` format is `[{"exchangeType": int, "tokens": [str]}]`.
- [ ] **Step 4: Run.** Expected: 4 passed.
- [ ] **Step 5: Commit** `feat: websocket stream wrapper and tick normalisation`.

---

### Task 6: Instruments (master, expiries, chain tokens)

**Files:**
- Create: `quantdesk/instruments.py`, `tests/test_instruments.py`, `tests/fixtures/master_small.json` (about 40 synthetic rows in the Angel master format: `token`, `symbol`, `name`, `expiry` like `"06OCT2026"`, `strike` ×100 as string like `"2255000.000000"`, `lotsize`, `instrumenttype`, `exch_seg`, `tick_size` in paise like `"5.000000"`)

**Interfaces:**
- Consumes: `Store`, `PoliteSession`, settings `angel.instrument_master_url`, `angel.index_tokens`
- Produces:
  - `download_master(store, http_get, day: date) -> tuple[Path, bool]`. Returns `(path, is_fallback)`. On failure it uses the newest earlier cached master.
  - `load_master(path) -> pd.DataFrame` with columns `token, symbol, name, expiry (date|NaT), strike (rupees), lotsize (int), instrumenttype, exch_seg, tick_size (rupees)`
  - `option_expiries(master, underlying: str, today: date, n: int = 2) -> list[date]`. Uses NIFTY → NFO and SENSEX → BFO, `instrumenttype == "OPTIDX"`.
  - `atm_strike(spot: float, strikes: Sequence[float]) -> float`
  - `chain_tokens(master, underlying, expiry: date, atm: float, width: int) -> pd.DataFrame` with columns `strike, ce_token, pe_token, lotsize, tick_size`
  - `current_future(master, underlying, today) -> pd.Series`
  - `nifty50_symbols(csv_bytes: bytes) -> list[str]`
  - `equity_tokens(master, symbols: list[str]) -> dict[str, str]`, matching `symbol == f"{s}-EQ"` on NSE

- [ ] **Step 1: Write the failing tests:**
  - `test_load_master_scales_strike_and_tick`: strike `"2255000.000000"` → `22550.0`; tick `"5.000000"` → `0.05`.
  - `test_option_expiries_nearest_two`: today 2026-10-19 gives `[2026-10-20, 2026-10-27]` for NIFTY.
  - `test_holiday_shifted_expiry_taken_from_master` [Review Focus 2]: the fixture has the NIFTY weekly on Monday 2026-11-23 (Tuesday 24th a holiday in the fixture). `option_expiries(..., today=date(2026,11,20))[0] == date(2026,11,23)`.
  - `test_chain_tokens_width_uses_listed_strikes`: atm 22550, width 2 gives 5 strikes `[22450, 22500, 22550, 22600, 22650]`, each with both tokens.
  - `test_atm_strike_nearest`: 22574 → 22550 with 50-point strikes; 22576 → 22600.
  - `test_download_master_falls_back_to_previous_cache`: `http_get` raises; a cached master for the previous day exists → returns that path with `is_fallback True`.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement.** Parse expiry with format `%d%b%Y` (upper-case month). Store the downloaded master via `Store.write_raw("instruments", day, "master.json", bytes)`.
- [ ] **Step 4: Run.** Expected: 6 passed.
- [ ] **Step 5: Commit** `feat: instrument master, expiries and chain tokens`.

---

### Task 7: Minute aggregation and bad-tick filter (pure)

**Files:**
- Create: `quantdesk/recorder/__init__.py`, `quantdesk/recorder/bars.py`, `tests/test_bars.py`

**Interfaces:**
- Consumes: `Tick`
- Produces:
  - `is_bad_tick(tick: Tick, last_ltp: float | None, is_index: bool) -> str | None`. Returns `"non_positive"`, `"crossed"` (bid > ask when both > 0), `"index_jump"` (index |ltp/last − 1| > 0.05), or `None`.
  - `MinuteAggregator(option_tokens: set[str], depth_tokens: set[str], index_tokens: set[str])` with:
    - `.add(tick) -> str | None` (returns the drop reason)
    - `.flush(minute_end: datetime) -> FlushResult`
  - `FlushResult(bars: DataFrame, snapshots: DataFrame, depth: DataFrame, dropped: dict[str, int], zero_quotes: int, crossed: int)`
    - `bars` columns: `minute, token, open, high, low, close, volume, n_ticks`. Volume is the delta of cumulative volume within the minute; None for index tokens.
    - `snapshots` columns: `minute, token, ltp, bid, bid_qty, ask, ask_qty, volume, oi, zero_quote, exchange_ts, received_at`
    - `depth` columns: `minute, token, side, level, price, qty`

- [ ] **Step 1: Write the failing tests:**
  - `test_bars_ohlc_and_volume_delta`: ticks at ltp 100, 102, 99, 101 with cumulative volume 1000→1300 within 09:15 give bar o=100 h=102 l=99 c=101 volume=300 n_ticks=4.
  - `test_option_snapshot_is_last_state_in_minute`: the snapshot's bid and ask equal the last tick's values.
  - `test_bad_ticks_dropped_and_counted`: ltp 0 → `non_positive`. bid 10, ask 9 → `crossed`. Index 22500 → 23700 → `index_jump`. `flush().dropped == {"non_positive":1, "crossed":1, "index_jump":1}`.
  - `test_zero_quote_flagged_not_dropped`: bid 0 and ask 0 with ltp > 0 → kept, `zero_quote True`, `zero_quotes == 1`.
  - `test_depth_rows_only_for_depth_tokens`: depth rows exist only for tokens in `depth_tokens` (10 rows per token).
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement.** Bucket by `tick.exchange_ts.replace(second=0, microsecond=0)`. `flush` emits buckets for minutes `< minute_end` and keeps later ones.
- [ ] **Step 4: Run.** Expected: 5 passed.
- [ ] **Step 5: Commit** `feat: minute aggregation and bad-tick filter`.

---

### Task 8: Subscription planning and re-centring (pure)

**Files:**
- Create: `quantdesk/recorder/plan.py`, `tests/test_plan.py`

**Interfaces:**
- Consumes: `option_expiries`, `chain_tokens`, `atm_strike`, `current_future`, `equity_tokens`, settings `recorder.*`, `angel.index_tokens`
- Produces:
  - `SubscriptionPlan` (dataclass) with:
    - `tokens: dict[int, list[str]]`
    - `option_meta: pd.DataFrame` (`token, underlying, expiry, strike, side`)
    - `depth_tokens: set[str]`
    - `index_tokens: set[str]`
    - `centres: dict[tuple[str, date], float]`
    - `width: int`
    - `reduced: bool`
    - `.count() -> int`
  - `plan_subscriptions(master, spots: dict[str, float], today: date, constituents: dict[str, str], settings) -> SubscriptionPlan`
    - Both underlyings, 2 expiries each, ATM ± `strike_width`
    - Depth = ATM ± `depth_width` on each underlying's nearest expiry
    - Plus indices, VIX, current futures and constituents
  - `recenter(plan, spots, master, settings) -> tuple[SubscriptionPlan, dict[int, list[str]]]`: returns the new plan and only the newly added tokens. Never drops tokens.

- [ ] **Step 1: Write the failing tests:**
  - `test_plan_counts_and_depth`: on the fixture master with width 15, there are 31 strikes × 2 sides × 2 expiries per underlying. Depth tokens = 7 strikes × 2 sides × 2 underlyings = 28.
  - `test_plan_reduces_width_when_over_budget`: with `max_tokens_per_connection` set to 200 → `width == 10` and `reduced is True`.
  - `test_recenter_adds_only_when_moved_more_than_5_strikes`: a spot move of 5 strikes → no new tokens. 6 strikes → new tokens only for the uncovered strikes, and the old ones are still in `plan.tokens`.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement.** Exchange types: NFO → 2, BFO → 4, NSE cash → 1, BSE cash → 3.
- [ ] **Step 4: Run.** Expected: 3 passed.
- [ ] **Step 5: Commit** `feat: subscription planning and re-centring`.

---

### Task 9: Live recorder runtime

**Files:**
- Create: `quantdesk/recorder/live.py`, `tests/test_live_recorder.py`

**Interfaces:**
- Consumes:
  - `AngelClient.ltp`
  - `TickStream` (via `stream_factory`)
  - `plan_subscriptions`, `recenter`
  - `MinuteAggregator`
  - `Store`
  - `calendar.is_trading_day` (Task 15). Until then, inject `is_trading_day: Callable[[date], bool]`.
- Produces:
  - `run_recording(day, *, client, stream_factory, master, constituents, store, clock, sleep, is_trading_day, settings) -> RecordingSummary`
  - `RecordingSummary(status: str, minutes_written: int, dropped: dict, zero_quotes: int, crossed: int, stale_periods: list[tuple[datetime, datetime]], recenter_events: int, subscription_count: int, reduced: bool)`, where status is one of `"ok" | "holiday" | "no_session"`
  - `run_lock(store) -> ContextManager`, which raises `AlreadyRunningError`
  - **Storage kinds written:** `bars`, `option_snapshots`, `depth`, `opening_ticks` (every option tick 09:15–09:30, raw fields), `recorder_events` (stale periods, recentring, subscription count, reduced flag)

- [ ] **Step 1: Write the failing tests** (`FakeStream` replays scripted ticks; `FakeClock` advances):
  - `test_holiday_exits_cleanly_without_writing` [Review Focus 1]: with `is_trading_day` returning False → `status == "holiday"` and `store.read("bars")` is empty.
  - `test_second_instance_refuses` [Review Focus 3]: while `run_lock(store)` is held, a second `run_lock(store)` raises `AlreadyRunningError`.
  - `test_stale_lock_from_dead_pid_is_cleared`: a lock file containing PID 999999 (not alive) is replaced.
  - `test_records_minutes_and_flushes_each_minute`: scripted ticks from 09:15:00 to 09:17:30 → three minutes of `bars` and `option_snapshots` parts. `minutes_written == 3`. Opening ticks are stored only for 09:15–09:30.
  - `test_restart_same_day_appends`: two runs over different minute ranges → `read("bars")` contains both ranges and no file was overwritten (count the part files).
  - `test_stale_period_recorded`: a 40-second tick gap → one stale period in the summary and a `recorder_events` row.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement.**
  - Wait until 09:15 using `sleep`.
  - Fetch spots via `client.ltp` for NIFTY and SENSEX at 09:15:05.
  - Plan, subscribe, then loop: on each minute boundary, `flush` and write the three kinds. Every 60 s, run `recenter` and `add_tokens`. Stop at the session close.
  - The lock is a file `data/run/record.lock` holding the PID, checked with `os.kill(pid, 0)` in a try.
- [ ] **Step 4: Run.** Expected: 6 passed.
- [ ] **Step 5: Commit** `feat: live recorder runtime with lock, staleness and recentring`.

---

### Task 10: History backfill

**Files:**
- Create: `quantdesk/history/__init__.py`, `quantdesk/history/backfill.py`, `tests/test_backfill.py`

**Interfaces:**
- Consumes: `AngelClient.candles`, `chunk_ranges`, `Store`, settings `backfill.*`, `angel.candle_max_days`
- Produces:
  - `Target(name: str, exchange: str, token: str, interval: str, start: date)`
  - `default_targets(master, constituents: dict[str, str], settings, today: date) -> list[Target]`
    - ONE_MINUTE from 2019-01-01: NIFTY, SENSEX, INDIAVIX and each constituent
    - ONE_DAY from 2015-01-01: NIFTY, SENSEX, INDIAVIX
    - ONE_MINUTE for the current Nifty and Sensex futures, from their listing
  - `run_backfill(targets, client, store, clock, settings) -> BackfillReport`
    - Writes kind `history_<interval>` with column `target`
    - Writes a manifest of JSON lines at `data/raw/history/manifest.jsonl`, fields `{target, interval, chunk_start, chunk_end, rows, status}`, status `ok | empty | error`
  - `BackfillReport(chunks_done: int, chunks_skipped: int, errors: int, rows: int)`

- [ ] **Step 1: Write the failing tests:**
  - `test_default_targets_cover_indices_vix_constituents_daily`: with 3 constituents → 3 + 3 + 3 + 2 targets with the right intervals and starts.
  - `test_resume_skips_ok_chunks`: a manifest marks the first chunk `ok` → the second run calls `candles` only for the remaining chunks.
  - `test_error_chunk_recorded_and_run_continues`: one chunk raises `AngelApiError` → status `error` and later chunks still run. `errors == 1`.
  - `test_empty_chunk_marked_empty`: an empty DataFrame → status `empty`, nothing appended.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement.** Iterate targets × `chunk_ranges`. Skip chunks whose manifest status is `ok` or `empty`.
- [ ] **Step 4: Run.** Expected: 4 passed.
- [ ] **Step 5: Commit** `feat: resumable 1-minute history backfill`.

---

### Task 11: NSE and BSE F&O bhavcopy (fetch, parse, backfill)

**Files:**
- Create: `quantdesk/eod/__init__.py`, `quantdesk/eod/bhavcopy.py`, `tests/test_bhavcopy.py`
- Create fixtures:
  - `tests/fixtures/nse_fo_udiff_sample.zip`: a CSV with UDiFF headers `TradDt,BizDt,Sgmt,Src,FinInstrmTp,FinInstrmId,ISIN,TckrSymb,SctySrs,XpryDt,FininstrmActlXpryDt,StrkPric,OptnTp,FinInstrmNm,OpnPric,HghPric,LwPric,ClsPric,LastPric,PrvsClsgPric,UndrlygPric,SttlmPric,OpnIntrst,ChngInOpnIntrst,TtlTradgVol,TtlTrfVal,TtlNbOfTxsExctd,SsnId,NewBrdLotQty,Rmks,Rsvd1,Rsvd2,Rsvd3,Rsvd4` and 4 rows: NIFTY IDO CE/PE, NIFTY IDF, one STO
  - `tests/fixtures/bse_fo_udiff_sample.csv`: same headers, SENSEX rows
  - `tests/fixtures/nse_block_page.html`
- Modify: `config/settings.yaml`, adding:

```yaml
urls:
  nse_home: https://www.nseindia.com
  nse_fo_bhavcopy: https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{yyyymmdd}_F_0000.csv.zip
  bse_fo_bhavcopy: https://www.bseindia.com/download/Bhavcopy/Derivative/BhavCopy_BSE_FO_0_0_0_{yyyymmdd}_F_0000.CSV
  nse_participant_oi: https://nsearchives.nseindia.com/content/nsccl/fao_participant_oi_{ddmmyyyy}.csv
  nse_fii_dii: https://www.nseindia.com/api/fiidiiTradeReact
  nse_nifty50_list: https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv
```

**Interfaces:**
- Consumes: `PoliteSession`, `looks_like_html`, `BadDownloadError`, `Store`
- Produces:
  - `NotPublishedError(Exception)`
  - `fetch_nse_fo_bhavcopy(session, store, day) -> Path`
  - `fetch_bse_fo_bhavcopy(session, store, day) -> Path`
    - HTTP 404 → `NotPublishedError`
    - HTML content → `BadDownloadError`, and nothing is written
    - If the raw file already exists, return it without a download
  - `parse_fo_bhavcopy(path: Path) -> pd.DataFrame` (zip or csv) with normalised columns `date, symbol, instrument (IDO|IDF|STO|STF), expiry, strike, option_type, open, high, low, close, settle, underlying, oi, chg_oi, volume`
  - `backfill_bhavcopy(session, store, start: date, end: date, trading_days: Iterable[date], sleep) -> dict[date, str]`, with values `ok | not_published | bad_download | skipped_existing`

- [ ] **Step 1: Write the failing tests:**
  - `test_parse_nse_udiff_columns_and_types`: 4 rows; the NIFTY IDO CE row has `strike == 22550.0`, `option_type == "CE"`, `expiry == date(2026,10,20)`, `oi` int.
  - `test_parse_bse_csv_same_schema`: the column sets are equal.
  - `test_html_block_page_raises_bad_download_and_writes_nothing` [Review Focus 4]: FakeHttp returns status 200 with the block page → `BadDownloadError`, and `store.raw_exists("nse_fo", day, ...)` is False.
  - `test_404_raises_not_published`.
  - `test_backfill_skips_existing_and_records_status`.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement.** Call `session.bootstrap(nse_home)` once per run before NSE archive downloads.
- [ ] **Step 4: Run.** Expected: 5 passed.
- [ ] **Step 5: Commit** `feat: NSE/BSE F&O bhavcopy fetch, parse, backfill`.

---

### Task 12: Participant OI, FII/DII, Nifty 50 list, EOD orchestration

**Files:**
- Create: `quantdesk/eod/flows.py`, `tests/test_flows.py`, `tests/fixtures/fao_participant_oi_sample.csv`, `tests/fixtures/fiidii_sample.json`, `tests/fixtures/ind_nifty50list_sample.csv`

**Interfaces:**
- Consumes: Task 11 items, `nifty50_symbols`, `AngelClient.candles` (VIX ONE_DAY)
- Produces:
  - `fetch_participant_oi(session, store, day) -> Path`
  - `parse_participant_oi(path) -> pd.DataFrame`, one row per client type (`Client, DII, FII, Pro, TOTAL`), columns snake_cased from the CSV header row, which is the second line of the file
  - `fii_index_futures_long_ratio(df) -> float` = FII `future_index_long` / (`future_index_long` + `future_index_short`)
  - `fetch_fii_dii(session, store, day) -> Path`
  - `parse_fii_dii(path) -> pd.DataFrame` with columns `date, category (FII|DII), buy, sell, net` (₹ crore)
  - `run_eod(day, *, session, store, client, clock, sleep, settings, until: time) -> EodReport`
    - Items: `nse_fo, bse_fo, participant_oi, fii_dii, vix_daily, nifty50_list`
    - Each item is retried hourly until `until` while `not_published`. It never raises.
  - `EodReport(status: dict[str, str])`

- [ ] **Step 1: Write the failing tests:**
  - `test_parse_participant_oi_rows_and_ratio`: in the fixture, FII long 120000 and short 280000 → ratio 0.30.
  - `test_parse_fii_dii_net_values`.
  - `test_run_eod_retries_not_published_until_deadline`: participant OI returns 404 until 21:00 on the fake clock, then succeeds → status `ok`, with 2 hourly sleeps recorded.
  - `test_run_eod_marks_missing_after_deadline`: always 404 → status `not_published` at 23:00, and the other items are still `ok`.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run.** Expected: 4 passed.
- [ ] **Step 5: Commit** `feat: participant OI, FII/DII and EOD orchestration`.

---

### Task 13: Macro collector (OpenBB lean + yfinance)

**Files:**
- Create: `quantdesk/macro/__init__.py`, `quantdesk/macro/sources.py`, `quantdesk/macro/collect.py`, `tests/test_macro.py`
- Modify: `config/settings.yaml`, adding a `macro:` section (below)

```yaml
macro:
  daily_times: ["07:30", "18:30"]
  intraday_every_minutes: 5
  intraday_window: ["09:00", "15:30"]
  intraday_tickers: ["ES=F", "NQ=F", "INR=X", "BZ=F", "^N225", "^HSI"]
  series:
    - {id: brent, source: yfinance, symbol: "BZ=F"}
    - {id: usdinr, source: yfinance, symbol: "INR=X"}
    - {id: dxy, source: yfinance, symbol: "DX-Y.NYB"}
    - {id: es, source: yfinance, symbol: "ES=F"}
    - {id: nq, source: yfinance, symbol: "NQ=F"}
    - {id: spx, source: yfinance, symbol: "^GSPC"}
    - {id: n225, source: yfinance, symbol: "^N225"}
    - {id: hsi, source: yfinance, symbol: "^HSI"}
    - {id: kospi, source: yfinance, symbol: "^KS11"}
    - {id: nifty_yf, source: yfinance, symbol: "^NSEI"}
    - {id: sensex_yf, source: yfinance, symbol: "^BSESN"}
    - {id: banknifty_yf, source: yfinance, symbol: "^NSEBANK"}
    - {id: indiavix_yf, source: yfinance, symbol: "^INDIAVIX"}
    - {id: us10y, source: openbb_federal_reserve_treasury, field: year_10}
    - {id: dgs10, source: openbb_fred, symbol: DGS10}
    - {id: dexinus, source: openbb_fred, symbol: DEXINUS}
    - {id: brent_fred, source: openbb_fred_brent}
    - {id: india_cpi_oecd, source: openbb_oecd_cpi, country: india}
    - {id: india_gdp_oecd, source: openbb_oecd_gdp_real, country: india}
    - {id: india_rates_oecd, source: openbb_oecd_rates, country: india}
    - {id: india_cpi_imf, source: openbb_imf_cpi, country: IND}
    - {id: econ_calendar, source: openbb_nasdaq_calendar}
    - {id: india_gsec10y, source: fbil}
    - {id: nifty_fundamentals, source: nse_index_fundamentals}
```

**Interfaces:**
- Consumes: `Store`, `get_secret("FRED_API_KEY")`, `PoliteSession`
- Produces:
  - `FETCHERS: dict[str, Callable[[dict, date, date], pd.DataFrame]]`, one per `source` value above
    - OpenBB imports happen inside each OpenBB fetcher, so tests do not need OpenBB installed.
    - The FRED key is set via `obb.user.credentials.fred_api_key`.
    - Every fetcher returns columns `series_id, date, value` (the calendar returns its native columns plus `series_id`).
  - `run_macro_daily(day, *, store, fetchers=FETCHERS, settings, sleep) -> MacroReport`
    - Writes kinds `macro_daily` and `econ_calendar`
    - Status per series: `ok | missing_key | failed` (2 retries)
    - Never raises
  - `run_macro_intraday(now, *, store, fetch_intraday, settings) -> MacroReport`
    - Writes kind `macro_intraday` at a 5-minute interval for `intraday_tickers`
  - `MacroReport(status: dict[str, str])`

- [ ] **Step 1: Install the macro extra.**
  - Run `.venv/Scripts/python -m pip install -e ".[macro]"`, then `set OPENBB_AUTO_BUILD=false` and `.venv/Scripts/openbb-build`.
  - Expected: `.venv/Scripts/python -c "from openbb import obb; print(hasattr(obb,'fred'))"` prints `True`.
  - **If the resolver conflicts with pandas 3:** create `.venv-macro` for OpenBB only. Run `collect.py`'s OpenBB fetchers through a subprocess (`.venv-macro/Scripts/python -m quantdesk.macro.openbb_worker <source> <json-params>`) that prints CSV to stdout. Record this decision in `docs/decisions.md`.
- [ ] **Step 2: Write the failing tests** (fake fetchers injected; no network):
  - `test_daily_run_writes_rows_and_status_ok`: 3 fake series → `macro_daily` has 3 series and all statuses are `ok`.
  - `test_failing_series_retried_twice_then_failed_others_continue`: one fetcher always raises → its status is `failed` after 2 retries, and the others are `ok`.
  - `test_fred_series_missing_key_marked`: no `FRED_API_KEY` in the env → `dgs10` status `missing_key`, and no OpenBB import is attempted.
  - `test_yfinance_normaliser_converts_index_to_ist_date`: a fake yfinance frame with a UTC index → `date` column of type `date` in IST.
  - `test_intraday_writes_only_configured_tickers`.
- [ ] **Step 3: Run.** Expected: FAIL.
- [ ] **Step 4: Implement.**
  - `fbil` and `nse_index_fundamentals` fetch through `PoliteSession`. Their URLs go in `urls:` as `fbil_gsec` and `nse_index_pe`.
  - **If either URL cannot be confirmed during Task 18, the fetcher raises `NotImplementedError("url unverified")`**, and the run marks that series `failed` without affecting the others.
- [ ] **Step 5: Run.** Expected: 5 passed.
- [ ] **Step 6: Commit** `feat: macro collector with OpenBB lean providers and yfinance`.

---

### Task 14: India news collector

**Files:**
- Create: `quantdesk/news/__init__.py`, `quantdesk/news/collect.py`, `config/news_feeds.yaml`, `tests/test_news.py`, `tests/fixtures/rss_sample.xml`
- `config/news_feeds.yaml` uses the URLs verified live on 6 Oct 2026 (research note `sentiment_signals.md`):

```yaml
feeds:
  - {name: et_markets, url: "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"}
  - {name: et_economy, url: "https://economictimes.indiatimes.com/news/economy/rssfeeds/1373380680.cms"}
  - {name: bs_markets, url: "https://www.business-standard.com/rss/markets-106.rss"}
  - {name: mint_markets, url: "https://www.livemint.com/rss/markets"}
  - {name: ndtv_profit, url: "https://feeds.feedburner.com/ndtvprofit-latest"}
  - {name: nse_announcements, url: "https://nsearchives.nseindia.com/content/RSS/Online_announcements.xml"}
  - {name: bse_notices, url: "https://www.bseindia.com/data/xml/notices.xml"}
  - {name: rbi_press, url: "https://www.rbi.org.in/pressreleases_rss.xml"}
  - {name: pib_economy, url: "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3"}
gdelt_lastupdate: "https://data.gdeltproject.org/gdeltv2/lastupdate.txt"
schedule: {active: ["07:00", "19:30"], active_every_minutes: 5, idle_every_minutes: 60}
excluded: ["moneycontrol (RSS stale since Apr 2024)"]
```

**Interfaces:**
- Consumes: `Store`, `PoliteSession`, `is_trading_day` (injected)
- Produces:
  - `is_price_restatement(title: str) -> bool`
    - True when the title names Sensex/Nifty/Bank Nifty/"market(s)" **and** has a number followed by `pts|points|%` **and** a move verb (`tanks|jumps|surges|falls|slips|rises|gains|ends|closes|crashes|rallies|sheds|climbs|drops`).
  - `poll_once(feeds, *, http_get, store, clock, seen: SeenIndex) -> PollReport`
    - Saves raw XML per feed per poll as `news/<date>/<feed>-<HHMMSS>.xml`.
    - Appends new items to kind `news` with columns `item_id (sha1 of link), title_hash, feed, title, link, summary, pub_date, first_seen, price_restatement`.
  - `SeenIndex(path)`: a persistent set of `item_id` and `title_hash` in `data/state/news_seen.txt`
  - `PollReport(new_items: dict[str, int], failed: list[str], stale: list[str])`. `stale` lists feeds whose newest `pub_date` is older than 24 h.
  - `poll_gdelt_once(...)`: downloads the latest GKG zip referenced by `lastupdate.txt`, keeps rows whose themes/locations mention India and economy/markets, and appends kind `news_gdelt`.
  - `run_news_loop(*, poll, clock, sleep, is_trading_day, settings) -> None`: every 5 minutes 07:00–19:30 on trading days, hourly otherwise.

- [ ] **Step 1: Write the failing tests:**
  - `test_restatement_tagger`: these are True:
    - "Sensex tanks 800 points as banks drag"
    - "Nifty ends 1.2% higher"

    These are False:
    - "RBI hikes repo rate by 25 bps"
    - "Infosys Q2 profit rises 8%" (no index named)
  - `test_first_seen_uses_poll_time_and_dedupes`: polling the same fixture twice → items appended once. `first_seen` equals the fake clock time of the first poll; `pub_date` is kept separately.
  - `test_failing_feed_does_not_stop_others`: one feed's `http_get` raises → it is listed in `failed` and the other feeds' items are stored.
  - `test_stale_feed_flagged`: every item older than 24 h → the feed is in `stale`.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement** with `feedparser.parse(bytes)`.
- [ ] **Step 4: Run.** Expected: 4 passed.
- [ ] **Step 5: Commit** `feat: India news collector with first-seen timestamps`.

---

### Task 15: Event calendar and trading days

**Files:**
- Create: `quantdesk/calendar/__init__.py`, `quantdesk/calendar/events.py`, `config/events.yaml`, `tests/test_events.py`

**Interfaces:**
- Produces:
  - `Event(date: date, time: time | None, type: str, gate: str, title: str, source_url: str)`
    - `type` ∈ `{rbi_mpc, budget, election_results, us_fomc, us_cpi, us_nfp, index_rebalance, results, holiday_nse, holiday_bse}`
    - `gate` ∈ `{E0, E1, E2, E3}`
  - `load_events(path) -> list[Event]`. Raises `EventValidationError` listing **every** bad entry (missing or non-https `source_url`, unknown type or gate, unparseable date).
  - `is_trading_day(day: date, events: list[Event], exchange: str = "NSE") -> bool`: weekday and not a matching holiday.
  - `trading_days(start, end, events, history_days: set[date] | None = None) -> list[date]`. For past dates, when `history_days` (dates with an index daily candle) is given, it is authoritative.
  - `events_on(day, events) -> list[Event]`

- [ ] **Step 1: Seed `config/events.yaml`** with only entries that carry a verifiable source:
  - **2026 NSE trading holidays**: fetched from `https://www.nseindia.com/api/holiday-master?type=trading` through `PoliteSession`, with that URL as `source_url`.
  - **RBI MPC decision 2026-10-07 10:00 (E2)**: source `https://www.business-standard.com/amp/economy/news/rbi-s-panel-starts-monetary-policy-deliberations-0-25-bps-rate-hike-likely-126100500635_1.html`.
  - **US FOMC 2026-10-28 (E1)**: source = the Federal Reserve FOMC calendar page `https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm`.
  - **If the NSE holiday API is unreachable**, leave holidays out. The Task 18 smoke run adds them, and Task 9 still works because the owner can see the `holiday` status.
- [ ] **Step 2: Write the failing tests:**
  - `test_missing_source_url_rejected_with_all_errors_listed`: a YAML with 2 bad entries → the error message names both entries.
  - `test_weekend_and_holiday_not_trading`: Saturday → False; a listed `holiday_nse` date → False; the next weekday → True.
  - `test_history_days_authoritative_for_past`: a weekday missing from `history_days` → excluded.
  - `test_seed_file_is_valid`: `load_events(Path("config/events.yaml"))` raises nothing.
- [ ] **Step 3: Run.** Expected: FAIL.
- [ ] **Step 4: Implement.**
- [ ] **Step 5: Run.** Expected: 4 passed.
- [ ] **Step 6: Commit** `feat: event calendar with mandatory sources`.

---

### Task 16: Daily health report

**Files:**
- Create: `quantdesk/quality.py`, `tests/test_quality.py`

**Interfaces:**
- Consumes:
  - `Store` kinds (`bars`, `option_snapshots`, `recorder_events`, `news`)
  - the backfill manifest
  - the reports for kinds `recording`, `eod`, `macro`, `news`, `backfill`, saved with `Store.write_report` by the CLI (Task 17) after each command
  - `is_trading_day`
- Produces:
  - `build_health_report(day, *, store, events, settings) -> dict` with keys:
    - `date`, `trading_day`, `minutes_expected` (375 or 0)
    - `minutes_recorded` (per index token)
    - `option_tokens_recorded`, `crossed_quotes`, `zero_quotes`, `dropped_ticks`
    - `stale_periods`, `recenter_events`, `subscription_count`, `reduced_window`
    - `news_items_per_feed`, `stale_feeds`
    - `macro_status`, `eod_status`
    - `backfill_progress` (`{done, errors}` from the manifest)
    - `problems` (list of human-readable strings)
  - `write_health_report(report, store) -> Path`: writes `data/reports/health/<date>.json`

- [ ] **Step 1: Write the failing tests:**
  - `test_full_day_no_problems`: synthetic store with 375 minutes and no stale periods → `problems == []`.
  - `test_missing_minutes_reported`: 370 minutes → `problems` contains `"NIFTY: 5 minutes missing"`.
  - `test_holiday_report_expects_zero_minutes`: `trading_day False` → `minutes_expected == 0` and no "missing" problem.
  - `test_eod_and_macro_failures_listed`: an EOD status `not_published` for `participant_oi` and a macro `failed` → both appear in `problems`.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run.** Expected: 4 passed.
- [ ] **Step 5: Commit** `feat: daily data health report`.

---

### Task 17: App wiring and CLI

**Files:**
- Create: `quantdesk/app.py`, `tests/test_cli.py`
- Modify: `quantdesk/cli.py` (replace the stub)

**Interfaces:**
- Consumes: everything above
- Produces:
  - `build_app(settings) -> App`. A dataclass holding the real `AngelClient.from_env`, `Store`, `SystemClock`, `time.sleep`, `PoliteSession`, the loaded events, the fetchers and the stream factory. Constructed lazily, so `status` works without Angel credentials.
  - `cli.main(argv: list[str] | None = None) -> int`, using argparse subcommands:
    - `login-check`: logs in, prints the client name from `profile()` and "session ok". Exit 0.
    - `record`: runs `run_recording` for today, prints the summary, then writes the health report.
    - `backfill --what history|bhavcopy|fundamentals [--start YYYY-MM-DD]`
    - `eod [--day YYYY-MM-DD] [--until HH:MM]`
    - `macro [--intraday]`. `--intraday` loops every 5 minutes inside the 09:00–15:30 window.
    - `news [--once]`
    - `status [--day YYYY-MM-DD]`: prints the health report summary and backfill progress.
  - **Missing secrets:** print `Missing secret(s): ANGEL_API_KEY, ... — copy .env.example to .env and fill them in.` and return 2. Names only.
  - After each command, the CLI saves the command's report dataclass with `Store.write_report(<kind>, day, dataclasses.asdict(report))`. Kinds: `recording`, `eod`, `macro`, `news`, `backfill`.
  - `App.constituents(day) -> dict[str, str]`: symbol → NSE token. Built from the newest `nifty50_list` raw file (Task 12) via `nifty50_symbols` and `equity_tokens`. If none exists yet, fetch it once through `PoliteSession`.

- [ ] **Step 0: Add a test** `test_record_saves_recording_report`: with a fake `run_recording` returning a summary → `store.read_report("recording", day)["status"] == "ok"`.

- [ ] **Step 1: Write the failing tests** (monkeypatch `build_app` to return fakes):
  - `test_unknown_command_exits_nonzero`
  - `test_missing_secrets_message_lists_names_not_values`: env has `ANGEL_PIN=1234` but other secrets are missing → exit code 2. The output names the missing variables and does not contain `1234`.
  - `test_status_prints_health_summary`: a fake store with a health report → stdout contains `minutes_recorded` and `problems`.
  - `test_backfill_dispatches_what`: `--what bhavcopy` calls `backfill_bhavcopy` and not `run_backfill`.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the full suite** `.venv/Scripts/python -m pytest -v`. Expected: all tests pass and the live tests are skipped.
- [ ] **Step 5: Commit** `feat: CLI and app wiring`.

---

### Task 18: Live smoke run, open items, runbook

Needs the owner's `.env` with the six secrets. The owner must create the file. Never paste values into chat.

**Files:**
- Create: `tests/test_live_smoke.py` (all `@pytest.mark.live`), `docs/runbook.md`
- Modify: `docs/superpowers/specs/...design.md` §9 (mark settled items), `docs/decisions.md`, `config/settings.yaml` (correct any value the smoke run disproves), `config/events.yaml` (holidays if not added in Task 15)

- [ ] **Step 1: Write the live smoke tests.**
  - `test_live_login`: `login-check` returns 0.
  - `test_live_master_index_tokens`:
    - The master contains the three index tokens from settings.
    - A NIFTY OPTIDX strike divides cleanly by 50 after /100 scaling.
    - The NIFTY and SENSEX OPTIDX `lotsize` are 65 and 20.
  - `test_live_candles_one_day`: 375 ONE_MINUTE rows for NIFTY on the last trading day.
  - `test_live_ws_tick_scale`: one SnapQuote tick for the NIFTY current future has an `ltp` within 2% of `ltp()` (confirms the paise conversion).
- [ ] **Step 2: Run** `.venv/Scripts/python -m pytest -m live -v` with the owner's `.env` present. Expected: 4 passed. Correct the settings and code for any failure, re-run, then commit.
- [ ] **Step 3: Answer the open items from spec §9 and record them in §9 and `docs/decisions.md`.**
  1. Does `candles` return data for an expired futures token, if any appears in `searchScrip`? If not, record "VWAP from constituent volume in SP2".
  2. What is the max tokens per websocket connection? Subscribe in batches of 100 until an error or 1,000, and record the number in `recorder.max_tokens_per_connection`.
  3. Record the Sensex lot size and the tick sizes from the master.
- [ ] **Step 4: Full-session check.**
  - Run `python -m quantdesk record` on the next trading day 09:00–15:30, then `python -m quantdesk status`.
  - Expected: `minutes_recorded` NIFTY 375 (±2 at the open), `problems` empty or explained.
  - Also run `eod`, `macro` and `news --once`, and check that their statuses are `ok`, or `failed` with a recorded reason for an unverified URL.
- [ ] **Step 5: Write `docs/runbook.md`.**
  - The daily commands and their times:
    - `record` 08:55
    - `macro --intraday` 08:58
    - `news` 06:55 (loops)
    - `eod` 18:35
    - `macro` 07:30 and 18:35
  - Windows Task Scheduler entries: one task per command, action `"<repo>\.venv\Scripts\python.exe" -m quantdesk <cmd>`, start in `<repo>`, Monday–Friday.
  - How to read the health report.
  - What to do on `holiday`, `bad_download` and `missing_key`.
- [ ] **Step 6: Commit and push** `docs: SP1 smoke results, open items settled, runbook`. Run `git push`.

---

## Self-review notes

**Spec §5 coverage:**

| Spec item | Task |
|---|---|
| 5.3 broker | 4, 5 |
| 5.4 instruments | 6 |
| 5.5 recorder | 7, 8, 9 |
| 5.6 backfill | 10 |
| 5.7 EOD | 11, 12 |
| 5.7a macro | 13 |
| 5.7b news | 14 |
| 5.8 calendar | 15 |
| 5.9 storage and quality | 2, 16 |
| 5.10 commands | 17 |
| 5.11 error handling | spread across tasks, each with tests |
| 5.12 testing | every task |
| §9 items 1–3 | 18 |
| §9 item 10 (OpenBB install) | 13 Step 1 |

**Deferred out of SP1, by design:**
- Latency fields for alert and fill times: SP3. SP1 stores exchange and receive timestamps (Task 5/7).
- Fundamentals backfill (`backfill --what fundamentals`) uses the `nse_index_fundamentals` fetcher from Task 13.
