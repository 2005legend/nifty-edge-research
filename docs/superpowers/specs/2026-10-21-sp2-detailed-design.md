# SP2 detailed design: strategy core, backtester and verdict

**Date:** 21 Oct 2026.

**Who it's for:** the owner, who will implement SP2. Read it together with:
- the design spec, `docs/superpowers/specs/2026-10-06-nifty-sensex-options-signal-system-design.md`: §5A engines, §6.0 data conventions, §6.1–§6.3 pipeline, backtester and validation, §6.4 rulings R1–R38
- `research/hypotheses.yaml`, which holds every number
- the three coding plans in `docs/superpowers/plans/2026-10-21-sp2-plan-{1,2,3}-*.md`

This document says **what** each part computes and **why**. The plans say **in what order** to build it and **which tests** prove it.

Rules that apply everywhere:
- **Numbers live only in `hypotheses.yaml`.** Code reads them through `quantdesk.validation.hypotheses.param(h, key)`. If you need a number that isn't there, add it with a source and provenance, before any P&L run.
- **No P&L before the registry.** Until plan 3's registry issues a ticket, never look at the profit of a strategy idea on real data. Pass rates, excursions and pricing errors are fine; profit, win rate and R are not.

---

## 1. What SP2 produces

1. Pure functions that turn market data up to time T into a decision: no signal, a signal blocked by a named gate, or an alert with strike, entry limit, stop and plan.
2. A backtester that replays 2019–2026 through those same functions and simulates the owner's fills and exits.
3. A validation layer that runs the 13-slot registry and ends in a verdict: **alert-on** for one frozen configuration, or **alert-off**.

## 2. What already exists (as of `main`, 21 Oct 2026)

| Piece | Where |
|---|---|
| Pre-registration, prior-looks inventory and empty experiment log | `research/hypotheses.yaml`, `research/prior_looks.md`, `research/experiments.csv` |
| Validator for the pre-registration | `quantdesk/validation/hypotheses.py`: `load_hypotheses`, `param`, `validate` |
| Point-in-time Nifty 50 membership | `config/nifty50_membership.yaml`, `quantdesk/market/membership.py`: `load_membership().members_on(day)`, `.listing(sym)`, `.backfill_symbols()` |
| Event history 2019–2026 | `config/events_history.yaml`. `Event` gained `scheduled`, `announced_on` and `time_assumed`. |
| Derived store with content hashes | `quantdesk/derived/store.py`: `DerivedStore(root)` with `write_frame`, `write_query`, `write_parts`, `read(name, where, columns)`, `manifest`, `data_hash` |
| `minutes` table | `quantdesk/derived/minutes.py` `build_minutes(store, derived)`. Deduplicated, 09:15–15:29 only, `available_at = ts + 1 min`, partitioned by year. |
| `sessions` table | `build_sessions(derived, session_settings)`: `regular` or `irregular` per day |
| Cost model | `quantdesk/costs.py` `round_trip(buy, sell, qty, *, exchange, day) -> Costs(.total)` |
| Scalar Black-76 | `quantdesk/black76.py` `black76`, `greeks`, `implied_vol` |
| Backfills on disk | minutes 2019+ for indices, VIX and members (former members come in with tonight's run). Also: bhavcopy NSE 2019+ and BSE 2024+, daily candles 2015+, macro 2015+, participant OI 2019+ (running). |

## 3. Architecture

```
data/raw  ──derive──►  data/derived  ──►  vol/ + pricing/  ──►  analysis/ (engines)  ──►  strategy/ (pipeline)
 (append-only)        (rebuilt, hashed)    (HAR, clock,          (per-minute features,     (decide(), exits)
                                            quotes)               causal)                       │
                                                                                                 ▼
                                    validation/ (registry, CV, stats, verdict)  ◄──  backtest/ (fills, day loop, reports)
```

| Package | Responsibility | Depends on |
|---|---|---|
| `quantdesk/derived/` | Build every table under `data/derived`; as-of reads | `storage`, `market/membership`, `eod/bhavcopy` |
| `quantdesk/vol/` | Garman–Klass RV, HAR fits and forecasts, HAR percentile | `derived` |
| `quantdesk/pricing/` | Business-time clock, VIX conversion, surface (R, skew, beta), vectorised Black-76, quotes, pricing check | `derived`, `black76` |
| `quantdesk/analysis/` | Engines: VWAP proxy, bands, levels, breadth, z-scores, family scores, macro engine, hurdles | `vol`, `pricing` |
| `quantdesk/strategy/` | Types, day card, timeline, trigger, gates, meta-model, strike picker + EV, exits, pipeline | `analysis`, `pricing` |
| `quantdesk/backtest/` | Fills, day loop, reports, placebo | `strategy`, `costs` |
| `quantdesk/validation/` | Pre-registration, registry and tickets, CPCV, statistics, verdict, pilots | everything above |

**Dependency rule:** arrows point one way. `strategy` never imports `backtest`, and `analysis` never imports `strategy`. SP3's live engine will call `strategy` exactly as `backtest` does.

## 4. Knowledge time (R4, R5)

Every derived row has `available_at`, the first moment the real system could have known it. Nothing computed for time T may use a row with `available_at > T`.

| Data | Stamp | `available_at` |
|---|---|---|
| 1-minute bar (index, VIX, stock) | minute start `ts` | `ts + 1 min` |
| `members_minute` row | `ts` | `ts + 1 min` |
| Daily official OHLC (`daily`) | day d | d 16:00 IST |
| Bhavcopy rows (`options_eod`), participant OI | day d | next session 09:00 IST |
| FRED series (`dgs10`, `dexinus`, `brent_fred`) | date d | d + 2 calendar days, 09:00 IST |
| yfinance global (`spx`, `es`, `nq`, `dxy`, `brent`, `usdinr`, `us10y`) | d | d + 1, 09:00 IST |
| yfinance Asia (`n225`, `hsi`, `kospi`) | d | d + 1, 09:00 IST |
| yfinance Indian (`nifty_yf`, `sensex_yf`, `banknifty_yf`, `indiavix_yf`) | d | d 16:00 IST |
| OECD/IMF monthly | period start d | d + 60 days |
| NSE index file (`nifty_fundamentals`, `india_gsec10y_price`) | d | d 20:00 IST |
| Scheduled event | — | known from the start of its year |
| Unscheduled event | — | `announced_on` at its `time` |
| HAR forecast for day d | — | d 09:16 (uses today's gap) |

**Check-time rule.** A check at T (10:00, say) uses bars stamped up to T − 1 minute (the 09:59 bar, closed at 10:00).

**Fill rule.** A fill with delay k uses the close of the bar stamped T + k − 1:
- delay 0 fills at the signal bar's close
- delay 1 fills at the close of the T bar
- and so on.

**Future calendar.** The trading calendar of future days is known in advance (holiday lists are published yearly), so the clock may count sessions until expiry from the `sessions` table.

**Frozen fits** (clock, surface, skew, beta) are fitted on 2019–2022 only. Using them on 2019–2022 itself is in-sample. That is allowed for pricing calibration, which is not P&L. The meta-model is different: it is always trained inside CV folds.

The `AsOf` reader (plan 1, task 7) enforces these rules for history. A truncation test (plan 2, task 9) enforces them for intraday features: features computed with data cut at T must equal features computed on the full day, for every row at or before T − 1 minute.

## 5. Derived tables

All are under `data/derived/<name>/`. They are rebuilt with `python -m quantdesk derive` and hashed in `manifest.json`.

| Table | Key | Columns | Build rule |
|---|---|---|---|
| `minutes` (done) | target, ts | open, high, low, close, volume, available_at, day | Dedupe with the latest file winning; 09:15–15:29 only |
| `sessions` (done) | day | bars, first_bar, last_bar, kind | `regular` if a weekday, first bar ≤ 09:20, last bar ≥ 15:29 (≥ 15:14 from 2026-08-03), and bars ≥ 95% of 375 (361 in the auction era) |
| `daily` | target, day | open, high, low, close, available_at | From `history_one_day`; the latest file wins |
| `macro` | series_id, date | value, available_at | From `macro_daily`; the latest `stored_on` wins; lag rules from §4 |
| `members_minute` | ts | day, available_at, members_total, members_present, tv, adv, dec, above_vwap, top5_ret | §5.1 |
| `options_eod` | day, symbol, instrument, expiry, strike, option_type | open, high, low, close, settle, oi, volume, lot, available_at | §5.2 |
| `expiries` | symbol, day | expiry_1, expiry_2, is_expiry_day, lot_1, lot_2 | From the previous session's `options_eod` (known on the morning of d) |
| `fii_ratio` | day | ratio, available_at | `fii_index_futures_long_ratio(parse_participant_oi(file))`, available the next session at 09:00 |

### 5.1 `members_minute`

This table is the VWAP proxy's weights and the breadth inputs, computed once.

- **Members.** On each day d: `members = {membership.listing(s) for s in membership.members_on(d)}`. `members_total` is the size of that set (50). `members_present` counts members with a bar at ts.
- **Traded value:** `tv(ts) = Σ over members with a bar at ts of ((high + low + close) / 3) × volume`.
- **Stock state, carried forward within the day.** Each stock keeps its last close, its day open (the open of its first bar of the day) and its own cumulative VWAP: Σ tp·v / Σ v since the open.
- **Breadth counts over stocks seen so far that day:**
  - `adv` = number with last close > day open
  - `dec` = number with last close < day open
  - `above_vwap` = number with last close > own VWAP
- **Top-5 stocks.** These are the 5 members with the largest traded value in the **previous session** (R5). Then `top5_ret = Σ w_i × (last_close_i / day_open_i − 1) / Σ w_i`, with w_i = previous-session traded value, over top-5 stocks seen so far.
- **Coverage.** HDFC Ltd has no data, so `members_present` stays at 49 or fewer until 12 Jul 2023. Report coverage per day; never fill missing stocks.

### 5.2 `options_eod`

**Source files:**
- NSE bhavcopy for `NIFTY` (2019-01-01 onward)
- BSE bhavcopy for `SENSEX` (2024-01-01 onward, R11)

Only instruments IDO (options) and IDF (futures) are used.

**Columns:**
- `expiry` is the actual expiry: `FininstrmActlXpryDt` in UDiFF, `EXPIRY_DT` in the legacy layout.
- `lot`:
  - UDiFF: `NewBrdLotQty` per contract.
  - Legacy: round(VAL_INLAKH × 1e5 / (CONTRACTS × SETTLE_PR)) for the futures whose expiry is the first on or after the option's expiry, snapped to the nearest of {25, 50, 75}.
- `traded = volume > 0`. Untraded rows keep a close but no real price, so fits use traded rows only.
- `available_at` = the next session at 09:00 IST.

Known gap: NSE's legacy archive has no file for 2021-03-30, a real trading day. Expiry and lot lookups fall back to the previous file.

## 6. Volatility (`quantdesk/vol/`)

**Garman–Klass session variance**, for day d of index X (from `daily`):

```
RV_d = 0.5 · ln(H_d / L_d)^2 − (2·ln 2 − 1) · ln(C_d / O_d)^2       (fraction², open-to-close)
r_on,d = ln(O_d / C_{d−1})                                          (overnight return)
```

**HAR, per index.** The target is y_t = ln RV_t. The regressors are all known at 09:16 on day t:

```
x1 = ln RV_{t−1}
x2 = ln( mean(RV_{t−5..t−1}) )
x3 = ln( mean(RV_{t−22..t−1}) )
x4 = ln( (VIX_close_{t−1} / 100)^2 / 252 )
x5 = ln( r_on,t^2 + 1e−8 )
```

**Fitting:**
- OLS with an intercept, on the 750 sessions that end at the last session before the refit day.
- Refit on the first session of each month.
- Save β0..β5, the residual variance s² and n per refit to the derived table `har_fits` (an audit trail; HAR is not frozen).

**Forecasts:**
- **Day variance:** RV̂_t = exp(ŷ_t + s²/2), and σ̂_day,t = √RV̂_t, as a fraction of the index.
- **Pre-gap forecast** (for the shock rule): the same ŷ with x5 replaced by its mean in the fit window, giving σ̂_gap,t = √(θ_n × RV̂ⁿᵒ⁻ᵍᵃᵖ_t). θ_n comes from §7.
- **HAR percentile:** the rank of RV̂_t among RV̂ over the previous 252 sessions, as a fraction in [0, 1]. It needs at least 60 earlier values; otherwise it is undefined, and the signal is not counted (R12).
- **Remaining-session volatility:** σ_rem(T) = σ̂_day,t × √W_rem(T), where W_rem(T) is the share of today's clock weight still ahead at T (§7). In index points: × O_t.

## 7. Business-time clock (`quantdesk/pricing/clock.py`)

The unit is one regular session = 1.0. A clock is a frozen file, `config/frozen/clock_v1.yaml`, holding:
- `minute_weights`: 375 values summing to 1, slot m = 09:15 + m minutes
- `theta_night`, `theta_weekend_day`, `theta_holiday`
- `fit_window`, `data_hash`, `fitted_at`

**Minute weights.** Use 2019–2022 regular NIFTY sessions:

```
r_{d,0} = ln(C_{d,0} / O_d)
r_{d,m} = ln(C_{d,m} / C_{d,m−1})        for m ≥ 1
```

Then w_m ∝ mean over d of min(r²_{d,m}, q_m), where q_m is the 99.9th percentile of r²_{d,m}. Normalise so the weights sum to 1.

From 2026-08-03 the index pauses at 15:15, but options trade until 15:30. Keep all 375 weights, because option time still passes.

**Night weight:**

```
θ_n = mean(r_on,d²) / mean(ln(C_d/O_d)²)
```

over 2019–2022 pairs of consecutive sessions with no weekend day or holiday between them.

**Weekend and holiday weights**, fitted from implied variance:
1. For each session d (2019–2022) and each NIFTY expiry e with 2–6 trading days left, take the ATM strike K (nearest to F). Use only rows where both call and put traded.
2. F = K + C − P (put–call parity, r = 0).
3. IV = the mean of call and put `implied_vol`, with calendar T = (15:30 on e − 15:30 on d) / 365 days.
4. Ṽ_d,e = IV² × T / (VIX_d / 100)². Dividing by VIX² removes level changes.
5. For consecutive sessions d → d′ with the same e: ΔṼ = Ṽ_d,e − Ṽ_d′,e, W = weekend days strictly between d and d′, H = weekday holidays strictly between.
6. Regress ΔṼ = β0 + β1·W + β2·H by OLS. One session plus one night is β0. Then:

```
θ_w = clip(β1/β0 · (1 + θ_n), 0, 1 + θ_n)
θ_h = clip(β2/β0 · (1 + θ_n), 0, 1 + θ_n)
```

Report standard errors in the CLOCK pilot report.

**Business time between two moments:**

```
BT(t0, t1) =   W_rem(t0)                                   # rest of t0's session (1.0 if before 09:15)
             + Σ over gaps g between d0 and d1:  θ_n + θ_w·W_g + θ_h·H_g
             + (# sessions strictly between d0 and d1)
             + W_done(t1)                                  # share of d1's session up to t1 (1.0 at 15:30)
```

When d0 = d1, BT = W_done(t1) − W_done(t0). Irregular sessions count as sessions, because time passes on them too.

**VIX to business-time volatility (R15):**

```
σ_bt(t)² = (VIX_t/100)² · (30/365) / BT(t, t + 30 calendar days at the same clock time; rolled back to the previous session's 15:30 if that day is not a session)
```

The units are per √(session unit). Black-76 only ever sees σ·√T, so passing T = BT and σ = σ_bt is consistent.

## 8. Option pricing and quotes (`quantdesk/pricing/`)

- **Forward:** F = S, the index level, with r = 0 for weeklies. Carry over 7 days or less is under 0.1%. Record this as a parameter.
- **ATM level:** σ_ATM(t, e) = R(dte) × σ_bt(t).
  - R(dte), for dte = 1..6, is the median over 2019–2022 of σ_ATM,bt / σ_bt(VIX at 15:29).
  - σ_ATM,bt is the bhavcopy ATM implied vol computed with T = BT(close, expiry).
  - Use R(0) = R(1) until recorded chains measure expiry days.
- **Skew:**
  - σ(K) = σ_ATM × max(0.5, 1 + b1·z + b2·z²), where z = ln(K/F) / (σ_ATM·√BT).
  - Fit b1 and b2 by least squares on traded strikes with |z| ≤ 3, dte 1–6, NIFTY 2019–2022, pooled.
  - Sensex uses the same values (R11).
- **Spot–vol beta** (planning only, R16):
  - Over 2019–2022 regular sessions, take non-overlapping 15-minute windows from 09:30.
  - Regress Δln VIX on the index log return, separately for r < 0 (γ_dn) and r ≥ 0 (γ_up).
  - After a move r: σ_bt′ = σ_bt × exp(γ·r).
- **Black-76:** a vectorised `black76_vec`, plus `delta_vec` and `theta_bt_vec` (derivative with respect to BT). They must match the scalar `quantdesk/black76.py` to 1e-10.
- **Quotes:**
  - mid = model premium.
  - Half-spread h = base × multiplier:
    - base: 0.10 for NIFTY with premium < 50, 0.20 for NIFTY with premium ≥ 50, 0.50 for SENSEX
    - multiplier: 2.0 before 09:30 and after 14:45, 1.5 for 09:30–10:00, else 1.0
  - ask = mid + h rounded **up** to ₹0.05; bid = max(mid − h, 0.05) rounded **down**.
  - A `QuoteSource` protocol has `quote(index, expiry, strike, kind, at) -> Quote(bid, ask, mid)`. `ModelQuotes` serves the backtest. SP3 adds `RecordedQuotes`.
- **Pricing check (R17).** Pair recorded `option_snapshots` with model marks at the same minute:

```
error = median over (check time T, candidate strike, horizon h ∈ {15, 30, 60 min, exit})
        of |Δmodel − Δactual| / max(|Δactual|, 2 ticks)
```

  - Δ = premium(T + h) − premium(T), using recorded mid = (bid + ask)/2.
  - It needs at least 15 sessions with at least 4 expiry days per index.
  - Pass: ≤ 0.15. If it fails, the pre-registered fallback marks P&L through recorded deltas, using a reserve slot.

## 9. Engines (`quantdesk/analysis/`)

Every function takes data frames and returns a frame or a value. None of them read files.

**Minute frame.** For index X on day d, `build_minute_frame` returns one row per minute stamp ts with:
- open, high, low, close
- vwap, vwap_sd, upper, lower
- vix
- adv_share = (adv − dec)/present, above_share = above_vwap/present, top5_ret
- session_high, session_low
- available_at

Row ts uses only data stamped ≤ ts.

- **VWAP proxy (§6.0):**
  - I_s = (H + L + C)/3 of the index.
  - vwap_t = Σ_{s≤t} I_s·tv_s / Σ_{s≤t} tv_s.
  - vwap_sd_t = √(Σ tv_s·(I_s − vwap_t)² / Σ tv_s).
  - At the first minute, if tv is 0, vwap = I_0.
- **Noise band (H1):**
  - σ(τ) = mean over the previous 14 sessions of the same type of |C_{d,τ}/O_d − 1|.
    - Type: expiry sessions of X versus non-expiry sessions.
    - Only regular sessions count.
    - Slot τ = minutes since 09:15.
  - upper_τ = max(O_t, C_{t−1}) × (1 + V·σ(τ)) and lower_τ = min(O_t, C_{t−1}) × (1 − V·σ(τ)), with V = 1.0.
  - O_t is the official open (from `daily`, or the first bar's open if `daily` lacks today) and C_{t−1} the official prior close.
- **H1 at check T**, using the bar at T − 1 minute:
  - long if close > upper and close > vwap
  - short if close < lower and close < vwap
  - otherwise none
- **Levels** (`levels_for(ctx, frame_row, side)`):
  - multiples of 100 (NIFTY) or 500 (SENSEX)
  - prior session high, low and close
  - prior Monday–Friday week high, low and close
  - multi-touch extremes: the session high is a resistance level if at least 2 bars came within 0.05% of it at least 3 minutes apart; the same for the low as support
- **Breadth agreement** (R20), for a long; mirror for a short:
  - count of [adv_share > 0, above_share > 0.5, top5_ret > 0] ≥ 2
- **Causal z-score** (`causal_z(history, value)`): z = (value − mean)/sd over the same feature's values at the same check time in the previous 250 sessions. It needs at least 60 values (else undefined) and is winsorised at ±3.
- **Technical family score**, sign-aligned (× +1 for long, × −1 for short):
  - location = mean of z[(close − vwap)/b] and z[distance to nearest opposing level / b]
  - confirmation = mean of z[adv_share], z[above_share − 0.5] and z[top5_ret]
  - score = mean(location, confirmation), clipped to ±3
- **Options-implied score**, from the previous session's `options_eod`, sign-aligned:
  - PCR_OI = Σ put OI / Σ call OI over the nearest weekly, strikes within ±10 steps of the prior close
  - RR25 = IV(call, Δ +0.25) − IV(put, Δ −0.25) at the nearest weekly with dte ≥ 1, from traded closes, interpolating IV in delta
  - score = mean(z[PCR_OI], z[RR25]) using causal z over 250 sessions
  - Convention: a positive score supports a long.
- **Macro engine:**
  - **Event gate:**
    - E3 day (election results): no trade.
    - Scheduled RBI: no entries before time + 45 minutes.
    - Budget: no entries before 13:00, and Δ_event = +0.04 for that day.
    - Rebalance day: hard exit 15:00.
    - Scheduled timed events: exit 5 minutes before.
    - Unscheduled events are ignored by the calendar gate (R9).
  - **Intraday VIX block:** |VIX_T / VIX_close_{t−1} − 1| > 0.08.
  - **Shock flag on day t**, if any of:
    - ln(VIX_close_{t−1} / VIX_close_{t−6}) ≥ 0.20
    - |r_on,t| ≥ 1.5·σ̂_gap,t
    - a variance-CUSUM alarm in sessions t−20 .. t−1

    If set, Δ_shock = +0.04 for that session and the next 4.
  - **Variance CUSUM:**
    - σ0 = sd of daily close-to-close log returns over the previous 250 sessions; σ1 = 1.5·σ0.
    - ℓ_t = ln(σ0/σ1) + r_t²/2·(1/σ0² − 1/σ1²).
    - S_t = max(0, S_{t−1} + ℓ_t); alarm when S_t > h, then reset S to 0.
    - h is calibrated once on 2019–2022 by a moving-block bootstrap (block 20 sessions, 1,000 resamples) so the alarm rate is 1 per 250 sessions. It is frozen in `config/frozen/shock_v1.yaml`.
  - **Stress score (0–8)**, from `macro` as of 09:05:
    - Brent ≥ 95: +1
    - Brent 5-day change ≥ +5%: +1 (≥ +10%: +2)
    - USD/INR 5-day change ≥ +0.75%: +1 (≥ +1.5%: +2)
    - US 10-year (DGS10) 5-day change ≥ +15 bp: +1
    - India 10-year 5-day change ≥ +15 bp: +1, with Δy ≈ −(ΔP/P)/7 from the G-sec price index
    - DXY 5-day change ≥ +1.5%: +1

    Tiers: Δ_stress = 0 for scores ≤ 2, +0.02 for 3–4, +0.04 for ≥ 5. It is capped at +0.02 unless RV-1 has been accepted.
  - **Macro family score**, sign-aligned:
    - post_holiday_fade = −sign(r_on,t) on the first session after a weekday exchange holiday
    - fii_flip = sign(ratio_{t−1} − 0.5) if the FII index-futures long ratio crossed 0.5 within the last 5 sessions
    - score = post_holiday_fade + fii_flip, in [−2, 2]
    - The expiry-weekday term in spec §5A.2 has no pre-registered direction, so it is dropped. The meta-model's days-to-expiry column carries expiry effects instead (ruling R39).
- **Hurdle total:** Δ = min(0.08, Δ_shock + Δ_stress + Δ_event + Δ_slowtrend + Δ_gamma). Each component counts only in trials whose configuration includes it: RV-2 shock, RV-1 stress at full tiers, RV-3 slow trend, RV-4 gamma. Δ_event always counts.

## 10. The pipeline (`quantdesk/strategy/pipeline.py`)

The entry point is `decide(ctx: DayContext, frame: DataFrame, at: datetime, cfg: TrialConfig, model, quotes) -> Decision`. Steps run in this order and stop at the first failure, recording its reason:

1. **Session:** `ctx.session_kind == "regular"`; otherwise reason `irregular_session`.
2. **Timeline:**
   - `at` is a check time: minute in {0, 15, 30, 45}, between 09:45 and 14:00, or 13:30 on X's expiry day.
   - No blocking event window applies.
   - The caps in the backtest state allow a trade.
3. **H1:** read the row at `at − 1 min`; record side, ref_close, upper, lower and vwap.
4. **Gates (§6.1 step 4):**
   1. **event_shock:** the event gate and the intraday VIX block.
   2. **stop_fit:**
      - stop_level = max(upper, vwap) for a long or min(lower, vwap) for a short; b = |ref_close − stop_level|.
      - Reject if b > 0.5 × S × σ_bt (one session's implied move).
      - The rupee test happens per strike in step 6.
   3. **room_in_time:**
      - 1.6 × σ_rem_pts ≥ 2 × (2.3·b + drag).
      - drag = −θ_bt × BT(at, at + 60 min) / |Δ| for the nearest-weekly ATM option, in index points.
   4. **room_to_run:** no level strictly between ref_close and ref_close ± 2.3·b.
   5. **volatility:**
      - ratio = σ_bt(at) / σ̂_day,t.
      - Reject if the ratio is above the 80th percentile of the same ratio at 09:45 over the previous 252 sessions.
   6. **confirmation:** breadth agreement ≥ 2 of 3.
   7. **spike_guard:**
      - Over the last 5 minutes, take each 1-minute change in the modelled ATM premium (nearest weekly).
      - None may exceed 4 × the median absolute 1-minute change at the same minute over the previous 14 sessions.
5. **Probability p:**
   - **B0:** p = Platt(equal-weight mean of the three family scores).
   - **From M1 on:** the ridge meta-model. The macro column's effect is clipped to ±0.08 of probability.
6. **Strike picker with EV:**
   1. **Candidates:**
      - Index X's own options, expiries expiry_1 and expiry_2.
      - Strikes from one step ITM to 1.5% OTM, on 50-point (NIFTY) or 100-point (SENSEX) steps.
      - Calls for longs, puts for shorts.
   2. **Pricing each candidate**, with lot = that expiry's lot:
      - entry ask = quote(ask) at `at`.
      - **Stop premium:** index at S_stop = ref_close ∓ 1.3·b, 15 minutes later, σ moved by the spot–vol beta; P_stop = mid − 3·h.
      - **Target premium:** index at ref_close ± 2.3·b, 60 minutes later; P_tgt = mid − h.
      - **Rupees:** L = (ask − P_stop)·lot + costs(ask, P_stop); G = (P_tgt − ask)·lot − costs(ask, P_tgt). Costs use `round_trip(..., day=TODAY)`.
   3. **Keep a candidate if all of these hold:**
      - ask·lot + 60 ≤ 9,500
      - L ≤ 400
      - G/L ≥ 1.5
      - 0.25 ≤ |Δ| ≤ 0.55
      - p ≥ L/(G + L) + 0.04 + Δ
      - EV = p·G − (1 − p)·L ≥ max(0.10 × 400, 75)
      - Kelly f* = p − (1 − p)·L/G ≥ L/10,000
   4. **Choose** the highest EV. Ties go to NIFTY, then the nearer expiry, then |Δ| closest to 0.40. If no candidate is left, the reason is `no_strike`.
7. **Alert:**
   - index, side, expiry, strike, kind, lot
   - entry limit = ask + 2 ticks
   - index stop and planning target
   - backstop SL-limit: trigger = ask − 400/lot, limit = trigger − max(10% of the trigger, 5 ticks)
   - p, Δ (by component), EV, G, L
   - reasons for and against: each family score's sign, the gates passed, the nearest level

## 11. Exits (`quantdesk/strategy/exits.py`)

`simulate_exit(trade: OpenTrade, frame: DataFrame, quotes, cfg) -> ExitResult` steps minute by minute from the fill.

**X1, E-trail with R2 execution:**
- **Trail.** Track `best`. Once the favourable move reaches 1.0·b, the trail is active, and the wanted stop is:
  - long: max(stop, best − 1.5·b, vwap)
  - short: min(stop, best + 1.5·b, vwap)
- **Ratchet alerts.** When the wanted stop improves on the current one and 10 minutes or more have passed since the last ratchet alert, send an alert at t. The stop changes at t + 2 minutes, because the owner acts on it by phone.
- **Model A (index alert).**
  - When a bar closes beyond the current stop at t, the exit fills at the bid at t + 2.
  - Time and event exits work the same way, with the same 2-minute delay:
    - **laggards:** if 1.0·b was never reached, exit at 30 minutes when |S/S0 − 1| ≤ 0.0005, and at 60 minutes in any case
    - **events:** exit 5 minutes before a timed scheduled event
    - **hard exits:** 15:10, or 15:00 on X's expiry day and on rebalance days
- **Model B (backstop).**
  - The premium SL-limit sits at the trigger and limit set at entry. Each ratchet moves it to the premium matching the new index stop, from the model at ratchet time.
  - It fills at the first minute whose modelled bid ≤ trigger, at max(limit, bid).
  - If bid < limit, it does not fill and model A applies.
- **Result:** the trade's P&L is the **lower** of model A and model B (R2). Record both.

**X0** uses the same machinery with these rules:
- stop at b, no trailing
- fixed target 2.3·b, a resting limit filled at the bid on the first minute that touches it
- exit when a bar closes across vwap against the trade
- stall at 45 minutes when |S/S0 − 1| ≤ 0.0005, deadline at 90 minutes
- hard exits

**X2** (only if the owner opts in) has no target and no trail. Its stop is max(stop, vwap) for a long, plus hard exits.

**P&L:**

```
pnl = (exit_premium − entry_premium)·lot − round_trip(entry, exit, lot, exchange, day=TODAY).total
R   = pnl / 400
```

Also record `costs_asof`, the costs with day = trade day, as the side column.

## 12. Backtester (`quantdesk/backtest/`)

`run(cfg, ticket, days, loader, delays=(0, 1, 3, 5)) -> BacktestResult`

For each regular session day d, for NIFTY (from 2019-02-11) and SENSEX (from 2024-01-01):
1. Build `ctx` with `loader.day_context(X, d)` and `frame` with `loader.minute_frame(X, d)`.
2. At each check time, call `decide`. Every H1 signal produces one row in `signals`, with the failing gate or the chosen strike.
3. **Caps (R31),** applied in time order across both indices:
   - at most 1 trade a day
   - at most 3 a week (Monday–Sunday)
   - at most ceil(100 × sessions in the month / sessions in the year) trades in the month

   A signal the caps block is logged with reason `cap`.
4. **Fill**, for each delay k:
   - **Entry price:** model ask at the bar T + k − 1, plus 1 tick.
   - **Chase cap:** if |S_fill − ref_close| > min(0.15·σ(τ)·O, 0.3·b), the result is `lapsed` with R = 0.
   - **Sign flip:** if the index close at T + 2 is back on the wrong side (inside the band, or across vwap), the result is `rejected_flip` with R = 0. This is decided for delays of 3 or more; for smaller delays it is only recorded.
5. **Exit:** `simulate_exit`.
6. **Outputs:**
   - `trades.parquet`: one row per signal per delay.
   - `daily_r.parquet`: every available day in range, with Σ R of its trades (0 if none).
   - **Splits:** results before and after 2024-06-01, 2024-11-20, 2025-09-01 and 2026-08-03.
   - Premium-turnover ledger: Σ entry premium × lot per year.
7. **Overlay (R31):** the same trades with the day (−₹400) and week (−₹1,000) loss limits and the ₹7,000 floor applied, as an "as-lived" equity curve. It is reported only, never used in gates.

**Placebo mode** (`ticket=None`):
- entries at random check times and sides from a seeded RNG
- the same fills and exits
- P&L is visible

This is the only way to run the engine on real data before a ticket exists. Its result must show no edge.

## 13. Meta-model (`quantdesk/strategy/meta.py`)

- **Rows:** every H1 signal in the training days, including signals later blocked by gates or caps. This is the "skipped setups" rule.
- **Label:** y = 1 if, from minute T on, the index close reaches ref ± 2.3·b before ref ∓ b and before the hard exit; otherwise 0.
- **Columns (6):** technical score, options score, macro score, side_long ∈ {0, 1}, har_percentile − 0.5, min(dte, 5)/5.
- **Fit:**
  - minimise Σ logloss + (λ/2)·‖β‖² with λ = 10, intercept not penalised
  - `scipy.optimize.minimize(method="L-BFGS-B")` with the analytic gradient
- **Calibration:**
  1. Split the training rows by time, 80% then 20%.
  2. Fit on the 80%; on the 20%, regress y on logit(p̂).
  3. If the 95% CI of the slope excludes 1, fit Platt (a, b) on that 20%.
  4. Refit the model on 100% and apply Platt if it was chosen.
- **Macro clip:** clip β_macro·x_macro to ±0.08 / (p0·(1 − p0)), where p0 is the training base rate.
- **B0 consensus:** s = mean(technical, options, macro); p = sigmoid(a + b·s), with a and b fitted on the training rows.
- **Saved** to `research/trials/<id>/model_<split>.json`: coefficients, Platt, base rate and hash.

## 14. Validation (`quantdesk/validation/`)

**CPCV:**
- Days: regular NIFTY sessions from 2019-02-11 to 2023-12-31, in 10 groups by half-year (2019-H1 is partial).
- Test sets: all C(10,2) = 45 pairs.
- Training: all other days, minus 20 sessions before and after each test group (R34, both sides).
- Paths: φ = 9. Each group is tested in 9 splits; path j takes, for each group, the j-th split that tests it.

**Per path:** n trades, mean net R and t = mean/sd·√n. "Median path" is the path with the median t.

**Walk-forward:**
- Train once on 2019-02-11..2023-12-31 minus 20 sessions.
- Run 2024-01-01..2025-12-31 (both indices).
- Gate: mean net R > 0.

**2026** is reported as "touched" (D4).

**DSR:**
- Data: the daily_r series of the median path (CPCV days) concatenated with the walk-forward.
- SR = mean/sd of daily R; T = number of days; γ3 = skew; γ4 = kurtosis (not excess).
- N = 46 + trials run. V = max(variance of SR across trials run, 0.04²).

```
SR0 = √V · ((1 − 0.5772)·Φ⁻¹(1 − 1/N) + 0.5772·Φ⁻¹(1 − 1/(N·e)))
DSR = Φ( (SR − SR0)·√(T − 1) / √(1 − γ3·SR + (γ4 − 1)/4·SR²) )
```

Pass: DSR ≥ 0.95.

**PBO (CSCV):**
1. Build matrix M of daily R (CPCV days × trials run so far, n ≥ 2) and cut it into S = 10 contiguous blocks.
2. For each of the C(10,5) = 252 choices of IS blocks:
   - take the trial with the best IS Sharpe
   - find its OOS rank ω in 1..n
   - λ = ln(ω′/(1 − ω′)) with ω′ = ω/(n + 1)
3. PBO = share of λ ≤ 0.

Pass: PBO ≤ 0.2. With one trial it does not apply.

**Permutation:**
1. For each traded signal, also simulate the mirror trade (opposite side, mirror option of the same moneyness, same timing and exit rules).
2. Over 1,000 rounds, flip the side at random within buckets (weekday × expiry day × VIX tercile) and take the mean R.
3. p = share of rounds with mean ≥ the actual mean.

Pass: p < 0.01.

**Other gates:**
- **Years:** mean net R by calendar year over 2020–2025 (median path for 2020–2023, walk-forward for 2024–2025). Pass: positive in at least 4 of 6.
- **Delay test:** the delay-3 run's median-path mean net R > 0.
- **Post-publication:** walk-forward mean R after 2024-06-01 ≥ 0.5 × the CPCV mean R. Otherwise the trigger is demoted to shadow.
- **Regime add-on** (RV-x vs its predecessor, on identical setups):
  - per-available-day mean P&L not lower
  - paired per-trade gain with t ≥ 1
  - better in at least 4 of 6 years
  - at least 30 trades per fold
  - then also the clean forward holdout before going live (R33)

**Verdict:**
- alert-on when the last accepted configuration in registry order passes `validation_pass`, plus `regime_addon` for add-ons, and the pricing check has passed.
- Otherwise alert-off.

## 15. Registry and tickets (`quantdesk/validation/registry.py`)

`Registry(research_dir, derived, repo)`:
- **`issue_ticket(trial_id) -> TrialTicket`** refuses when:
  - the cap of 13 is reached
  - the id is not in `hypotheses.yaml`, or has already run
  - `frozen` is not true, or the YAML hash differs from the `prereg-v1` tag's
  - the git tree is dirty
  - a prerequisite is unmet: pilots P1, P2, P4, P9, P10 and CLOCK reported; pricing check passed; earlier always-run trials done; the trial's `run_if` condition true
- **`record(ticket, result, metrics)`:**
  - appends a row to `experiments.csv`
  - writes `research/trials/<id>/{trades.parquet, daily_r.parquet, metrics.json, model_*.json}`
  - `cumulative_trials` = rows in the CSV
- **TrialTicket fields:** trial_id, slot, issued_at, commit, hypotheses_hash, data_hash, cumulative_trials.

## 16. Pilots (zero-trial; outputs in `research/pilots/<ID>.md`)

| Pilot | Computes | Decides |
|---|---|---|
| CLOCK | minute weights, θ_n, θ_w, θ_h and their SEs; the R(dte) table; skew b1/b2; γ_dn/γ_up | Writes the frozen files. Plan 1 |
| P9 | On front-month NIFTY futures days: share of minutes where side(index vs proxy) ≠ side(futures vs futures VWAP); median \|proxy − (futures VWAP − basis)\| / median b, where basis = futures close − index close at the same minute | The VWAP anchor (spec §6.0) |
| P4 | Nifty daily AR(1) and MAC(5) (mean of 5-day return autocorrelation lags), 2014–2026 and after 2015, with HAC SEs | Whether CTX runs |
| P1 | Per year, VIX tercile and lot era: count of H1 signals, stop_fit pass rate, picker pass rate, eligible setups per year. No P&L | The D2 checkpoint |
| P2 | For eligible setups in 2019–2022: MFE and MAE paths in units of b, time to MFE, share with MFE > 2.5b, retracement after MFE. Index only, no option P&L | The D1 reversal clause |
| P10 | Simulates trades from P1 counts and P2 excursion paths with a planted 2–4 point uplift; reports P(every gate passes) and the minimum detectable uplift at 80% power | Shown at D2 |
| P3, P5 | Gamma engine (prior-day OI) vs rest-of-day range; OI walls vs settlement | Only if RV-4 or ROD would run (P3); P5 is display |
| P6 | Depth and latency from recordings | SP3 cost check |
| P7 | Pretrained volatility models vs HAR | Time-boxed: HAR stays unless P7 is done by pre-flight |

**D2 checkpoint.** If eligible setups are fewer than 60 a year, or the high-VIX stop_fit pass rate is under half the low-VIX rate, the owner chooses between ₹15k/₹600 and alert-off. The owner also decides on X2.

## 17. Parameters to add to `hypotheses.yaml` before any run

Plan 1, task 1 adds these, each with `provenance: design_ruling` and a source line pointing here:
- `event.rebalance_hard_exit`: "15:00"
- `planning.stop_horizon_min`: 15
- `planning.target_horizon_min`: 60
- `fill.sign_flip_check_min`: 3
- `exit.x0_stall_min`: 45
- `exit.x0_deadline_min`: 90
- `macro.score_terms`: "post_holiday_fade + fii_flip (expiry term dropped, R39)"
- `macro.fii_flip_window`: 5
- `shock.cusum_sigma_window`: 250
- `shock.cusum_block`: 20
- `shock.cusum_resamples`: 1000
- `clock.weight_winsor_q`: 0.999
- `pricing.forward`: "F = S, r = 0"
- `pricing.skew_floor`: 0.5
- `pricing.skew_max_abs_z`: 3
- `har.overnight_c`: 1.0e-8
- `har.percentile_min`: 60
- `gate.vol_rich_reference_time`: "09:45"
- `gate.dsr_sr_sd_floor`: 0.04
- `cv.embargo_both_sides`: true
- `options_score.strike_steps`: 10
- `options_score.rr_delta`: 0.25
- `meta.calibration_split`: 0.8
- `alert.entry_limit_ticks`: 2
- `alert.backstop_limit`: "max(10% of trigger, 5 ticks)"

## 18. Testing strategy

- **Unit tests** use small synthetic frames built in the test. No test reads `data/`. Use `tests/fakes.py` patterns: inject clock and data.
- **Known answers:**
  - vectorised Black-76 equals the scalar version
  - Garman–Klass on a hand example
  - HAR recovers planted coefficients
  - the clock fit recovers planted θ values
  - the band matches a hand-computed example
  - DSR matches the formula on a fixed input
- **Truncation test:** a registry of every feature function. Each is run on a day cut at a random T and on the full day; outputs at or before T − 1 minute must be equal.
- **Controls before B0:**
  - placebo runs show no edge (|t| < 2)
  - a planted drift is recovered (t > 3)
  - the delay test runs
  - a recorded day replays through `decide`
- **No test asserts on P&L of real data.**

## 19. Known limitations, stated up front

- The backtest shows more trades than live, because the headline, depth and OFI gates are live-only (R30).
- HDFC Ltd is missing from breadth and the VWAP proxy until July 2023.
- Pricing is modelled, not recorded, until the pricing check passes. Expiry-day intraday pricing rests on R(1) until then.
- With 46 earlier looks counted, DSR ≥ 0.95 is hard to reach. P10 states the odds before any trial is spent.
