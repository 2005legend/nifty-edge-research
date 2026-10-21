# SP2 Plan 2: Engines, Pipeline, Exits and Zero-Trial Pilots — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `decide()`, the pure function that turns market data up to time T into "no signal", "blocked by gate X", or an alert. Build the exit simulator next to it. Then run the pilots that cost no trials (P9, P4, P1, P2, P10) and prepare the D2 checkpoint.

**Architecture:**
- `quantdesk/analysis/` holds causal feature functions: data frames in, values out.
- `quantdesk/strategy/` holds the pipeline steps in spec order. `DayLoader` builds one day's context and minute frame from `data/derived` through `AsOf`.
- Pilots live in `quantdesk/validation/pilots/` and write markdown to `research/pilots/`.

**Tech Stack:**
- Python 3.11, pandas 3, numpy, scipy (`optimize.minimize`, `special`), pytest
- reuses plan 1's `pricing` and `vol`

**Spec:** `docs/superpowers/specs/2026-10-21-sp2-detailed-design.md` §9–§13 and §16. It argues from spec §5A and §6.1, with rulings R1–R38 in §6.4.

**Prerequisite:** plan 1 is merged, `derive` has run, and the frozen clock and surface exist.

## Global Constraints

- Same as plan 1:
  - numbers only via `param(h, key)`
  - offline tests with synthetic frames
  - IST tz-aware timestamps
  - branch `sp2/plan-2`, fast-forward to `main` when the suite passes
- **No profit on real data.** Pilots may count signals and measure index excursions. They must never compute option P&L, win rate or R. Plan 3's registry is the only way to P&L.
- `strategy/` must not import `backtest/`. SP3 will call `decide()` live.
- Every intraday feature registers in `analysis/frame.py:FEATURES`, so the truncation test covers it.

## Review Focus

1. **σ(τ) undefined.** This happens with fewer than 14 earlier sessions of the same type: early 2019, Sensex's first 2024 expiry days, or the first expiry days after a weekday change. The result must be **no signal**, not an error and not a band of 0. Pinned in Task 3.
2. **A minute with zero member traded value** (data gap or the first minute) must not divide by zero in the VWAP proxy. The VWAP stays at its last value; at the first minute it equals the typical price. Pinned in Task 2.
3. **Exits whose delayed fill would fall after the hard exit** (a stop hit at 15:09 with the 2-minute delay) exit at the hard exit, never later and never after 15:29. Pinned in Task 14.
4. **Ties between strikes or indices** at the same EV resolve deterministically: NIFTY, then the nearer expiry, then |Δ| closest to 0.40. Pinned in Task 12.
5. **A check inside an RBI block, after the last entry time, or on an irregular session** returns a named reason and never raises. Pinned in Task 11.

---

### Task 1: Types and trial configurations

**Files:**
- Create: `quantdesk/analysis/__init__.py`, `quantdesk/strategy/__init__.py`, `quantdesk/strategy/types.py`, `quantdesk/strategy/configs.py`
- Test: `tests/test_strategy_types.py`

**Interfaces:**
- Produces (all `@dataclass(frozen=True)` unless noted):
  - `ZRef(mean: float, sd: float, n: int)`
  - `DayContext`:
    - `index: str`, `day: date`, `session_kind: str`
    - `open: float`, `prev_close: float`
    - `prev_day: tuple[float, float, float]`, `prev_week: tuple[float, float, float]` (H, L, C)
    - `is_expiry_day: bool`
    - `expiry_1: date`, `expiry_2: date`, `lot_1: int`, `lot_2: int`, `dte_1: int`
    - `sigma_day: float`, `sigma_gap: float`, `har_pct: float | None`
    - `vix_prev_close: float`
    - `band_sigma: np.ndarray` (375 values, NaN where undefined)
    - `events: tuple`, `delta_parts: dict[str, float]`
    - `options_raw: dict[str, float] | None`, `macro_raw: float`
    - `vol_rich_threshold: float | None`
    - `z_refs: dict[tuple[str, str], ZRef]`, keyed by (feature, "HH:MM")
    - `hard_exit: time`
  - `Signal`:
    - `index: str`, `at: datetime`, `side: str` ("long"/"short")
    - `ref_close: float`, `upper: float`, `lower: float`, `vwap: float`
    - `stop_level: float`, `b: float`, `target_level: float`
  - `StrikeChoice`:
    - `index`, `expiry: date`, `strike: float`, `kind: str`, `lot: int`, `ask: float`, `delta: float`
    - `gain: float`, `loss: float`, `p_be: float`, `ev: float`, `kelly: float`
  - `Alert`:
    - `choice: StrikeChoice`, `side`, `at`
    - `entry_limit: float`, `index_stop: float`, `index_target: float`
    - `backstop_trigger: float`, `backstop_limit: float`
    - `p: float`, `delta: float`, `delta_parts: dict`
    - `reasons_for: tuple[str, ...]`, `reasons_against: tuple[str, ...]`
  - `Decision` (mutable dataclass):
    - `index`, `at`, `signal: Signal | None`, `failed: str | None`
    - `p: float | None = None`, `delta: float = 0.0`
    - `scores: dict = field(default_factory=dict)`
    - `choice: StrikeChoice | None = None`, `alert: Alert | None = None`
  - `TrialConfig`:
    - `trial_id: str`, `exit_policy: str` ("X0", "X1" or "X2")
    - `probability: str` ("consensus" or "meta")
    - `hurdles: frozenset[str]` (a subset of {"shock", "stress", "slow_trend", "gamma"})
  - `configs.config_for(trial_id: str, accepted: dict[str, bool]) -> TrialConfig`, following the registry:
    - B0 = (X0, consensus, ∅)
    - X1 = (X1, consensus, ∅)
    - M1 = (X1 if accepted["X1"] else X0, meta, ∅)
    - RV-2 adds "shock", RV-1 adds "stress", RV-3 adds "slow_trend", RV-4 adds "gamma"
    - Each later RV builds on the accepted predecessor set.

- [ ] **Step 1: Write the failing test**

```python
def test_registry_configs_build_on_accepted_trials():
    assert config_for("B0", {}).exit_policy == "X0"
    assert config_for("M1", {"X1": True}).exit_policy == "X1"
    assert config_for("M1", {"X1": False}).exit_policy == "X0"
    rv1 = config_for("RV-1", {"X1": True, "RV-2": True})
    assert rv1.probability == "meta" and rv1.hurdles == frozenset({"shock", "stress"})
    assert config_for("RV-1", {"X1": True, "RV-2": False}).hurdles == frozenset({"stress"})
```

- [ ] **Step 2: Run it to verify it fails.**
- [ ] **Step 3: Implement** the dataclasses and `config_for`. An unknown trial id raises `KeyError`.
- [ ] **Step 4: Run it to verify it passes.**
- [ ] **Step 5: Commit** with message `feat: SP2 strategy types and registry trial configurations`.

---

### Task 2: VWAP proxy

**Files:**
- Create: `quantdesk/analysis/vwap.py`
- Test: `tests/test_vwap.py`

**Interfaces:**
- Produces: `vwap_proxy(index_bars: pd.DataFrame, tv: pd.Series) -> pd.DataFrame`.
  - `index_bars` has columns `ts, high, low, close`. `tv` is indexed by ts; a missing ts means 0.
  - Returns columns `ts, vwap, vwap_sd` (design §9).

- [ ] **Step 1: Write the failing tests**

```python
def test_vwap_weights_index_typical_price_by_member_traded_value():
    ts = [datetime(2024, 3, 4, 9, 15 + i, tzinfo=IST) for i in range(3)]
    bars = pd.DataFrame({"ts": ts, "high": [101.0, 103.0, 105.0], "low": [99.0, 101.0, 103.0],
                         "close": [100.0, 102.0, 104.0]})
    out = vwap_proxy(bars, pd.Series([1.0, 3.0, 0.0], index=ts))
    assert out["vwap"].tolist() == pytest.approx([100.0, (100 + 3 * 102) / 4, (100 + 3 * 102) / 4])


def test_no_traded_value_at_the_open_falls_back_to_the_typical_price():
    ts = [datetime(2024, 3, 4, 9, 15, tzinfo=IST)]
    bars = pd.DataFrame({"ts": ts, "high": [101.0], "low": [99.0], "close": [100.0]})
    out = vwap_proxy(bars, pd.Series(dtype=float))
    assert out["vwap"].tolist() == [100.0] and out["vwap_sd"].tolist() == [0.0]
```

- [ ] **Step 2: Run them to verify they fail.**
- [ ] **Step 3: Implement** with cumulative sums. `vwap_sd` uses cumulative Σtv·I² − vwap²·Σtv, clipped at 0.
- [ ] **Step 4: Run them to verify they pass.**
- [ ] **Step 5: Commit** with message `feat: stock-volume VWAP proxy and band (spec §6.0)`.

---

### Task 3: Noise band and the H1 trigger

**Files:**
- Create: `quantdesk/analysis/bands.py`, `quantdesk/strategy/trigger.py`
- Test: `tests/test_bands.py`

**Interfaces:**
- Produces:
  - `slot(ts: datetime) -> int`: minutes since 09:15, from 0 to 374
  - `band_sigma(history: list[pd.DataFrame], opens: list[float], lookback: int) -> np.ndarray`
    - `history` is the earlier same-type sessions, oldest first; each frame has `ts, close`.
    - Returns 375 values, each the mean over the last `lookback` sessions of |close/open − 1| at that slot. A slot is NaN when fewer than `lookback` sessions have it.
  - `band_edges(open_: float, prev_close: float, sigma: float, v: float) -> tuple[float, float]`
  - `h1(frame: pd.DataFrame, at: datetime, ctx: DayContext, h: dict) -> Signal | None`
    - Reads the row stamped `at − 1 min`.
    - stop_level is max(upper, vwap) for a long and min(lower, vwap) for a short. b = |ref_close − stop_level|.
    - target = ref_close ± `stop.planning_target_multiple`·b.

- [ ] **Step 1: Write the failing tests**

```python
def test_band_hand_example():
    # 14 sessions; at slot 30 each closed 0.2% above its open
    hist = [pd.DataFrame({"ts": [datetime(2024, 1, d, 9, 45, tzinfo=IST)], "close": [100.2]}) for d in range(1, 15)]
    sigma = band_sigma(hist, [100.0] * 14, lookback=14)
    assert sigma[30] == pytest.approx(0.002) and np.isnan(sigma[31])
    upper, lower = band_edges(open_=101.0, prev_close=100.0, sigma=0.002, v=1.0)  # gap up
    assert (upper, lower) == pytest.approx((101.0 * 1.002, 100.0 * 0.998))


def test_thirteen_sessions_give_no_band_and_no_signal():
    hist = [pd.DataFrame({"ts": [datetime(2024, 1, d, 9, 45, tzinfo=IST)], "close": [100.2]}) for d in range(1, 14)]
    assert np.isnan(band_sigma(hist, [100.0] * 13, lookback=14)[30])


def test_h1_long_needs_close_above_band_and_vwap():
    ctx = make_ctx(band_sigma=np.full(375, 0.002), open=100.0, prev_close=100.0)   # helper in the test
    frame = make_frame(close_at_0944=100.5, vwap_at_0944=100.1)                      # upper = 100.2
    sig = h1(frame, datetime(2024, 3, 4, 9, 45, tzinfo=IST), ctx, load_hypotheses())
    assert sig.side == "long" and sig.stop_level == pytest.approx(100.2) and sig.b == pytest.approx(0.3)
    assert sig.target_level == pytest.approx(100.5 + 2.3 * 0.3)
```

- [ ] **Step 2: Run them to verify they fail.**
- [ ] **Step 3: Implement.** `h1` returns `None` when the band at that slot is NaN (R12) or no row exists at `at − 1 min`.
- [ ] **Step 4: Run them to verify they pass.**
- [ ] **Step 5: Commit** with message `feat: gap-adjusted noise band and the H1 trigger`.

---

### Task 4: Levels and breadth agreement

**Files:**
- Create: `quantdesk/analysis/levels.py`, `quantdesk/analysis/breadth.py`
- Test: `tests/test_levels_breadth.py`

**Interfaces:**
- Produces:
  - `round_levels(lo: float, hi: float, step: int) -> list[float]`
  - `multi_touch(frame: pd.DataFrame, upto: datetime, tol: float, min_touches: int, min_gap_min: int) -> tuple[float | None, float | None]` (resistance, support)
  - `opposing_levels(ctx: DayContext, frame: pd.DataFrame, signal: Signal, h: dict) -> list[float]`: levels strictly between ref_close and target_level
  - `nearest_opposing_distance(ctx, frame, signal, h) -> float`: distance to the nearest opposing level beyond ref_close, in points. It is `inf` when there is none within 3·b.
  - `breadth_agrees(row: pd.Series, side: str, min_agree: int) -> bool`. `row` has `adv_share`, `above_share` and `top5_ret`.

- [ ] **Step 1: Write the failing tests**

```python
def test_round_levels_and_opposing_levels():
    assert round_levels(22_850.0, 23_120.0, 100) == [22_900.0, 23_000.0, 23_100.0]


def test_a_session_high_touched_twice_three_minutes_apart_is_resistance():
    closes = [100.0, 100.5, 100.2, 100.1, 100.0, 100.49]       # 100.5 at 09:16 and 100.49 at 09:20
    frame = minute_frame_from(closes)                            # helper: ts from 09:15, high = close
    res, sup = multi_touch(frame, upto=frame.ts.iloc[-1], tol=0.0005, min_touches=2, min_gap_min=3)
    assert res == pytest.approx(100.5) and sup is None


def test_breadth_needs_two_of_three():
    row = pd.Series({"adv_share": 0.2, "above_share": 0.6, "top5_ret": -0.001})
    assert breadth_agrees(row, "long", 2) and not breadth_agrees(row, "short", 2)
```

- [ ] **Step 2: Run them to verify they fail.**
- [ ] **Step 3: Implement** following design §9. Prior day and prior week H/L/C come from `ctx.prev_day` and `ctx.prev_week`.
- [ ] **Step 4: Run them to verify they pass.**
- [ ] **Step 5: Commit** with message `feat: level map (round, prior day/week, multi-touch) and breadth agreement`.

---

### Task 5: Causal z-scores and the technical family score

**Files:**
- Create: `quantdesk/analysis/zscore.py`, `quantdesk/analysis/technical.py`
- Test: `tests/test_technical.py`

**Interfaces:**
- Produces:
  - `causal_z(value: float, ref: ZRef | None, min_n: int, winsor: float) -> float | None`
  - `z_refs_for(history: pd.DataFrame, window: int) -> dict[tuple[str, str], ZRef]`
    - `history` has columns `day, check, feature, value` for **earlier** sessions only.
    - It keeps each (feature, check)'s last `window` days.
  - `technical_raw(row: pd.Series, signal: Signal, nearest_dist: float) -> dict[str, float]`
    - Keys: `loc_vwap = (close − vwap)/b`, `loc_level = nearest_dist/b`, `adv_share`, `above_share − 0.5`, `top5_ret`.
    - All are long-aligned; multiply by −1 for a short.
  - `technical_score(raw: dict, z_refs, check: str, h: dict) -> float | None`: design §9. It is None when any z is undefined.

- [ ] **Step 1: Write the failing tests**

```python
def test_causal_z_uses_only_the_reference_and_winsorises():
    assert causal_z(3.0, ZRef(1.0, 1.0, 100), min_n=60, winsor=3.0) == 2.0
    assert causal_z(10.0, ZRef(0.0, 1.0, 100), min_n=60, winsor=3.0) == 3.0
    assert causal_z(1.0, ZRef(0.0, 1.0, 59), min_n=60, winsor=3.0) is None


def test_z_refs_keep_the_last_window_sessions():
    hist = pd.DataFrame({"day": pd.date_range("2024-01-01", periods=300).date, "check": "10:00",
                         "feature": "adv_share", "value": np.arange(300.0)})
    ref = z_refs_for(hist, window=250)[("adv_share", "10:00")]
    assert ref.n == 250 and ref.mean == pytest.approx(np.arange(50.0, 300.0).mean())
```

- [ ] **Step 2: Run them to verify they fail.**
- [ ] **Step 3: Implement.** Use the sample sd (ddof = 1). An sd of 0 gives None.
- [ ] **Step 4: Run them to verify they pass.**
- [ ] **Step 5: Commit** with message `feat: causal trailing z-scores and the technical family score (R10)`.

---

### Task 6: Options-implied score (prior-day bhavcopy)

**Files:**
- Create: `quantdesk/analysis/options_implied.py`
- Test: `tests/test_options_implied.py`

**Interfaces:**
- Produces:
  - `pcr_oi(eod: pd.DataFrame, expiry: date, center: float, step: int, n_steps: int) -> float | None`
  - `rr25(eod: pd.DataFrame, expiry: date, F: float, T_bt: float, rr_delta: float) -> float | None`. It uses traded rows only, computes IV with `implied_vol` at T = T_bt, and interpolates IV linearly in delta.
  - `options_raw(eod_prev: pd.DataFrame, ctx_like: dict, clock, h) -> dict[str, float] | None`, with keys `pcr` and `rr25`

- [ ] **Step 1: Write the failing tests**

```python
def test_pcr_counts_strikes_within_ten_steps():
    eod = pd.DataFrame({"expiry": date(2024, 3, 7), "strike": [22000.0, 22050.0, 23000.0] * 2,
                        "option_type": ["CE"] * 3 + ["PE"] * 3, "oi": [100, 100, 999, 300, 100, 999],
                        "traded": True})
    assert pcr_oi(eod, date(2024, 3, 7), center=22025.0, step=50, n_steps=10) == pytest.approx(400 / 200)


def test_rr25_is_zero_without_skew():
    eod = synthetic_chain(F=100.0, sigma=0.2, T=0.02, skew=0.0)     # helper: Black-76 closes on a strike grid
    assert rr25(eod, eod.expiry.iloc[0], F=100.0, T_bt=0.02, rr_delta=0.25) == pytest.approx(0.0, abs=1e-6)
```

- [ ] **Step 2: Run them to verify they fail.**
- [ ] **Step 3: Implement.** The score itself is `mean(causal_z(pcr), causal_z(rr25))`, computed in Task 15's pipeline with `ctx.z_refs`.
- [ ] **Step 4: Run them to verify they pass.**
- [ ] **Step 5: Commit** with message `feat: options-implied raw features from the previous day's bhavcopy (R26)`.

---

### Task 7: Macro engine (event gate, VIX block, stress, macro score)

**Files:**
- Create: `quantdesk/analysis/macro.py`
- Test: `tests/test_macro_engine.py`

**Interfaces:**
- Produces:
  - `event_block(events: tuple, at: datetime, h: dict) -> str | None`. Returns:
    - `"E3"` on a day with a scheduled E3 event
    - `"rbi_wait"` before time + 45 minutes
    - `"budget_wait"` before 13:00
    - None otherwise
  - `event_delta(events, h) -> float`: +0.04 on a Budget day
  - `hard_exit(day: date, is_expiry_day: bool, events, h) -> time`: 15:00 on expiry days and rebalance days, else 15:10
  - `timed_event_exits(events, day) -> list[datetime]`: the time of each scheduled timed event minus 5 minutes
  - `vix_block(vix_now: float, vix_prev_close: float, band: float) -> bool`
  - `stress_score(macro: pd.DataFrame, day: date) -> int`: design §9 points. `macro` is already cut as of 09:05 of day.
  - `stress_delta(score: int, full: bool, h) -> float`
  - `macro_raw(holiday_before: bool, r_on: float, fii_ratios: pd.Series, window: int) -> float`: long-aligned, in [−2, 2]

- [ ] **Step 1: Write the failing tests**

```python
RBI = Event(date(2024, 4, 5), time(10, 0), "rbi_mpc", "E2", "RBI", "https://x")
UNSCHEDULED = Event(date(2022, 5, 4), time(14, 0), "rbi_mpc", "E2", "RBI", "https://x", scheduled=False)


def test_rbi_blocks_entries_for_45_minutes():
    h = load_hypotheses()
    assert event_block((RBI,), datetime(2024, 4, 5, 10, 30, tzinfo=IST), h) == "rbi_wait"
    assert event_block((RBI,), datetime(2024, 4, 5, 10, 45, tzinfo=IST), h) is None


def test_unscheduled_events_never_block_from_the_calendar():
    assert event_block((UNSCHEDULED,), datetime(2022, 5, 4, 14, 15, tzinfo=IST), load_hypotheses()) is None


def test_stress_points():
    macro = stress_fixture(brent=[90, 90, 90, 90, 90, 100.0], usdinr=[83.0] * 5 + [84.3])   # helper
    assert stress_score(macro, date(2024, 3, 11)) == 1 + 2 + 2      # brent>=95, brent 5d +11%, inr 5d +1.6%


def test_macro_raw_fades_a_post_holiday_gap_and_follows_an_fii_flip():
    flips = pd.Series([0.45, 0.47, 0.52])        # crossed 0.5 within the window -> +1
    assert macro_raw(holiday_before=True, r_on=0.004, fii_ratios=flips, window=5) == -1 + 1
```

- [ ] **Step 2: Run them to verify they fail.**
- [ ] **Step 3: Implement** following design §9.
- [ ] **Step 4: Run them to verify they pass.**
- [ ] **Step 5: Commit** with message `feat: macro engine - event gate, VIX block, stress score, macro score (R25, R27, R39)`.

---

### Task 8: Shock hurdle (VIX jump, gap, variance CUSUM)

**Files:**
- Create: `quantdesk/analysis/hurdles.py`
- Modify: `quantdesk/cli.py` (`fit shock` writes `config/frozen/shock_v1.yaml`)
- Test: `tests/test_hurdles.py`

**Interfaces:**
- Produces:
  - `cusum_alarms(returns: pd.Series, sigma_window: int, h: float) -> pd.Series[bool]`: design §9, reset after each alarm
  - `calibrate_cusum_h(returns: pd.Series, sigma_window: int, block: int, resamples: int, target_rate: float, seed: int) -> float`: bisection on h
  - `shock_days(daily: pd.DataFrame, vix_close: pd.Series, sigma_gap: pd.Series, alarms: pd.Series, h: dict) -> pd.Series[bool]`
  - `shock_delta(shock: pd.Series, day: date, sessions: int, delta: float) -> float`: +0.04 if a shock fell on this session or the 4 before

- [ ] **Step 1: Write the failing tests**

```python
def test_cusum_alarms_on_a_variance_jump_and_not_before():
    rng = np.random.default_rng(0)
    r = pd.Series(np.r_[rng.normal(0, 0.01, 300), rng.normal(0, 0.03, 40)])
    alarms = cusum_alarms(r, sigma_window=250, h=5.0)
    assert not alarms.iloc[250:300].any() and alarms.iloc[300:340].any()


def test_calibrated_h_gives_about_one_alarm_per_250_sessions():
    rng = np.random.default_rng(1)
    r = pd.Series(rng.standard_t(4, 1500) * 0.01)
    h = calibrate_cusum_h(r, sigma_window=250, block=20, resamples=200, target_rate=1 / 250, seed=1)
    rate = cusum_alarms(r, 250, h).iloc[250:].mean()
    assert 0.5 / 250 <= rate <= 2.0 / 250


def test_shock_lasts_five_sessions():
    days = pd.date_range("2024-01-01", periods=8).date
    shock = pd.Series([False, True] + [False] * 6, index=days)
    assert shock_delta(shock, days[5], sessions=5, delta=0.04) == 0.04
    assert shock_delta(shock, days[6], sessions=5, delta=0.04) == 0.0
```

- [ ] **Step 2: Run them to verify they fail.**
- [ ] **Step 3: Implement.** Use a moving-block bootstrap on 2019–2022 NIFTY daily log returns, then save h with its seed and data hash.
- [ ] **Step 4: Run them to verify they pass.**
- [ ] **Step 5: Owner step.** Run `python -m quantdesk fit shock` and commit `config/frozen/shock_v1.yaml`.
- [ ] **Step 6: Commit** with message `feat: shock hurdle with a bootstrap-calibrated variance CUSUM`.

---

### Task 9: Minute frame and the truncation (look-ahead) test

**Files:**
- Create: `quantdesk/analysis/frame.py`
- Test: `tests/test_truncation.py`

**Interfaces:**
- Consumes: `vwap_proxy` (Task 2), `band_edges` and `slot` (Task 3).
- Produces:
  - `build_minute_frame(index_bars, members, vix_bars, ctx: DayContext, h) -> pd.DataFrame`, with columns:
    - `ts, open, high, low, close, vwap, vwap_sd, upper, lower, vix`
    - `adv_share, above_share, top5_ret`
    - `session_high, session_low`
    - `atm_premium` (modelled, nearest weekly; used by the spike guard)
    - `available_at`
  - `FEATURES: dict[str, Callable[[pd.DataFrame], pd.Series]]`: every column above that the gates read

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.parametrize("cut_minute", [5, 47, 120, 300])
def test_no_feature_changes_when_the_future_is_removed(cut_minute):
    index_bars, members, vix_bars, ctx = synthetic_day(seed=cut_minute)   # helper: 375 random-walk minutes
    full = build_minute_frame(index_bars, members, vix_bars, ctx, load_hypotheses())
    cut_ts = index_bars.ts.iloc[cut_minute]
    part = build_minute_frame(index_bars[index_bars.ts <= cut_ts], members[members.ts <= cut_ts],
                              vix_bars[vix_bars.ts <= cut_ts], ctx, load_hypotheses())
    for name in FEATURES:
        pd.testing.assert_series_equal(full.loc[full.ts <= cut_ts, name].reset_index(drop=True),
                                       part[name].reset_index(drop=True), check_names=False)
```

- [ ] **Step 2: Run it to verify it fails.**
- [ ] **Step 3: Implement.** Use only expanding or cumulative operations. `session_high` and `session_low` are cumulative max and min.
- [ ] **Step 4: Run it to verify it passes.** Any feature added later in SP2 must be registered in `FEATURES`.
- [ ] **Step 5: Commit** with message `feat: per-minute frame and a truncation test over every feature (R4)`.

---

### Task 10: `DayLoader` (day context and frame from derived tables)

**Files:**
- Create: `quantdesk/strategy/daycard.py`
- Test: `tests/test_daycard.py`

**Interfaces:**
- Consumes:
  - `AsOf` (plan 1, Task 7)
  - `har_series` (plan 1, Task 10)
  - `Clock` and `Surface` (plan 1)
  - Tasks 3 and 5–8 of this plan
- Produces:
  - `class DayLoader`:
    - `__init__(self, derived: DerivedStore, clock, surface, h, events: list[Event])`
    - `day_context(self, index: str, day: date) -> DayContext`: everything known by 09:16 of day, read through `AsOf(derived, 09:16 of day)`
    - `minute_frame(self, index: str, day: date) -> pd.DataFrame`
  - `feature_history(self, index: str, day: date) -> pd.DataFrame`: the `day, check, feature, value` rows for earlier sessions, from a cache under `data/derived/feature_history/` that is extended day by day

- [ ] **Step 1: Write the failing tests.**
  - Build a tiny `DerivedStore` in `tmp_path` holding:
    - 20 sessions of `sessions`, `minutes` (NIFTY, VIX, 3 stocks), `daily`, `expiries` and `members_minute`
    - one `options_eod` day
    - one `macro` series
  - Assert that `day_context("NIFTY", day_20)` has:
    - `prev_close` equal to day 19's daily close
    - `band_sigma` defined (14 earlier sessions)
    - `expiry_1` from day 19's file
    - `har_pct is None`, because fewer than 60 forecasts exist
  - Assert that a `daily` row for day 20 itself with `available_at` 16:00 is **not** used for `open`.
    - `open` comes from the first bar's open, or from `daily` only once `available_at` has passed.
    - The test changes the day-20 daily open to 999 and checks that the context's open is unchanged.
- [ ] **Step 2: Run them to verify they fail.**
- [ ] **Step 3: Implement.** Cache the HAR series per index once per loader. The previous Monday–Friday week comes from `daily` rows of the previous calendar week.
- [ ] **Step 4: Run them to verify they pass.**
- [ ] **Step 5: Commit** with message `feat: DayLoader builds the 09:16 day context and minute frame through AsOf`.

---

### Task 11: Timeline and gates

**Files:**
- Create: `quantdesk/strategy/timeline.py`, `quantdesk/strategy/gates.py`
- Test: `tests/test_gates.py`

**Interfaces:**
- Produces:
  - `check_times(day: date, is_expiry_day: bool, h) -> list[datetime]`: 09:45 to 14:00 every 15 minutes, ending at 13:30 on the index's expiry day
  - `timeline_block(ctx: DayContext, at: datetime, h) -> str | None`. Returns:
    - `"irregular_session"`
    - `"not_a_check_time"`
    - `"after_last_entry"`
    - or the `event_block` reason
  - Seven gate functions, each with signature `(signal, ctx, frame, helpers, h) -> bool`:
    - `gate_event_shock`
    - `gate_stop_fit`: only the structural cap b ≤ 0.5·S·σ_bt; rupees are checked in Task 12
    - `gate_room_in_time`
    - `gate_room_to_run`
    - `gate_volatility`
    - `gate_confirmation`
    - `gate_spike_guard`
  - `GATES: tuple[tuple[str, Callable], ...]` in spec order
  - `first_failed_gate(signal, ctx, frame, helpers, h) -> str | None`
  - `Helpers`, a dataclass holding `clock`, `surface` and `quotes`, so gates can price the ATM option

- [ ] **Step 1: Write the failing tests.** One test per gate, each with a synthetic signal and frame that passes every gate except that one. Assert `first_failed_gate(...) == "<name>"`. Also:

```python
def test_check_times_end_earlier_on_expiry_day():
    h = load_hypotheses()
    normal = check_times(date(2024, 3, 5), False, h)
    expiry = check_times(date(2024, 3, 7), True, h)
    assert normal[0].time() == time(9, 45) and normal[-1].time() == time(14, 0) and len(normal) == 18
    assert expiry[-1].time() == time(13, 30)


def test_an_irregular_session_is_blocked_before_any_gate():
    assert timeline_block(make_ctx(session_kind="irregular"), datetime(2024, 3, 2, 10, 0, tzinfo=IST),
                          load_hypotheses()) == "irregular_session"
```

- [ ] **Step 2: Run them to verify they fail.**
- [ ] **Step 3: Implement** following design §10 step 4.
- [ ] **Step 4: Run them to verify they pass.**
- [ ] **Step 5: Commit** with message `feat: timeline and the seven pre-trade gates in spec order`.

---

### Task 12: Strike picker with the EV gate

**Files:**
- Create: `quantdesk/strategy/strikes.py`
- Test: `tests/test_strikes.py`

**Interfaces:**
- Consumes: `round_trip` (`quantdesk/costs.py`), `ModelQuotes`, `Surface.shifted`, `black76_vec`.
- Produces:
  - `@dataclass(frozen=True) class Candidate`: `index, expiry, strike, kind, lot, ask, delta, gain, loss`
  - `candidates(signal, ctx, helpers, h, today: date) -> list[Candidate]`, priced per design §10 step 6, with costs from `round_trip(..., day=today)`
  - `pick(cands: list[Candidate], p: float | None, delta: float, h, evaluate_ev: bool = True) -> StrikeChoice | None`
    - With `evaluate_ev=False`, only the non-probability filters run: affordability, L ≤ 400, G/L ≥ 1.5 and delta. P1 uses this mode.

- [ ] **Step 1: Write the failing tests**

```python
def test_the_ev_gate_uses_the_breakeven_of_each_strike():
    c = Candidate("NIFTY", date(2024, 3, 7), 22000.0, "CE", 50, ask=60.0, delta=0.4, gain=800.0, loss=380.0)
    # p_be = 380 / 1180 = 0.322; need p >= 0.322 + 0.04 + 0.0 = 0.362
    assert pick([c], p=0.35, delta=0.0, h=load_hypotheses()) is None
    choice = pick([c], p=0.44, delta=0.0, h=load_hypotheses())
    assert choice.ev == pytest.approx(0.44 * 800 - 0.56 * 380)      # 139.2 >= max(0.10 x 400, 75)


def test_affordability_and_delta_bounds_are_never_relaxed():
    pricey = Candidate("NIFTY", date(2024, 3, 7), 22000.0, "CE", 75, ask=130.0, delta=0.5, gain=900.0, loss=390.0)
    deep = Candidate("NIFTY", date(2024, 3, 7), 21500.0, "CE", 50, ask=60.0, delta=0.70, gain=900.0, loss=390.0)
    assert pick([pricey, deep], p=0.9, delta=0.0, h=load_hypotheses()) is None   # 130*75+60 > 9500; delta > 0.55


def test_ties_go_to_nifty_then_nearer_expiry_then_delta_near_040():
    a = Candidate("SENSEX", date(2024, 3, 8), 73000.0, "CE", 10, 200.0, 0.40, 800.0, 380.0)
    b = Candidate("NIFTY", date(2024, 3, 14), 22000.0, "CE", 50, 60.0, 0.40, 800.0, 380.0)
    c = Candidate("NIFTY", date(2024, 3, 7), 22050.0, "CE", 50, 60.0, 0.30, 800.0, 380.0)
    d = Candidate("NIFTY", date(2024, 3, 7), 22000.0, "CE", 50, 60.0, 0.41, 800.0, 380.0)
    assert pick([a, b, c, d], p=0.6, delta=0.0, h=load_hypotheses()).strike == 22000.0
```

- [ ] **Step 2: Run them to verify they fail.**
- [ ] **Step 3: Implement.**
  - `candidates` follows design §10 step 6.
  - `pick` applies the filters, then EV and Kelly when `evaluate_ev`, then sorts by (−ev, index ≠ "NIFTY", expiry, |Δ − 0.40|).
- [ ] **Step 4: Run them to verify they pass.**
- [ ] **Step 5: Commit** with message `feat: strike picker with planning rupees and the per-strike EV and Kelly gate`.

---

### Task 13: Meta-model, labels and B0 consensus

**Files:**
- Create: `quantdesk/strategy/meta.py`
- Test: `tests/test_meta.py`

**Interfaces:**
- Produces:
  - `label(frame: pd.DataFrame, signal: Signal, hard_exit_at: datetime) -> int`: 1 if the close reaches the target before the stop and before the hard exit; minute closes only, from `signal.at` on
  - `columns(scores: dict, side: str, har_pct: float, dte: int) -> np.ndarray` (6 values, design §13)
  - `@dataclass class MetaModel`: `beta: np.ndarray (7,)`, `platt: tuple[float, float] | None`, `base_rate: float`, `macro_clip: float`
    - `predict(x) -> float`
    - `to_json() -> dict` and `from_json(d) -> MetaModel`
  - `fit_meta(X: np.ndarray, y: np.ndarray, lam: float, split: float) -> MetaModel`, with the inner calibration check of design §13
  - `@dataclass class Consensus`: `a: float`, `b: float`, with `predict(mean_score) -> float`; `fit_consensus(s: np.ndarray, y: np.ndarray) -> Consensus`

- [ ] **Step 1: Write the failing tests**

```python
def test_label_target_before_stop():
    frame = closes_frame([100.0, 100.2, 99.6, 100.9])                  # helper; target 100.69, stop 99.7
    sig = Signal("NIFTY", frame.ts[0], "long", 100.0, 99.9, 0, 99.95, 99.7, 0.3, 100.69)
    assert label(frame, sig, hard_exit_at=frame.ts.iloc[-1]) == 0      # 99.6 hits the stop first


def test_ridge_recovers_the_direction_and_shrinks():
    rng = np.random.default_rng(3)
    X = rng.normal(size=(3000, 6)); true = np.array([0.8, 0, 0, 0, 0, 0])
    y = (rng.random(3000) < 1 / (1 + np.exp(-(X @ true - 0.5)))).astype(int)
    m = fit_meta(X, y, lam=10.0, split=0.8)
    assert 0.6 < m.beta[1] < 0.95 and abs(m.beta[2]) < 0.1     # beta[0] is the intercept


def test_well_calibrated_models_get_no_platt():
    rng = np.random.default_rng(4)
    X = rng.normal(size=(5000, 6)); y = (rng.random(5000) < 1 / (1 + np.exp(-X[:, 0]))).astype(int)
    assert fit_meta(X, y, lam=10.0, split=0.8).platt is None


def test_macro_column_cannot_move_p_more_than_8_points():
    m = MetaModel(beta=np.array([0, 0, 0, 5.0, 0, 0, 0]), platt=None, base_rate=0.5, macro_clip=0.08)
    assert abs(m.predict(np.array([0, 0, 2.0, 0, 0, 0])) - 0.5) <= 0.0801
```

- [ ] **Step 2: Run them to verify they fail.**
- [ ] **Step 3: Implement** with `scipy.optimize.minimize(method="L-BFGS-B", jac=True)`. The calibration-slope 95% CI comes from a one-variable logistic fit (Wald SE).
- [ ] **Step 4: Run them to verify they pass.**
- [ ] **Step 5: Commit** with message `feat: triple-barrier labels, ridge logistic meta-model and B0 consensus (R28)`.

---

### Task 14: Exit simulator (X0, X1 with both R2 models, X2)

**Files:**
- Create: `quantdesk/strategy/exits.py`
- Test: `tests/test_exits.py`

**Interfaces:**
- Produces:
  - `@dataclass class OpenTrade`: `signal: Signal`, `choice: StrikeChoice`, `fill_at: datetime`, `fill_premium: float`, `backstop_trigger: float`, `backstop_limit: float`
  - `@dataclass class ExitResult`:
    - `exit_at: datetime`, `exit_premium: float`, `reason: str`, `model: str` ("A" or "B")
    - `ratchets: int`
    - `pnl_a: float | None`, `pnl_b: float | None`
  - `simulate_exit(trade: OpenTrade, frame: pd.DataFrame, quotes, ctx: DayContext, policy: str, h, today: date) -> ExitResult`
    - P&L uses `round_trip(..., day=today)`.
    - X1 returns the result with the lower P&L of model A and model B (R2).

- [ ] **Step 1: Write the failing tests** (synthetic index paths, and a stub quote source whose premium = 50 + 0.5 × (S − 22000) for calls)

```python
def test_trail_starts_at_one_b_and_ratchets_with_a_two_minute_delay(): ...
    # path rises 1.0b at minute 5, 2.0b at 20, then falls; assert the first ratchet alert at minute 5,
    # stop effective from minute 7, exit reason "stop" with exit time = stop-cross minute + 2

def test_laggard_exits_at_30_minutes_when_flat(): ...
    # path within ±0.04% for 40 minutes -> exit at fill + 30 + 2 minutes, reason "laggard"

def test_a_delayed_exit_never_passes_the_hard_exit(): ...
    # stop crossed at 15:09 on a normal day -> exit at 15:10, reason "hard_exit"

def test_x1_books_the_worse_of_index_alert_and_premium_backstop(): ...
    # gap-down minute where the modelled bid jumps below the backstop limit -> backstop doesn't fill (model B
    # falls back to A); a slow fall where the backstop fills earlier and higher -> result = the lower P&L

def test_x0_takes_the_fixed_target(): ...
    # path touches 2.3b at minute 12 -> exit at the bid at minute 12, reason "target"
```

Write each body with concrete minute indices and exact expected exit minutes. The comments above give the numbers.

- [ ] **Step 2: Run them to verify they fail.**
- [ ] **Step 3: Implement** following design §11. Everything works on minute closes. The ratchet alert gap is 10 minutes and the manual delay 2 minutes.
- [ ] **Step 4: Run them to verify they pass.**
- [ ] **Step 5: Commit** with message `feat: exit simulator - X0, E-trail with phone-alert delay and backstop (R2), X2`.

---

### Task 15: `decide()` and the alert

**Files:**
- Create: `quantdesk/strategy/pipeline.py`
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Produces: `decide(ctx: DayContext, frame: pd.DataFrame, at: datetime, cfg: TrialConfig, model, helpers: Helpers, h, today: date) -> Decision`
  - `model` is a `MetaModel`, a `Consensus`, or None. None means "pass-rate mode": it stops after the picker with `evaluate_ev=False`.
  - Δ = min(0.08, the sum of `ctx.delta_parts` entries enabled by `cfg.hurdles`, plus `delta_parts["event"]`).
  - The alert is built as in design §10 step 7. `reasons_for` and `reasons_against` list each family score's sign and the nearest opposing level.

- [ ] **Step 1: Write the failing tests**

```python
def test_decide_reports_the_first_failing_step():
    d = decide(make_ctx(session_kind="irregular"), frame, at, config_for("B0", {}), None, helpers, h, TODAY)
    assert d.failed == "irregular_session" and d.signal is None


def test_decide_returns_an_alert_with_a_backstop(): ...
    # synthetic day built to pass every gate with a Consensus(a=0, b=0) -> p = 0.5;
    # assert alert.entry_limit == choice.ask + 2 * 0.05 and alert.backstop_trigger == choice.ask - 400 / lot


def test_decide_never_reads_beyond_at():
    full = decide(ctx, frame, at, cfg, model, helpers, h, TODAY)
    cut = decide(ctx, frame[frame.ts <= at - timedelta(minutes=1)], at, cfg, model, helpers, h, TODAY)
    assert full == cut
```

- [ ] **Step 2: Run them to verify they fail.**
- [ ] **Step 3: Implement** by chaining Tasks 3, 11, 12 and 13, in spec order.
- [ ] **Step 4: Run them to verify they pass.**
- [ ] **Step 5: Commit** with message `feat: decide() - the pure pipeline from day card to alert`.

---

### Task 16: Pilots P9 (VWAP proxy) and P4 (autocorrelation)

**Files:**
- Create: `quantdesk/validation/pilots/__init__.py`, `quantdesk/validation/pilots/p9_vwap.py`, `quantdesk/validation/pilots/p4_autocorr.py`, `quantdesk/validation/pilots/report.py`
- Modify: `quantdesk/cli.py` (`pilot P9|P4|P1|P2|P10`)
- Test: `tests/test_pilots_p9_p4.py`

**Interfaces:**
- Produces:
  - `vwap_agreement(index_frame: pd.DataFrame, fut_bars: pd.DataFrame, b_median: float) -> dict`, with keys `minutes, side_disagree_share, median_gap_over_b, passed` (design §16, spec §6.0 thresholds: 0.05 and 0.1)
  - `ar1_mac5(close: pd.Series, after: date) -> dict`, with keys `ar1, ar1_t, mac5, mac5_t, mac5_after, mac5_after_t, ctx_runs`. `ctx_runs` = mac5_after < 0 and its HAC t < −1.96.
  - `write_report(pilot_id: str, body: dict, path: Path) -> Path`, a markdown table plus the derived `data_hash`

- [ ] **Step 1: Write the failing tests**
  - `test_identical_vwaps_agree_fully`: futures = index + 20 points and futures VWAP = proxy + 20. Expect share 0 and gap 0.
  - `test_opposite_sides_count_as_disagreement`.
  - `test_ar1_of_an_ar_process`: simulate AR(1) with φ = −0.1 over 3,000 points and assert `ar1 ≈ −0.1 ± 0.04`.
- [ ] **Step 2: Run them to verify they fail.**
- [ ] **Step 3: Implement.**
  - HAC (Newey–West) with lag 5, written by hand.
  - P9 reads the futures targets from `minutes` (those whose target ends in `FUT` and starts with `NIFTY`). It skips the last 2 sessions before each expiry, when volume moves to the next contract.
- [ ] **Step 4: Run them to verify they pass.**
- [ ] **Step 5: Owner step.** Run `python -m quantdesk pilot P9` and `pilot P4`, then read `research/pilots/P9.md`. If P9 fails, the VWAP rules switch to the open-anchored average price: add the ruling to `decisions.md` and `hypotheses.yaml` before going further.
- [ ] **Step 6: Commit** with message `feat: pilots P9 (VWAP proxy vs futures) and P4 (AR1/MAC5)`.

---

### Task 17: Pilots P1, P2, P10 and the D2 checkpoint report

**Files:**
- Create: `quantdesk/validation/pilots/p1_pass_rates.py`, `quantdesk/validation/pilots/p2_excursions.py`, `quantdesk/validation/pilots/p10_power.py`
- Test: `tests/test_pilots_p1_p2_p10.py`

**Interfaces:**
- Produces:
  - `pass_rates(decisions: list[Decision], vix_tercile: dict[date, int], lot_era: dict[date, int]) -> pd.DataFrame`, with columns:
    - `year, vix_tercile, lot`
    - `signals, stop_fit_pass, picker_pass, eligible`
    - `stop_fit_rate, picker_rate`
  - `excursions(frame: pd.DataFrame, signal: Signal, hard_exit_at: datetime) -> dict`, with keys `mfe_b, mae_b, minutes_to_mfe, retrace_after_mfe_b`. Index only.
  - `power(setups_per_year: float, years: int, uplift: float, base_p: float, payoff: tuple[float, float], gates: dict, n_sims: int, seed: int) -> dict`
    - Keys: `p_all_gates, p_t, p_dsr, mde_80`.
    - It simulates trade outcomes as Bernoulli(base_p + uplift) with gains and losses in R from `payoff`.
    - It applies the t, years, DSR and PBO-free gates with the same functions plan 3 builds. Import them from `quantdesk/validation/stats.py` once it exists. Until then, write the t and DSR formulas here and move them in plan 3, Task 5.
  - `d2_report(p1: pd.DataFrame, p2: dict, p10: dict, h) -> str`: markdown saying whether D2 triggers, and the owner's two options

- [ ] **Step 1: Write the failing tests**
  - `test_pass_rates_by_tercile`: 6 decisions across 3 terciles, with known failures. Exact rates.
  - `test_excursions_of_a_known_path`: up 2b at minute 10, then down 1b. mfe_b = 2, minutes_to_mfe = 10, retrace = 3.
  - `test_power_is_low_without_uplift`: uplift 0, n_sims = 500. `p_all_gates < 0.05`.
  - `test_power_rises_with_uplift`: uplift 0.10, 300 setups a year for 5 years. `p_all_gates > 0.5`.
  - `test_d2_triggers_below_60_setups`: P1 with 40 eligible a year → the report contains "D2 checkpoint: triggered".
- [ ] **Step 2: Run them to verify they fail.**
- [ ] **Step 3: Implement.**
  - **P1** runs `decide(..., model=None)` over every regular session from 2019-02-11 to 2025-12-31 for both indices, using the `DayLoader`. P1 and P2 never compute option P&L.
  - **P10** takes `base_p` = the breakeven at the P1 median strike, and the payoff from P2's median excursions converted at that strike's delta.
- [ ] **Step 4: Run them to verify they pass.**
- [ ] **Step 5: Owner step.** Run `pilot P1`, then `pilot P2`, then `pilot P10`. Read `research/pilots/D2.md` and make the D2 decision (₹15k/₹600, or stay at ₹10k/₹400, or alert-off) and the X2 decision. Record both in `decisions.md` and `hypotheses.yaml`.
- [ ] **Step 6: Commit** with message `feat: pilots P1, P2, P10 and the D2 checkpoint report`.

---

## Plan 2 is done when

- The suite passes, including the truncation test over every feature.
- `research/pilots/` has P9, P4, P1, P2, P10 and D2. The owner's D2 and X2 decisions are recorded.
- If P9 failed, the VWAP fallback ruling is recorded before plan 3 starts.
- `main` is fast-forwarded.
