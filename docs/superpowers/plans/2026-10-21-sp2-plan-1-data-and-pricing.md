# SP2 Plan 1: Derived Data, Volatility and Option Pricing — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the derived data layer, then build the volatility model, the business-time clock and option pricing that every later part reads.

**Architecture:** Each builder reads `data/raw` through `Store` and writes one table to `data/derived` through `DerivedStore`, with an `available_at` column (design §4–§5). An `AsOf` reader refuses future rows. The pricing code is pure functions plus frozen YAML files fitted on 2019–2022 (design §6–§8).

**Tech Stack:**
- Python 3.11, pandas 3, numpy, scipy, DuckDB, pyarrow, PyYAML, pytest
- no sklearn or statsmodels

**Spec:** `docs/superpowers/specs/2026-10-21-sp2-detailed-design.md`, which argues from `docs/superpowers/specs/2026-10-06-nifty-sensex-options-signal-system-design.md` §6.0–§6.4. Numbers come from `research/hypotheses.yaml`.

## Global Constraints

- Every number comes from `research/hypotheses.yaml` via `quantdesk.validation.hypotheses.param(h, key)`. Add a missing value there, with `source` and `provenance`, before using it.
- Tests are offline. They never read `data/`. Build small frames inside the test. Run them with `.venv\Scripts\python -m pytest -q`.
- **Times:**
  - All timestamps are tz-aware `Asia/Kolkata`; use `quantdesk.clock.IST`.
  - In DuckDB, convert with `timezone('Asia/Kolkata', ts)` before casting to time.
- **Data folders:** `data/raw` is never edited. Derived tables are rebuilt whole by `DerivedStore.write_frame`, `write_query` or `write_parts`.
- **Git:**
  - One branch for this plan, `sp2/plan-1`. Commits start with `feat:`, `fix:` or `docs:`, with no Claude attribution.
  - Fast-forward `main` when the whole suite passes.
- **No P&L.** Nothing in this plan computes strategy profit.

## Review Focus

1. **Untraded bhavcopy rows** (volume 0 but a close and settle present) must never enter an IV, skew or clock fit. Pinned in Task 5 (`traded` flag) and Task 12 (fit filters).
2. **Holiday-shifted expiries.** `XpryDt` differs from `FininstrmActlXpryDt`, as with the 10 Nov → 9 Nov 2026 weekly. The expiry used must be the actual one. Pinned in Task 4.
3. **A trading day with no bhavcopy file** (NSE's legacy archive lacks 2021-03-30) must not break the expiry lookup. Use the last earlier file. Pinned in Task 5.
4. **Members with no bars:**
   - HDFC Ltd until July 2023
   - JIOFIN before its August 2023 listing

   `members_present` < `members_total` with no crash and no filling. Pinned in Task 6.
5. **Macro values refetched with a different value** for the same date. The latest `stored_on` wins. Pinned in Task 3.

---

### Task 1: Register the remaining parameters and declare dependencies

**Files:**
- Modify: `research/hypotheses.yaml` (append under `parameters:`)
- Modify: `pyproject.toml` (add `numpy` and `scipy` to `dependencies`)
- Test: `tests/test_hypotheses.py`

**Interfaces:**
- Produces: these parameter keys, readable via `param(h, key)`:

```
event.rebalance_hard_exit = "15:00"
planning.stop_horizon_min = 15
planning.target_horizon_min = 60
fill.sign_flip_check_min = 3
exit.x0_stall_min = 45
exit.x0_deadline_min = 90
macro.score_terms = "post_holiday_fade + fii_flip"
macro.fii_flip_window = 5
shock.cusum_sigma_window = 250
shock.cusum_block = 20
shock.cusum_resamples = 1000
clock.weight_winsor_q = 0.999
pricing.forward = "F = S, r = 0"
pricing.skew_floor = 0.5
pricing.skew_max_abs_z = 3
har.overnight_c = 1.0e-8
har.percentile_min = 60
gate.vol_rich_reference_time = "09:45"
gate.dsr_sr_sd_floor = 0.04
cv.embargo_both_sides = true
options_score.strike_steps = 10
options_score.rr_delta = 0.25
meta.calibration_split = 0.8
alert.entry_limit_ticks = 2
alert.backstop_limit = "max(10% of trigger, 5 ticks)"
```

- [ ] **Step 1: Write the failing test**

```python
NEW_KEYS = ["event.rebalance_hard_exit", "planning.stop_horizon_min", "planning.target_horizon_min",
            "fill.sign_flip_check_min", "exit.x0_stall_min", "exit.x0_deadline_min", "macro.score_terms",
            "macro.fii_flip_window", "shock.cusum_sigma_window", "shock.cusum_block", "shock.cusum_resamples",
            "clock.weight_winsor_q", "pricing.forward", "pricing.skew_floor", "pricing.skew_max_abs_z",
            "har.overnight_c", "har.percentile_min", "gate.vol_rich_reference_time", "gate.dsr_sr_sd_floor",
            "cv.embargo_both_sides", "options_score.strike_steps", "options_score.rr_delta",
            "meta.calibration_split", "alert.entry_limit_ticks", "alert.backstop_limit"]


def test_plan_parameters_are_registered():
    h = load_hypotheses()
    assert [k for k in NEW_KEYS if k not in h["parameters"]] == []
    assert param(h, "planning.stop_horizon_min") == 15 and param(h, "har.percentile_min") == 60
    assert validate(h) == []
```

- [ ] **Step 2: Run it to verify it fails.** Run `.venv\Scripts\python -m pytest tests/test_hypotheses.py -q`. Expected: FAIL, listing the missing keys.
- [ ] **Step 3: Add the 25 entries.** Each gets `provenance: design_ruling` and `source: "SP2 detailed design §17"`. Add `"numpy>=2"` and `"scipy>=1.13"` to `pyproject.toml`.
- [ ] **Step 4: Run it to verify it passes.** Expected: PASS.
- [ ] **Step 5: Commit**

```bash
git add research/hypotheses.yaml pyproject.toml tests/test_hypotheses.py
git commit -m "feat: register the SP2 design parameters; declare numpy and scipy"
```

---

### Task 2: `daily` table (official daily OHLC)

**Files:**
- Create: `quantdesk/derived/daily.py`
- Test: `tests/test_derived_daily.py`

**Interfaces:**
- Consumes: `Store` (`quantdesk/storage.py`); `DerivedStore.write_query` (`quantdesk/derived/store.py`).
- Produces: `build_daily(store: Store, derived: DerivedStore) -> dict`. It writes table `daily` with columns `target, day (date), open, high, low, close, available_at (timestamptz = day 16:00 IST)`.

- [ ] **Step 1: Write the failing test**

```python
def test_daily_keeps_the_latest_candle_and_stamps_16_00(tmp_path):
    raw = Store(tmp_path / "raw")
    day = date(2024, 3, 4)
    ts = datetime(2024, 3, 4, 0, 0, tzinfo=IST)
    raw.append_parquet("history_one_day", day, pd.DataFrame(
        {"ts": [ts], "open": [1.0], "high": [2.0], "low": [0.5], "close": [1.5], "volume": [0], "target": ["NIFTY"]}))
    raw.append_parquet("history_one_day", day, pd.DataFrame(   # a later refetch, same day
        {"ts": [ts], "open": [1.0], "high": [2.0], "low": [0.5], "close": [1.6], "volume": [0], "target": ["NIFTY"]}))
    derived = DerivedStore(tmp_path / "d")
    build_daily(raw, derived)
    rows = derived.read("daily")
    assert len(rows) == 1 and rows.loc[0, "close"] == 1.6 and rows.loc[0, "day"] == day
    assert rows.loc[0, "available_at"] == pd.Timestamp(datetime(2024, 3, 4, 16, 0, tzinfo=IST))
```

- [ ] **Step 2: Run it to verify it fails.** Expected: ImportError for `quantdesk.derived.daily`.
- [ ] **Step 3: Implement `build_daily`.** Use the pattern of `build_minutes` (`quantdesk/derived/minutes.py`): `row_number() over (partition by target, ts order by filename desc)`, then `day = cast(timezone('Asia/Kolkata', ts) as date)` and `available_at = (day + time '16:00') at time zone 'Asia/Kolkata'`.
- [ ] **Step 4: Run it to verify it passes.**
- [ ] **Step 5: Commit** with message `feat: daily official OHLC table with available_at 16:00`.

---

### Task 3: `macro` table with availability lags

**Files:**
- Create: `quantdesk/derived/macro.py`
- Test: `tests/test_derived_macro.py`

**Interfaces:**
- Produces:
  - `MACRO_LAGS: dict[str, tuple[int, time]]`, mapping series_id to (calendar days after the value's date, IST clock time), per design §4
  - `available_at(series_id: str, d: date) -> datetime`. It raises `KeyError` for an unknown series, so every series must be classified.
  - `build_macro(store: Store, derived: DerivedStore) -> dict`, writing table `macro` with `series_id, date, value, available_at`

- [ ] **Step 1: Write the failing tests**

```python
def test_lags_follow_design_section_4():
    assert available_at("dgs10", date(2026, 10, 16)) == datetime(2026, 10, 18, 9, 0, tzinfo=IST)
    assert available_at("spx", date(2026, 10, 16)) == datetime(2026, 10, 17, 9, 0, tzinfo=IST)
    assert available_at("n225", date(2026, 10, 16)) == datetime(2026, 10, 17, 9, 0, tzinfo=IST)
    assert available_at("indiavix_yf", date(2026, 10, 16)) == datetime(2026, 10, 16, 16, 0, tzinfo=IST)
    assert available_at("india_cpi_oecd", date(2026, 8, 1)) == datetime(2026, 9, 30, 9, 0, tzinfo=IST)
    with pytest.raises(KeyError):
        available_at("no_such_series", date(2026, 10, 16))


def test_a_refetched_value_replaces_the_older_one(tmp_path):
    raw = Store(tmp_path / "raw")
    raw.append_parquet("macro_daily", date(2026, 10, 17), pd.DataFrame(
        {"series_id": ["brent"], "date": [date(2026, 10, 16)], "value": [90.0]}))
    raw.append_parquet("macro_daily", date(2026, 10, 18), pd.DataFrame(
        {"series_id": ["brent"], "date": [date(2026, 10, 16)], "value": [91.0]}))
    derived = DerivedStore(tmp_path / "d")
    build_macro(raw, derived)
    rows = derived.read("macro")
    assert rows["value"].tolist() == [91.0]
```

- [ ] **Step 2: Run them to verify they fail.**
- [ ] **Step 3: Implement.**
  - **Lag table** (`MACRO_LAGS`):
    - FRED (`dgs10`, `dexinus`, `brent_fred`): `(2, 09:00)`
    - global and Asia yfinance (`brent`, `usdinr`, `dxy`, `es`, `nq`, `spx`, `us10y`, `n225`, `hsi`, `kospi`): `(1, 09:00)`
    - Indian yfinance (`nifty_yf`, `sensex_yf`, `banknifty_yf`, `indiavix_yf`): `(0, 16:00)`
    - OECD/IMF (`india_cpi_oecd`, `india_gdp_oecd`, `india_rates_oecd`, `india_cpi_imf`): `(60, 09:00)`
  - **Build:** read via `Store.read("macro_daily")`, which already exposes `stored_on`. Keep the row with the largest `stored_on` per `(series_id, date)`. Add `available_at`, then `write_frame`.
- [ ] **Step 4: Run them to verify they pass.**
- [ ] **Step 5: Commit** with message `feat: macro table with per-series availability lags (R5)`.

---

### Task 4: Bhavcopy contract parser (actual expiry, lot)

**Files:**
- Modify: `quantdesk/eod/bhavcopy.py` (add a new function; leave `parse_fo_bhavcopy` unchanged)
- Test: `tests/test_bhavcopy.py`

**Interfaces:**
- Produces: `parse_fo_contracts(path: Path, symbols: tuple[str, ...] = ("NIFTY", "SENSEX")) -> pd.DataFrame` with columns `COLUMNS + ["lot", "turnover"]`. Only instruments IDO and IDF for `symbols` are returned. `expiry` is the **actual** expiry.

- [ ] **Step 1: Write the failing tests**

```python
def test_udiff_contracts_use_the_actual_expiry_and_board_lot(tmp_path):
    header = ("TradDt,BizDt,Sgmt,Src,FinInstrmTp,FinInstrmId,ISIN,TckrSymb,SctySrs,XpryDt,FininstrmActlXpryDt,"
              "StrkPric,OptnTp,FinInstrmNm,OpnPric,HghPric,LwPric,ClsPric,LastPric,PrvsClsgPric,UndrlygPric,"
              "SttlmPric,OpnIntrst,ChngInOpnIntrst,TtlTradgVol,TtlTrfVal,TtlNbOfTxsExctd,SsnId,NewBrdLotQty,"
              "Rmks,Rsvd1,Rsvd2,Rsvd3,Rsvd4\n")
    row = ("2026-10-19,2026-10-19,FO,NSE,IDO,1,,NIFTY,,2026-11-10,2026-11-09,22550.00,CE,X,0,0,0,120.0,0,0,"
           "22600,120.0,1000,0,650,1.0,1,F1,65,,,,,\n")
    stock = row.replace(",NIFTY,", ",RELIANCE,").replace(",IDO,", ",STO,")
    path = tmp_path / "BhavCopy_NSE_FO_20261019.csv"
    path.write_text(header + row + stock)
    rows = parse_fo_contracts(path)
    assert len(rows) == 1
    assert rows.loc[0, "expiry"] == date(2026, 11, 9) and rows.loc[0, "lot"] == 65


def test_legacy_lot_comes_from_futures_turnover():
    rows = parse_fo_contracts(FIXTURES / "fo25SEP2023bhav_sample.csv.zip")
    assert set(rows["lot"]) == {50}      # 1225664.77e5 / (124504 x 19700.5) = 49.97 -> 50
```

- [ ] **Step 2: Run them to verify they fail.**
- [ ] **Step 3: Implement `parse_fo_contracts`.**
  - Reuse the decode-and-read part of `parse_fo_bhavcopy`.
  - **UDiFF:** take `FininstrmActlXpryDt` as `expiry`, `NewBrdLotQty` as `lot` and `TtlTrfVal` as `turnover`.
  - **Legacy:**
    1. For each symbol, compute the futures lot as `VAL_INLAKH * 1e5 / (CONTRACTS * SETTLE_PR)` per futures expiry.
    2. Snap it to the nearest of `{25, 50, 75}`.
    3. Give each option the lot of the first futures expiry on or after its own expiry. If there is none, use the latest futures expiry.
- [ ] **Step 4: Run them to verify they pass**, together with the existing `parse_fo_bhavcopy` tests.
- [ ] **Step 5: Commit** with message `feat: parse_fo_contracts with actual expiry and per-contract lot (R6)`.

---

### Task 5: `options_eod`, `expiries` and `fii_ratio` tables

**Files:**
- Create: `quantdesk/derived/options.py`
- Test: `tests/test_derived_options.py`

**Interfaces:**
- Consumes:
  - `parse_fo_contracts` (Task 4)
  - `_existing(store, day, urls, exchange)` from `eod/bhavcopy.py`
  - `parse_participant_oi`, `fii_index_futures_long_ratio` from `eod/flows.py`
  - table `sessions`
- Produces:
  - `build_options_eod(store, derived, urls: dict, nifty_from: date, sensex_from: date) -> dict`: table `options_eod`, with the parsed columns plus `day, traded (bool), available_at` (next session 09:00 IST, taken from `sessions`)
  - `build_expiries(derived) -> dict`: table `expiries` with `symbol, day, expiry_1, expiry_2, lot_1, lot_2, is_expiry_day`. Rows for day d use the latest `options_eod` day strictly before d (that file is known on the morning of d).
  - `build_fii_ratio(store, derived) -> dict`: table `fii_ratio` with `day, ratio, available_at`

- [ ] **Step 1: Write the failing tests**

```python
def test_expiries_come_from_the_previous_file_and_skip_a_missing_day(tmp_path):
    derived = DerivedStore(tmp_path)
    days = [date(2021, 3, 26), date(2021, 3, 30), date(2021, 3, 31)]       # no file for 30 March
    derived.write_frame("sessions", pd.DataFrame({"day": days, "kind": "regular", "bars": 375,
                                                  "first_bar": None, "last_bar": None}))
    eod = pd.DataFrame({
        "day": [date(2021, 3, 26)] * 2 + [date(2021, 3, 31)] * 2,
        "symbol": "NIFTY", "instrument": "IDO", "option_type": "CE", "strike": 14500.0,
        "expiry": [date(2021, 4, 1), date(2021, 4, 8), date(2021, 4, 1), date(2021, 4, 8)],
        "lot": 75, "volume": 10, "traded": True})
    derived.write_frame("options_eod", eod)
    build_expiries(derived)
    e = derived.read("expiries").set_index("day")
    assert e.loc[date(2021, 3, 30), "expiry_1"] == date(2021, 4, 1)    # from the 26 March file
    assert e.loc[date(2021, 3, 31), "expiry_2"] == date(2021, 4, 8)
    assert not e.loc[date(2021, 3, 31), "is_expiry_day"]


def test_untraded_rows_are_flagged(tmp_path):
    rows = _frame_from_contracts(pd.DataFrame({"volume": [0, 5], "close": [12.0, 13.0]}))
    assert rows["traded"].tolist() == [False, True]
```

`_frame_from_contracts(df) -> df` is a small private helper in `options.py`. It adds `traded = volume > 0`, and `build_options_eod` uses it.

- [ ] **Step 2: Run them to verify they fail.**
- [ ] **Step 3: Implement.**
  - `build_options_eod`:
    - Iterate the days in `sessions`. Find the file with `_existing(store, day, urls, exchange)`: NSE for NIFTY from `nifty_from`, BSE for SENSEX from `sensex_from`.
    - Parse it with `parse_fo_contracts`, apply `_frame_from_contracts`, and concatenate.
    - `available_at` is the next session's 09:00.
    - Write it with `write_parts` by year. It is slow (1,900 files, about 30 minutes) but runs once.
  - `build_expiries`: for each day in `sessions` and each symbol:
    - take the most recent `options_eod` day before it
    - take the expiries on or after the day, sorted; the first two are `expiry_1` and `expiry_2`
    - `lot_1` and `lot_2` are the modal lot per expiry
- [ ] **Step 4: Run them to verify they pass.**
- [ ] **Step 5: Commit** with message `feat: options_eod, expiries and fii_ratio derived tables`.

---

### Task 6: `members_minute` (VWAP weights and breadth inputs)

**Files:**
- Create: `quantdesk/derived/members.py`
- Test: `tests/test_derived_members.py`

**Interfaces:**
- Consumes: `load_membership()` (`quantdesk/market/membership.py`); tables `minutes` and `sessions`.
- Produces:
  - `member_breadth(day_bars: pd.DataFrame, members: set[str], prior_value: dict[str, float]) -> pd.DataFrame`, a pure function for one day. Columns: `ts, members_total, members_present, tv, adv, dec, above_vwap, top5_ret`.
  - `build_members_minute(derived, membership) -> dict`, which loops over days and writes table `members_minute` (adding `day` and `available_at = ts + 1 min`).

- [ ] **Step 1: Write the failing tests**

```python
def bars(sym, closes, opens=None, vols=None, start=datetime(2023, 1, 2, 9, 15, tzinfo=IST)):
    n = len(closes)
    return pd.DataFrame({"target": sym, "ts": [start + timedelta(minutes=i) for i in range(n)],
                         "open": opens or closes, "high": closes, "low": closes, "close": closes,
                         "volume": vols or [100] * n})


def test_breadth_counts_traded_value_and_top5():
    day = pd.concat([bars("A", [10.0, 11.0]), bars("B", [20.0, 19.0]), bars("C", [5.0])])  # C trades once
    out = member_breadth(day, members={"A", "B", "C", "HDFC"}, prior_value={"A": 9e9, "B": 1e9, "C": 1.0})
    second = out.iloc[1]
    assert second["members_total"] == 4 and second["members_present"] == 2   # HDFC has no data; C missing
    assert second["tv"] == 11.0 * 100 + 19.0 * 100
    assert (second["adv"], second["dec"]) == (1, 1)                           # A up, B down, C flat (carried)
    expected_top5 = (9e9 * (11 / 10 - 1) + 1e9 * (19 / 20 - 1) + 1.0 * 0) / (9e9 + 1e9 + 1.0)
    assert second["top5_ret"] == pytest.approx(expected_top5)


def test_a_member_without_data_is_counted_not_filled():
    out = member_breadth(bars("A", [10.0]), members={"A", "HDFC"}, prior_value={"A": 1.0})
    assert out.iloc[0]["members_present"] == 1 and out.iloc[0]["members_total"] == 2
```

- [ ] **Step 2: Run them to verify they fail.**
- [ ] **Step 3: Implement `member_breadth`**, following design §5.1. Keep a dict of per-stock state (day_open, last_close, cum_pv, cum_v) and walk the minutes in order. That's about 375 × 50 updates a day, which is fine in Python. `build_members_minute`:
  - members are `{membership.listing(s) for s in membership.members_on(day)}`
  - `prior_value` is Σ tp·v of each stock in the previous session
  - read the day's stock bars with `derived.read("minutes", where=f"day = '{d}' and target in (...)")`
- [ ] **Step 4: Run them to verify they pass.**
- [ ] **Step 5: Commit** with message `feat: members_minute table (traded value, A/D, above-VWAP, top-5) on point-in-time members`.

---

### Task 7: `AsOf` reader (no look-ahead)

**Files:**
- Create: `quantdesk/derived/asof.py`
- Test: `tests/test_asof.py`

**Interfaces:**
- Produces:
  - `class LookAheadError(RuntimeError)`
  - `class AsOf` with `__init__(self, derived: DerivedStore, at: datetime)` and `read(self, table: str, where: str | None = None) -> pd.DataFrame`, which returns only rows with `available_at <= at`
  - `require(self, frame: pd.DataFrame) -> pd.DataFrame`, which raises `LookAheadError` if any row has `available_at > at`

- [ ] **Step 1: Write the failing tests**

```python
def test_rows_from_the_future_are_never_returned(tmp_path):
    derived = DerivedStore(tmp_path)
    t0 = datetime(2024, 3, 4, 10, 0, tzinfo=IST)
    derived.write_frame("x", pd.DataFrame({"v": [1, 2], "available_at": [t0, t0 + timedelta(minutes=1)]}))
    assert AsOf(derived, t0).read("x")["v"].tolist() == [1]


def test_require_raises_on_a_future_row(tmp_path):
    t0 = datetime(2024, 3, 4, 10, 0, tzinfo=IST)
    frame = pd.DataFrame({"available_at": [t0 + timedelta(seconds=1)]})
    with pytest.raises(LookAheadError):
        AsOf(DerivedStore(tmp_path), t0).require(frame)
```

- [ ] **Step 2: Run them to verify they fail.**
- [ ] **Step 3: Implement.** `read` adds `available_at <= TIMESTAMPTZ '<at.isoformat()>'` to the `where` clause of `DerivedStore.read`.
- [ ] **Step 4: Run them to verify they pass.**
- [ ] **Step 5: Commit** with message `feat: AsOf reader that never returns future rows (R4)`.

---

### Task 8: `derive` command

**Files:**
- Modify: `quantdesk/cli.py` (add `cmd_derive` and a parser entry `derive` with `--only <table>`)
- Test: `tests/test_cli.py`

**Interfaces:**
- Produces: `python -m quantdesk derive [--only TABLE]`. It builds, in order: minutes, sessions, daily, macro, options_eod, expiries, fii_ratio, members_minute. Then it prints the manifest's `data_hash`. It runs under `run_lock(store, "derive")`.

- [ ] **Step 1: Write the failing test.** Monkeypatch each `build_*` in `cli` to append its name to a list. Assert that `cli.main(["derive"]) == 0`, that the list is in the order above, and that `--only daily` runs only `build_daily`.
- [ ] **Step 2: Run it to verify it fails.**
- [ ] **Step 3: Implement `cmd_derive`.** `DerivedStore(project_root() / "data" / "derived")`; pass `app.settings["urls"]`, and `param(h, "backtest.nifty_from")` and `param(h, "backtest.sensex_from")` as dates.
- [ ] **Step 4: Run it to verify it passes.**
- [ ] **Step 5: Owner step.** Run `.venv\Scripts\python -m quantdesk derive` once on real data, after tonight's history backfill has added the former members. Expect about 30–60 minutes. Note `data_hash` in `docs/decisions.md`.
- [ ] **Step 6: Commit** with message `feat: derive command builds every derived table in order`.

---

### Task 9: Vectorised Black-76

**Files:**
- Create: `quantdesk/pricing/__init__.py`, `quantdesk/pricing/black76_vec.py`
- Test: `tests/test_black76_vec.py`

**Interfaces:**
- Produces, all taking numpy arrays (broadcast) or scalars, with `kind` as an array of `"call"`/`"put"` or one string:
  - `price(F, K, T, sigma, kind) -> np.ndarray`
  - `delta(F, K, T, sigma, kind) -> np.ndarray`
  - `theta_bt(F, K, T, sigma, kind) -> np.ndarray`: ∂price/∂T, positive, per unit of T

- [ ] **Step 1: Write the failing test**

```python
def test_vector_prices_match_the_scalar_model():
    F, K = np.array([100.0, 100.0, 22800.0]), np.array([100.0, 110.0, 22900.0])
    T, s = np.array([0.5, 0.2, 0.004]), np.array([0.2, 0.3, 0.14])
    for kind in ("call", "put"):
        got = price(F, K, T, s, kind)
        want = [black76(f, k, t, v, kind=kind) for f, k, t, v in zip(F, K, T, s)]
        assert np.allclose(got, want, atol=1e-10)
        got_d = delta(F, K, T, s, kind)
        want_d = [greeks(f, k, t, v, kind=kind)["delta"] for f, k, t, v in zip(F, K, T, s)]
        assert np.allclose(got_d, want_d, atol=1e-10)


def test_theta_bt_is_the_time_derivative():
    h = 1e-6
    num = (price(100.0, 100.0, 0.2 + h, 0.2, "call") - price(100.0, 100.0, 0.2 - h, 0.2, "call")) / (2 * h)
    assert theta_bt(100.0, 100.0, 0.2, 0.2, "call") == pytest.approx(num, rel=1e-6)
```

- [ ] **Step 2: Run it to verify it fails.**
- [ ] **Step 3: Implement** with `scipy.special.ndtr` as the normal CDF. Return intrinsic value where T ≤ 0 or σ ≤ 0, matching the scalar version. With r = 0, theta_bt = F·φ(d1)·σ/(2√T).
- [ ] **Step 4: Run it to verify it passes.**
- [ ] **Step 5: Commit** with message `feat: vectorised Black-76 price, delta and business-time theta`.

---

### Task 10: Garman–Klass RV and HAR

**Files:**
- Create: `quantdesk/vol/__init__.py`, `quantdesk/vol/rv.py`, `quantdesk/vol/har.py`
- Test: `tests/test_vol.py`

**Interfaces:**
- Produces:
  - `garman_klass(o, h, l, c) -> np.ndarray` (fraction²)
  - `har_design(daily: pd.DataFrame, vix: pd.DataFrame, c: float) -> pd.DataFrame`. Index: day. Columns: `y, x1..x5`, where y is ln RV of that day and the x's are known at 09:16 that day (design §6).
  - `HarFit` dataclass: `refit_day: date, beta: np.ndarray (6,), s2: float, n: int, x5_mean: float`
  - `fit_har(design: pd.DataFrame, refit_day: date, window: int) -> HarFit`. Uses rows with day < refit_day, the last `window` complete rows.
  - `forecast(fit: HarFit, row: pd.Series) -> tuple[float, float]`. Returns (RV̂, RV̂ without the gap term).
  - `har_series(daily, vix, window, c, percentile_window, percentile_min) -> pd.DataFrame`. Index: day. Columns `rv_hat, rv_hat_nogap, sigma_day, har_pct`, with refits on the first session of each month.

- [ ] **Step 1: Write the failing tests**

```python
def test_garman_klass_hand_value():
    v = garman_klass(np.array([100.0]), np.array([102.0]), np.array([99.0]), np.array([101.0]))
    expected = 0.5 * np.log(102 / 99) ** 2 - (2 * np.log(2) - 1) * np.log(101 / 100) ** 2
    assert v[0] == pytest.approx(expected)


def test_har_recovers_planted_coefficients():
    rng = np.random.default_rng(1)
    n = 900
    X = rng.normal(size=(n, 5))
    beta = np.array([-9.0, 0.4, 0.3, 0.1, 0.2, 0.05])
    y = beta[0] + X @ beta[1:] + rng.normal(scale=0.01, size=n)
    design = pd.DataFrame(X, columns=["x1", "x2", "x3", "x4", "x5"],
                          index=pd.date_range("2019-01-01", periods=n).date).assign(y=y)
    fit = fit_har(design, refit_day=design.index[-1], window=750)
    assert np.allclose(fit.beta, beta, atol=0.01)


def test_har_never_uses_the_refit_day_or_later():
    design = _toy_design(800)          # helper in the test: random x's, y
    a = fit_har(design, refit_day=design.index[760], window=750)
    changed = design.copy()
    changed.loc[design.index[760]:, "y"] += 100.0
    b = fit_har(changed, refit_day=design.index[760], window=750)
    assert np.allclose(a.beta, b.beta)
```

- [ ] **Step 2: Run them to verify they fail.**
- [ ] **Step 3: Implement.**
  - OLS with `numpy.linalg.lstsq`.
  - `forecast` returns exp(ŷ + s²/2) and the same value with x5 replaced by `x5_mean`.
  - `har_pct` is the rank of `rv_hat` among the previous 252 values. It is NaN until 60 earlier values exist.
- [ ] **Step 4: Run them to verify they pass.**
- [ ] **Step 5: Commit** with message `feat: Garman-Klass RV and monthly-refit HAR with VIX and overnight terms (R13)`.

---

### Task 11: Business-time clock (`Clock`, `BT`)

**Files:**
- Create: `quantdesk/pricing/clock.py`
- Test: `tests/test_clock.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class Clock`:
    - `minute_weights: np.ndarray` (375 values, summing to 1)
    - `theta_night: float`, `theta_weekend_day: float`, `theta_holiday: float`
    - `sessions: tuple[date, ...]`, the trading days the clock counts
  - `Clock.w_done(at: datetime) -> float`: share of `at`'s session elapsed. 0 before 09:15, 1 at or after 15:30. Interpolate linearly within the minute.
  - `Clock.bt(t0: datetime, t1: datetime) -> float`: design §7. t0 ≤ t1. Holidays are weekdays between two sessions that are not sessions.
  - `load_clock(path: Path, sessions) -> Clock` and `save_clock(path, clock, meta: dict) -> None` for the YAML at `config/frozen/clock_v1.yaml`.

- [ ] **Step 1: Write the failing tests**

```python
FLAT = np.full(375, 1 / 375)
SESS = (date(2026, 10, 16), date(2026, 10, 19), date(2026, 10, 21))   # Fri, Mon, Wed; Tue 20 Oct a holiday
CLOCK = Clock(FLAT, theta_night=0.5, theta_weekend_day=0.1, theta_holiday=0.2, sessions=SESS)


def at(d, hh, mm):
    return datetime.combine(d, time(hh, mm), tzinfo=IST)


def test_within_a_session_business_time_is_the_weight_share():
    assert CLOCK.bt(at(SESS[0], 9, 15), at(SESS[0], 15, 30)) == pytest.approx(1.0)
    assert CLOCK.bt(at(SESS[0], 12, 22), at(SESS[0], 12, 52)) == pytest.approx(30 / 375)


def test_weekends_and_holidays_add_their_weights():
    # Fri close -> Mon close: night + 2 weekend days + Monday's session
    assert CLOCK.bt(at(SESS[0], 15, 30), at(SESS[1], 15, 30)) == pytest.approx(0.5 + 2 * 0.1 + 1.0)
    # Mon close -> Wed close: night + Tuesday holiday + Wednesday's session
    assert CLOCK.bt(at(SESS[1], 15, 30), at(SESS[2], 15, 30)) == pytest.approx(0.5 + 0.2 + 1.0)


def test_a_saved_clock_loads_back(tmp_path):
    save_clock(tmp_path / "c.yaml", CLOCK, meta={"fit_window": "test"})
    again = load_clock(tmp_path / "c.yaml", SESS)
    assert again.theta_holiday == 0.2 and np.allclose(again.minute_weights, FLAT)
```

- [ ] **Step 2: Run them to verify they fail.**
- [ ] **Step 3: Implement** with the cumulative sum of `minute_weights` for `w_done`, and the BT formula in design §7.
- [ ] **Step 4: Run them to verify they pass.**
- [ ] **Step 5: Commit** with message `feat: business-time clock with minute, night, weekend and holiday weights (R15)`.

---

### Task 12: Clock fit (minute weights, θ_n, θ_w, θ_h)

**Files:**
- Create: `quantdesk/pricing/clockfit.py`
- Test: `tests/test_clockfit.py`

**Interfaces:**
- Consumes: `Clock` (Task 11); `implied_vol` (`quantdesk/black76.py`).
- Produces:
  - `fit_minute_weights(minutes: pd.DataFrame, opens: pd.Series, q: float) -> np.ndarray`, where minutes holds one index's regular-session bars
  - `fit_theta_night(daily: pd.DataFrame, sessions) -> float`
  - `atm_implied_variance(eod: pd.DataFrame, vix_close: pd.Series) -> pd.DataFrame`, with columns `day, expiry, v_tilde` (traded strikes only)
  - `fit_weekend_holiday(vt: pd.DataFrame, sessions, theta_night: float) -> dict`, with keys `theta_weekend_day, theta_holiday, se_weekend, se_holiday, n`

- [ ] **Step 1: Write the failing tests.**
  - `test_minute_weights_follow_planted_variance`: simulate 200 days in which minute m has return sd ∝ 2 for m < 15 and 1 otherwise. Assert `w[:15].sum()/w[15:30].sum() ≈ 4` within 10%, and `w.sum() == 1`.
  - `test_weekend_weight_is_recovered`: build `v_tilde` rows where each consecutive-session drop is `β0 + β1·W + β2·H`, with β0 = 1.5, β1 = 0.15, β2 = 0.3 and θ_n = 0.5. Assert `theta_weekend_day == pytest.approx(0.15 / 1.5 * 1.5)` and `theta_holiday == pytest.approx(0.3)`.
  - `test_untraded_strikes_are_ignored`: give the ATM call `traded=False` with an absurd close. Assert `atm_implied_variance` falls back to the nearest strike where both legs traded, or drops the day.
- [ ] **Step 2: Run them to verify they fail.**
- [ ] **Step 3: Implement** following design §7. Use `numpy.linalg.lstsq` for the regression, and residual-based SEs from (X'X)⁻¹s².
- [ ] **Step 4: Run them to verify they pass.**
- [ ] **Step 5: Commit** with message `feat: clock fit from intraday variance and bhavcopy implied-variance decay`.

---

### Task 13: VIX conversion and the volatility surface (R, skew, beta)

**Files:**
- Create: `quantdesk/pricing/surface.py`
- Test: `tests/test_surface.py`

**Interfaces:**
- Produces:
  - `sigma_bt(vix: float, at: datetime, clock: Clock) -> float`: design §7. The 30-day point rolls back to the previous session's 15:30 when needed.
  - `@dataclass(frozen=True) class Surface` with:
    - `r_dte: dict[int, float]` (keys 0..6, with 0 = 1's value)
    - `b1: float`, `b2: float`, `floor: float`
    - `gamma_dn: float`, `gamma_up: float`
  - `Surface.sigma(at, expiry_close: datetime, F: float, K: np.ndarray, vix: float, clock, dte: int) -> np.ndarray`, which applies R(dte) and the skew with its floor
  - `Surface.shifted(sigma_bt_value: float, move: float) -> float`, the spot–vol beta for planning
  - `fit_surface(eod, vix_close, clock, minutes_15) -> tuple[Surface, dict]`, returning the surface and a report dict
  - `save_surface` and `load_surface` for `config/frozen/surface_v1.yaml`

- [ ] **Step 1: Write the failing tests**

```python
def test_sigma_bt_inverts_a_flat_calendar():
    days = tuple(date(2026, 1, 1) + timedelta(d) for d in range(60))       # every day a session
    clock = Clock(np.full(375, 1 / 375), 0.0, 0.0, 0.0, days)
    # 30 calendar days = 30 sessions with zero night weight: sigma_bt^2 = 0.15^2 * 30/365 / 30
    assert sigma_bt(15.0, datetime(2026, 1, 2, 15, 30, tzinfo=IST), clock) == pytest.approx(
        0.15 * np.sqrt(1 / 365))


def test_skew_floor_and_atm_level():
    s = Surface(r_dte={d: 1.1 for d in range(7)}, b1=-0.5, b2=0.0, floor=0.5, gamma_dn=-3.0, gamma_up=-1.5)
    # z = ln(K/F) / (sigma_atm * sqrt(T)) = 0.02 / 0.01 = 2  ->  1 - 0.5 * 2 = 0, floored at 0.5
    out = s.sigma_from_atm(0.01, F=100.0, K=np.array([100.0, 100.0 * np.exp(0.02)]), T=1.0)
    assert out[0] == pytest.approx(0.01) and out[1] == pytest.approx(0.005)


def test_spot_vol_beta_raises_vol_on_a_fall():
    s = Surface(r_dte={d: 1.0 for d in range(7)}, b1=0, b2=0, floor=0.5, gamma_dn=-3.0, gamma_up=-1.5)
    assert s.shifted(0.01, move=-0.01) == pytest.approx(0.01 * np.exp(0.03))
```

`sigma_from_atm(atm_sigma, F, K, T)` is the skew-only helper that `sigma` calls.

- [ ] **Step 2: Run them to verify they fail.**
- [ ] **Step 3: Implement.** `fit_surface` follows design §8:
  - R(dte) = the median ATM business-time IV divided by σ_bt at 15:29, for dte 1–6
  - b1 and b2 by least squares of IV/σ_ATM − 1 on z and z², for traded strikes with |z| ≤ 3
  - γ from 15-minute windows of Δln VIX on the index return, split by the sign of the return
- [ ] **Step 4: Run them to verify they pass.**
- [ ] **Step 5: Commit** with message `feat: VIX to business-time sigma, R(dte), skew and spot-vol beta (R15, R16)`.

---

### Task 14: Quotes (`ModelQuotes`)

**Files:**
- Create: `quantdesk/pricing/quotes.py`
- Test: `tests/test_quotes.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class Quote: bid: float; ask: float; mid: float`
  - `half_spread(index: str, mid: float, at: datetime, h: dict) -> float`, with design §8 values from `param`
  - `round_up_tick(x)` and `round_down_tick(x)` to ₹0.05
  - `class QuoteSource(Protocol): def quote(self, index, expiry: date, strike: float, kind: str, at: datetime) -> Quote`
  - `class ModelQuotes`:
    - `__init__(self, frames: dict[str, pd.DataFrame], surface, clock, h)`, where frames is index → minute frame with `close` and `vix` columns
    - `quote(...)` prices from the index close and VIX at the bar stamped `at − 1 min`

- [ ] **Step 1: Write the failing tests**

```python
def test_half_spread_table_and_time_multipliers():
    h = load_hypotheses()
    t = lambda hh, mm: datetime(2026, 10, 21, hh, mm, tzinfo=IST)
    assert half_spread("NIFTY", 40.0, t(11, 0), h) == pytest.approx(0.10)
    assert half_spread("NIFTY", 60.0, t(9, 20), h) == pytest.approx(0.40)
    assert half_spread("NIFTY", 60.0, t(9, 45), h) == pytest.approx(0.30)
    assert half_spread("SENSEX", 60.0, t(14, 50), h) == pytest.approx(1.00)


def test_quotes_round_away_from_the_mid():
    assert (round_up_tick(10.01), round_down_tick(10.04)) == (10.05, 10.0)
    assert round_down_tick(0.01) == 0.05    # never below one tick
```

- [ ] **Step 2: Run them to verify they fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run them to verify they pass.**
- [ ] **Step 5: Commit** with message `feat: modelled option quotes with the spread table and tick rounding`.

---

### Task 15: Pricing check (R17)

**Files:**
- Create: `quantdesk/pricing/pricecheck.py`
- Test: `tests/test_pricecheck.py`

**Interfaces:**
- Produces:
  - `price_errors(recorded: pd.DataFrame, model_mid: Callable[[str, date, float, str, datetime], float], horizons: list) -> pd.DataFrame`
    - `recorded` has columns `minute, token, bid, ask, underlying, expiry, strike, side` (snapshots joined with `option_meta`).
    - The result has one row per (check, token, horizon), with `err = |Δmodel − Δactual| / max(|Δactual|, 2 × 0.05)`.
  - `check_result(errors: pd.DataFrame, sessions_by_index: dict, h: dict) -> dict`, returning keys `median_error, passed, sessions, expiry_days, enough_data`

- [ ] **Step 1: Write the failing tests.**
  - `test_a_perfect_model_has_zero_error`: model_mid returns the recorded mid. Assert the median error is 0.
  - `test_errors_use_a_two_tick_floor`: recorded Δ = 0, model Δ = 0.05. Assert err == 0.5.
  - `test_too_few_sessions_is_not_a_pass`: with 10 sessions, assert `enough_data is False` and `passed is False`, even at zero error.
- [ ] **Step 2: Run them to verify they fail.**
- [ ] **Step 3: Implement.**
  - Check times are the strategy grid (09:45 to 14:00, every 15 minutes).
  - Horizons are 15, 30 and 60 minutes plus "exit". Exit means 15:10, or 15:00 on expiry days.
  - Candidate strikes are those within 1.5% of the index at the check.
- [ ] **Step 4: Run them to verify they pass.**
- [ ] **Step 5: Commit** with message `feat: recorded-chain pricing check with the pre-registered metric (R17)`.

---

### Task 16: `fit` command and the frozen files

**Files:**
- Modify: `quantdesk/cli.py` (add `cmd_fit` with `fit clock|surface|shock`)
- Create (by running it): `config/frozen/clock_v1.yaml`, `config/frozen/surface_v1.yaml`, `research/pilots/CLOCK.md`
- Test: `tests/test_cli.py`

**Interfaces:**
- Produces: `python -m quantdesk fit clock` and `fit surface`.
  - Each refuses to overwrite an existing frozen file unless given `--force`, and prints a reminder that a refit must be logged in `decisions.md` (R15).
  - Each writes its report to `research/pilots/CLOCK.md`: weights plot data as a table of 15-minute sums, θs with SEs, R(dte), b1/b2, γs, and the `data_hash`.
- The `fit shock` subcommand (the CUSUM h) belongs to plan 2, Task 8. Add the parser entry here and leave it raising `NotImplementedError` until then.

- [ ] **Step 1: Write the failing test.**
  - Monkeypatch the fit functions to return fixed objects.
  - Assert that `fit clock` writes the YAML, refuses a second run, and succeeds with `--force`.
- [ ] **Step 2: Run it to verify it fails.**
- [ ] **Step 3: Implement.** Read only the rows dated 2019-01-01..2022-12-31 (`clock.fit_start`/`clock.fit_end`).
- [ ] **Step 4: Run it to verify it passes.**
- [ ] **Step 5: Owner step.** Run `fit clock`, then `fit surface`, on real data. Read `research/pilots/CLOCK.md`. Sanity ranges:
  - θ_n between 0.3 and 1.0, since research measured an overnight share of about 0.38–0.43
  - R(1) between 0.8 and 2.0
  - b1 < 0, the usual put skew

  If a value is outside its range, find the bug **before** committing. Then commit the frozen files.
- [ ] **Step 6: Commit** with message `feat: fit command; frozen clock and surface fitted on 2019-2022`.

---

## Plan 1 is done when

- `.venv\Scripts\python -m pytest -q` passes.
- `python -m quantdesk derive` has built every table, and `data_hash` is noted in `decisions.md`.
- `config/frozen/clock_v1.yaml` and `config/frozen/surface_v1.yaml` are committed, and `research/pilots/CLOCK.md` exists.
- `main` is fast-forwarded.
