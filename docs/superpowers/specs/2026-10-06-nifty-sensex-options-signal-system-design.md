# Nifty/Sensex options signal system: design spec

- Date: 6 October 2026
- Status: draft for the owner's review

## Background reading

- `reports/RESEARCH_REPORT.md`
- `reports/Nifty options multifactor quant strategy.md`
- `research_notes/`

This is a personal research and alerting tool. It is not investment advice. It never places orders.

---

## 1. Purpose and success criteria

**Goal.** Run a local tool that, on the few days a measured edge exists, alerts the owner to buy one Nifty or Sensex weekly option intraday. Each alert gives:
- the contract
- entry, stop and target on both the index and the premium
- a hard exit time
- a calibrated probability and the expected value in rupees

On every other day it says "no trade". The owner places all orders manually in Angel One.

**What counts as success:**
1. A historical simulation (2019–2026) shows positive expectancy after full Indian costs. It must pass the pre-registered statistical gates in section 6.
2. Recorded live data confirms that the simulation's option-price model is accurate. The median error in the modelled premium change must be 15% or less.
3. Live trading with one lot, monitored by a sequential test, grows capital without hitting a kill-switch.
   - First goal: ₹10,000 to ₹11,000 (+10%).
   - Then compound towards larger capital.

**Possible outcome.** If the free experiments show no directional edge, the system should never fire. That is an acceptable, honest result.

## 2. Owner's constraints

| Item | Value |
|---|---|
| Capital | ₹10,000 |
| Risk per trade | ₹400 at the stop (4%), including stop slippage |
| Target | Net gain at least 1.5× the net loss. Payoff shapes 1.5×, 2× and 3× are tested in simulation and the best out-of-sample shape is kept. |
| Holding | Intraday only, flat by the session cutoff |
| Instruments | Nifty 50 weekly (Tuesday expiry, lot 65) and Sensex weekly (Thursday expiry, lot 20) |
| Broker / data | Angel One SmartAPI (free): read-only data use |
| Execution | Manual. The app has no order code. |
| Where | Windows PC, local web dashboard at `127.0.0.1:8000`, watched during market hours |
| Frequency cap | ≤1 trade a day and ≤3 a week |
| Loss limits | Day −₹400 (one loss ends the day), week −₹1,000, capital floor ₹7,000 (falls back to paper mode) |

## 3. What the research changed (summary)

- **Direction comes only from price-based triggers that have a mechanism behind them:**
  - H1, a regime-gated noise-band breakout. This is the core trigger.
  - Rest-of-day momentum at 14:45. It stays research-only until a Nifty test passes.
- **Opening option-order imbalance (9:15–9:25) is shadow-logged** until enough live data exists to test it.
- **Options-market, macro and sentiment data decide only whether, when, which contract and how big the move should be. They never decide the side.** For context: macro and global variables explain R² 0.002 of Nifty open-to-close.
- **Draft setups changed:**
  - H2 becomes a gated pullback variant of H1.
  - H3 (gap-down recovery) becomes a context feature.
  - H4 (first 30 minutes predicting the last hour) is dropped.
- **Breakeven win rate** is about 40–46% once real costs are included, not 35–38%.
- **Spreads** need about ₹29k of margin, so they are out of scope below about ₹50k of capital.
- **Option prices must use business time (trading time).** India VIX on a calendar-time clock underprices expiry-day ATM options by about half.
- **Validation is simulation-first:** historical replay, then a recorded-day replay, then a short paper check. The owner prefers this to a long paper phase.

## 4. System overview

```
Angel One SmartAPI (read-only)          NSE/BSE end-of-day files (free)      News RSS (free)
  live ticks, depth, option chain,        F&O bhavcopy, participant OI,        ET, BS, Mint, NDTV Profit,
  1-min candles, instrument master        FII/DII, India VIX                   NSE/BSE announcements, RBI, PIB
        │                                       │                                 │
        ▼                                       ▼                                 ▼
[SP1] DATA FOUNDATION: broker client · instruments · live recorder · history backfill · EOD jobs · calendar · storage
        ▼
[SP2] STRATEGY CORE (pure functions, shared by backtest and live)
        day card → triggers → gates → strike picker → meta-model → EV gate → alert object
      + BACKTESTER (replay 2019→today, business-time option pricing, cost model, experiment registry)
        ▼
[SP3] LIVE ENGINE + DASHBOARD + JOURNAL (alerts, paper/real trade log, replay mode, kill-switches)
```

**Core rule.** The backtester and the live engine call the same strategy-core functions with the same inputs. A parity test (section 8) enforces this.

**Build order.** There are three sub-projects. Each gets its own implementation plan:
1. **SP1, data foundation:** specified in full in section 5. It is built first so live recording starts as early as possible.
2. **SP2, strategy core + backtester:** design constraints are in section 6. A detailed design pass happens before its plan.
3. **SP3, live engine + dashboard + journal:** design constraints are in section 7. It gets a detailed design pass, with dashboard mockups, before its plan.

---

## 5. SP1: data foundation (full specification)

### 5.1 Scope

**In scope:**
- Angel One login and session handling
- Instrument resolution
- A live recorder
- Historical 1-minute backfill
- End-of-day downloads
- Global, macro and index-fundamental data collection (section 5.7a)
- The event and holiday calendar
- Storage layout
- Data-quality reports
- Command-line entry points

**Out of scope:** signals, backtesting and the dashboard.

### 5.2 Project layout

```
quantdesk/                 Python package
  config.py                loads config/settings.yaml + .env
  broker/angel.py          SmartAPI wrapper: login, candles, websocket. NO order methods.
  instruments.py           instrument master download, cache, token resolution
  recorder/
    live.py                market-hours recorder (websocket → 1-min snapshots + opening ticks)
    bars.py                tick → 1-min bar / snapshot aggregation (pure)
  history/backfill.py      1-min candle backfill with rate limiting and resume
  eod/
    nse.py, bse.py         bhavcopy, participant-wise OI, FII/DII downloads
  calendar/
    events.py              loads config/events.yaml, NSE/BSE holidays
  macro/collect.py         global, India-macro and index-fundamental data (section 5.7a)
  analysis/                built in SP2: technical.py and macro.py engines (section 5A)
  storage.py               Parquet writers, DuckDB views, immutable raw partitions
  quality.py               gap/sanity checks, daily health report
  cli.py                   `python -m quantdesk <command>`
config/settings.yaml       all tunable values (no secrets)
config/events.yaml         dated events (verified sources only)
.env                       secrets, git-ignored. .env.example is committed.
data/                      git-ignored
tests/                     pytest. Fixtures are saved API responses; tests make no live calls.
research/hypotheses.yaml   pre-registered hypotheses (used by SP2)
research/experiments.csv   append-only experiment registry (used by SP2)
```

### 5.3 Broker client (`broker/angel.py`)

**Login:**
- Uses the official `smartapi-python` SDK with client code, PIN and a TOTP code generated by `pyotp` from the owner's TOTP secret.
- Secrets are read from `.env`. The owner creates these credentials and fills in the file. The tool never asks for them anywhere else.
- Re-logs in automatically at 08:45 and whenever a session error comes back.

**Candles:**
- `getCandleData` wrapper with a token-bucket limiter set below the published limits (3 requests/second, 180/minute, 5,000/hour).
- Exponential backoff on HTTP 429/5xx errors.
- Chunks requests to the per-interval maximum day span.

**Websocket:**
- A SmartWebSocketV2 wrapper.
- Subscribes in snap-quote mode (LTP, 5-level depth, volume, OI) for the tokens it is given.
- Reconnects automatically with backoff and re-subscribes.
- Emits a "stale" event if no tick arrives for 30 seconds during market hours.

**Safety:** the module defines no order, modify or cancel functions. A unit test asserts that no such attribute exists.

### 5.4 Instruments (`instruments.py`)

- Downloads Angel One's daily instrument master JSON at 08:30 and caches it by date. If the download fails, it uses the previous day's cache, flags this, and still takes expiries only from a master.
- Resolves tokens for:
  - the NIFTY 50 and SENSEX indices and India VIX
  - current-month Nifty and Sensex futures
  - both indices' **current and next weekly expiries**, CE and PE, for ATM ± 15 strikes
  - the Nifty 50 constituents, for breadth
- Expiry dates always come from the master, never from calendar arithmetic.

### 5.5 Live recorder (`recorder/live.py`)

- **Run window:** started by the owner (or Windows Task Scheduler) around 09:00. Records 09:15–15:30, then flushes and writes the day's health report.
- **Every minute** it records:
  - 1-minute OHLC for the indices, futures, VIX and constituents (with volume where available)
  - for every option: last price, best bid and ask with their quantities, total traded volume and OI at the minute close
- **Opening ticks:** from 09:15 to 09:30, every option tick is also stored raw, for the order-flow research.
- **Re-centring:** when ATM moves more than 5 strikes from the subscribed centre, the recorder adds subscriptions so ATM ± 15 stays covered. Old strikes are not dropped during the day.
- **Subscription budget:** about 250 option tokens plus about 60 others. This is checked against Angel One's per-connection token limit at startup. If the limit is exceeded, the recorder falls back to ATM ± 10 and logs the reduction.
- **Writes:** Parquet once a minute, partitioned by `date` and `kind`. A crash loses at most one minute. Restarting the same day appends rather than overwriting.

### 5.6 History backfill (`history/backfill.py`)

- Targets 1-minute candles from 2019-01-01 to today for:
  - the NIFTY 50 index, SENSEX index and India VIX
  - the Nifty 50 constituents
  - Nifty and Sensex futures, if Angel One serves expired contracts
- The run resumes where it stopped, writes a manifest of what was fetched, and can be re-run safely.
- **Open item to settle while building SP1:**
  - Check whether expired futures 1-minute data can be fetched.
  - If not, VWAP for the backtest comes from constituent volume (index weights × constituent VWAP), and that substitution is documented.
- Daily history is backfilled for 2015 to today as a cross-check against Yahoo data already in `data/`.

### 5.7 End-of-day jobs (`eod/`), run after 18:30

- **Daily downloads:**
  - NSE F&O bhavcopy (UDiFF format)
  - BSE derivatives bhavcopy
  - NSE participant-wise OI (FII long/short)
  - FII/DII cash statistics
  - India VIX daily
- A one-off backfill of NSE and BSE bhavcopy back to 2019. This feeds the free tests: rebuilding dealer gamma, OI walls against settlement, and daily VRP.
- Requests are polite: browser-like headers, a session cookie and 1–2 seconds between requests. Raw files are kept unmodified.

### 5.7a Global, macro and fundamental data (`macro/collect.py`)

These feed the fundamental/macro engine (section 5A.2).

**Daily, at 07:30 and 18:30, from Yahoo Finance (free):**

| Ticker | Series |
|---|---|
| `BZ=F` | Brent |
| `INR=X` | USD/INR |
| `^TNX` | US 10-year yield |
| `DX-Y.NYB` | Dollar index |
| `ES=F`, `NQ=F` | S&P 500 and Nasdaq futures |
| `^GSPC` | S&P 500 |
| `^N225`, `^HSI`, `^KS11` | Nikkei, Hang Seng, KOSPI |
| `^INDIAVIX` | India VIX |
| `^NSEI`, `^BSESN`, `^NSEBANK` | Nifty, Sensex, Bank Nifty |

**Intraday, every 5 minutes during 09:00–15:30:** `ES=F`, `NQ=F`, `INR=X`, `BZ=F`, `^N225`, `^HSI`. Yahoo keeps only about 60 days of 5-minute data, so we store our own copy to build a lead-lag history.

**India rates and macro:**
- India 10-year G-sec yield (FBIL/CCIL daily benchmark).
- RBI policy rate and stance, recorded after each MPC.
- CPI, WPI, IIP and GDP prints (MOSPI). Each is stored as value and change vs the previous print.

**Index fundamentals:** Nifty 50 P/E, P/B and dividend yield from NSE's daily index data, backfilled to 2015.

**Flows:**
- FII/DII cash flows (also in section 5.7).
- FII index-futures long ratio from participant-wise OI.

**Manual monthly entries:**
- Results calendar for the top-10 Nifty weights.
- Nifty forward EPS revision direction (up, flat or down). Each entry carries a source URL.

### 5.8 Calendar (`calendar/events.py`, `config/events.yaml`)

- Fields per event: date, time (IST), type, gate level E0–E3, and a source URL.
- Types: RBI MPC, Union Budget, general/state election results, US FOMC/CPI/NFP, index rebalancing, and NSE/BSE holidays.
- **Every entry must carry a source URL.** Dates typed from memory are not allowed. This rule exists because the research notes flag that some historical RBI/FOMC dates were typed from memory.

### 5.9 Storage and quality

**Directory layout:**
- `data/raw/<source>/<date>/…`: immutable, never edited.
- `data/clean/…`: derived, can be rebuilt.
- DuckDB views over the Parquet files for queries.

**Daily health report (JSON, shown later in the dashboard's Research tab):**
- minutes recorded vs expected per instrument
- crossed or zero quotes
- stale periods
- re-centring events
- subscription count
- backfill progress

### 5.10 Commands

- `python -m quantdesk login-check`: verifies credentials and prints the session status.
- `python -m quantdesk record`: runs the live recorder for today.
- `python -m quantdesk backfill --what history|bhavcopy`.
- `python -m quantdesk eod`.
- `python -m quantdesk status`: prints data health and backfill progress.

### 5.11 SP1 error handling

| Failure | Behaviour |
|---|---|
| Login fails | Retry 3 times with backoff, then a clear error and non-zero exit. No partial recording without a session. |
| Websocket drop | Reconnect with backoff. Gap minutes are marked in the health report. |
| Stale feed > 30 s | Logged as a stale period. |
| Bad ticks (non-positive price, bid > ask, jump > 5% in a minute for the index) | Dropped and counted |
| Rate limit (429) | Backoff and resume |
| Instrument master missing | Use the previous day's file, flagged |
| NSE/BSE file not yet published | Retry hourly until 23:00, then mark it missing |

### 5.12 SP1 testing

- **Unit tests:**
  - bar and snapshot aggregation from synthetic ticks
  - token resolution from a saved instrument master
  - the rate limiter
  - backfill chunking and resume
  - bhavcopy parsers on saved files
  - event-file validation (every entry has a source)
  - the no-order-methods assertion
- **Recorded-fixture tests:** login, candles and websocket decoding replayed from saved responses.
- **Manual smoke test** on the first live day: the full recording session and the health report.

---

## 5A. Analysis engines (built in SP2, shown in SP3)

The system has two explicit engines that look at the market the way an experienced analyst would. Each engine produces:
- a readable report for the dashboard, so you can see the chart and macro picture yourself
- one numeric **family score** that feeds the meta-model

The research discipline still applies. Every indicator below is a *tested feature*: it earns weight only if it improves out-of-sample results, and each tested variant counts against the trial budget in section 6.3. Popular indicators that lack evidence are computed and shown, but they cannot trigger a trade on their own.

### 5A.1 Technical chart engine (`analysis/technical.py`)

| Area | What it computes | Timeframes | Role |
|---|---|---|---|
| Trend structure | 20/50/200-DMA position and slope; swing highs/lows (fractal pivots) giving higher-high/higher-low or lower-high/lower-low structure; EMA 9/21 on 5-min | Daily, 60-min, 15-min, 5-min | Trend-alignment score; the multi-timeframe agreement count is one input |
| Momentum | RSI(14), MACD histogram, ADX with +DI/−DI, rate of change | Daily, 15-min | Momentum score; RSI extremes as an overextension flag |
| Volatility | ATR(14), Bollinger bandwidth (squeeze → expansion), opening range, noise band, HAR-IV-ON remaining-day move | Daily, intraday | Sets stops and targets, plus a breakout-quality flag |
| Volume and flow | Futures VWAP and its bands; anchored VWAP from the day open and from the last swing; previous-day volume profile (POC, value-area high/low); 5-level order-flow imbalance | Intraday | Location score, confirmation and veto |
| Level map | Prior day/week high, low and close; round 100s; swing pivots; classic pivot/CPR levels (shown, untested); expiry-day OI walls | Daily and intraday | Room-to-run filter, targets and stops |
| Chart and candle patterns | Inside bar / narrow-range day; engulfing and rejection candles at key levels; flag/consolidation break; double top/bottom at prior extremes | 15-min, daily | Pattern flags (low evidence: feature only, never a trigger) |
| Breadth and leaders | Nifty 50 advance/decline, % of constituents above VWAP, weighted direction of the top-5 heavyweights (HDFC Bank, Reliance, ICICI Bank, Infosys, Bharti), Bank Nifty vs Nifty relative strength | Intraday | Confirmation score |
| Intermarket (intraday) | 5-min moves in S&P/Nasdaq futures, USD/INR, Brent, Nikkei/Hang Seng during Indian hours | Intraday | Lead-lag feature (to be tested; no published Indian evidence) |

**Technical family score:**
- Sign-aligned to the proposed side, winsorized at ±3, built from four sub-scores:
  - trend alignment
  - momentum
  - location (VWAP, value area, levels)
  - confirmation (breadth, leaders, order flow)
- Sub-scores are equal-weighted, as the research recommends for small samples. Learned weights come only via the meta-model.

### 5A.2 Fundamental / macro engine (`analysis/macro.py`)

The research showed macro data predicts *range, risk and timing*, not intraday direction (R² 0.002 for open-to-close). The engine is built for those jobs.

| Area | Inputs | Output |
|---|---|---|
| Event risk | RBI MPC, Budget, elections, US FOMC/CPI/NFP, index rebalances, heavyweight results | Gate level E0–E3, entry-time rules, range multiplier |
| Global overnight | US session return, S&P/Nasdaq futures, Asian indices, overnight gap size | Expected gap, overnight-shock range multiplier |
| Stress (oil, rupee, rates) | Brent level and 5-day change; USD/INR 5-day change; US 10-year and India 10-year 5-day change; dollar index; geopolitical-risk headline flag | 0–9 stress score, which raises the entry hurdle |
| Flows and positioning | FII/DII cash 5-day sum; FII index-futures long ratio and its flips; PCR-OI z-score | Positioning score (slow tilt) |
| Domestic macro | Latest CPI/WPI/IIP/GDP change vs previous; RBI rate and stance; India 10-year trend | Monetary/growth regime label: easing, neutral or tightening |
| Fundamentals | Nifty P/E and P/B percentile vs 10-year history; earnings yield minus India 10-year; EPS revision direction; results season of top weights | Valuation/earnings regime label (slow: weeks to months) |
| Calendar effects | Post-holiday, expiry day, turn of month (monitor only) | Context flags |

**Macro family score:**
- A capped direction tilt of at most ±8 probability points. It comes only from the context effects that showed in our data: post-holiday fade, the expiry-Tuesday pattern, and FII-flip events.
- It also feeds the stress-based hurdle and the range multipliers.
- The monetary and valuation regime labels are shown on the day card and enter the meta-model as one regime feature, shrunk.

### 5A.3 How the engines combine

1. The day card shows both engines' readings in plain words, for example "Trend: down on daily, up on 15-min; Momentum: oversold; Macro: tightening, stress 5/9, RBI day".
2. A trade needs the H1 trigger, all gates, and then the meta-model probability.
3. The meta-model sees the family scores: technical, options-implied and macro/context. Sentiment is a veto.
4. Every alert lists the chart reasons and macro reasons that supported or opposed it, so you can check the analysis yourself.

---

## 6. SP2: strategy core + backtester (design constraints for its own design pass)

### 6.1 Strategy pipeline (pure functions)

**1. Day card** (evening inputs, finalised about 09:05):
- **Event gate E0–E3.** Election results: no trade. Budget: only after the speech, at a higher hurdle. RBI: no entries until 30–45 minutes after the decision. Rebalance days: flat by 15:00.
- **Expected range** = VIX-implied move × event multiplier × overnight-shock multiplier. The multipliers are shrunk towards 1.0 until re-validated.
- **Stress score** (oil, rupee, yields, FII positioning, geopolitical risk), which raises the entry hurdle.
- Context flags: post-holiday, expiry day, gap size.
- The **instrument of the day**, from the affordability calendar. With ₹10k, closer-to-the-money strikes are affordable on more days.

**2. Timeline:**
- No entries before **09:45**. The 09:15–09:25 option flow is shadow-logged.
- H1 is checked every 15 minutes, until 13:30 on the contract's expiry day and 14:30 otherwise.
- One late-day momentum check at 14:45 on non-expiry days, once that setup has passed its test.

**3. Trigger (H1):**
- Price closes outside the noise band (open ± k × 14-day average absolute move from the open at this time of day, gap-adjusted) on the same side as VWAP.
- Separate bands on expiry days.
- The pullback variant is used only when the 10:15 trend-day probability is at least 0.6.

**4. Gates, in this order. All must pass:**
1. Event and shock gate: no severe unscheduled headline in the last 15–30 minutes, and intraday VIX within about ±8%.
2. Stop fit: the structural stop (band edge or VWAP) lies within the ₹400 budget, and the index target is at least 2.3× the stop.
3. Room to run: no opposing level (round 100s, prior-day high/low, session extremes) before the target.
4. Volatility gate: remaining-session implied move is not rich against the HAR-IV-ON forecast.
5. Confirmation: breadth agrees with the side, and 5-level order-flow imbalance is not more than 1 SD against it.

**5. Meta-model:**
- Pooled ridge logistic regression with at most 9 columns.
- One sign-aligned score per signal family: technical (section 5A.1), options-implied, and macro/context (section 5A.2). Sentiment is a veto only.
- One regime feature and one days-to-expiry or time feature.
- Estimates P(target before stop before deadline).
- Platt recalibration only if needed.

**6. EV gate:**
- p ≥ measured breakeven + a stress-dependent margin (+0.04, +0.06 or +0.08)
- EV ≥ +0.10R after measured costs
- Kelly check: f* ≥ loss / capital

**7. Strike picker:**
- Candidates: Nifty and Sensex, this and next weekly expiry, from 1 strike ITM to 1.5% OTM.
- Priced with a business-time Black-76 model calibrated to recorded chains, with skew and the spot–vol beta.
- A strike is kept only if:
  - premium × lot + ₹60 ≤ ₹9,500
  - loss at the stop, including three half-spreads, ≤ ₹400
  - net gain/loss ≥ the registered payoff shape
  - delta is 0.25–0.55
  - spread ≤ 2 ticks or 1.5% for Nifty (4 ticks or 2% for Sensex), with ≥5 lots on each side
  - EV ≥ ₹75
- The survivor with the highest EV is chosen. If none survives: no trade.

**8. Exits:**
- index stop
- index target
- a VWAP cross against the position
- a 45-minute stall (index within ±0.05% of entry)
- a 90-minute deadline
- hard exit at 15:00 on expiry days (before the 15:15 closing auction) and 15:10 otherwise

Orders are limit at mid + 1 tick and never chased more than 2 ticks. An SL-limit backstop is placed on the premium. Nothing is held overnight.

### 6.2 Backtester

- Replays 1-minute data from 2019 to today through the same functions.
- Entry is at the next bar plus a manual delay of 0, 1, 3 or 5 minutes. **Any signal whose sign flips at 3 minutes is rejected.**
- **Option P&L** uses the business-time pricing model. It is labelled "modelled" until the recorded-day replay validates it (median premium-change error ≤ 15%). If that check fails, outcomes are translated through recorded deltas instead.
- **Rules applied as they were on each historical date:**
  - lot sizes
  - STT rates
  - expiry weekdays (Thursday → Tuesday in Sep 2025)
  - closing auction from 3 Aug 2026
- **Costs** come from a unit-tested cost model (brokerage ₹20 per order, STT, exchange charges, SEBI fee, GST, stamp duty) plus a spread and slippage table measured from recorded data.

### 6.3 Validation protocol (pre-registered)

- `research/hypotheses.yaml` lists each hypothesis, its rules and its pass gates **before** it is tested.
- `research/experiments.csv` records every run: commit, data hash, parameters, metrics and the cumulative trial count. **Trial budget: 10–15 effective configurations.**
- **Splits:**
  1. Combinatorial purged cross-validation on 2019–2023 (10 half-year groups, 2 test groups, 5-day embargo).
  2. Frozen walk-forward on 2024–2025.
  3. **2026 used once** as a holdout.
- **Pass gates:**
  - out-of-sample t ≥ 2 on net returns
  - ≥30 trades per fold
  - positive after costs
  - consistent sign across years
  - permutation test
  - deflated Sharpe ≥ 0.95
  - probability of backtest overfitting ≤ 0.2
  - survives the 3-minute delay test
- **Free experiments to run first:**
  - rest-of-day momentum conditioned on dealer gamma, rebuilt from bhavcopy under three sign conventions
  - OI walls and max pain against settlement
  - H1 with option costs and delays
  - fit of the HAR volatility engine
- **Expected outcome:** if nothing passes, the system ships in alert-off (research) mode.

## 7. SP3: live engine, dashboard, journal (design constraints for its own design pass)

- **Tech:** FastAPI backend, a single clean page (plain HTML/JS with TradingView Lightweight Charts) and WebSocket updates. Bound to 127.0.0.1 only.
- **Today tab:**
  - status bar: session, data freshness, trades left, P&L, locks
  - day card with the technical and macro readings in plain words
  - Nifty and Sensex charts (1, 5, 15 and 60-minute and daily) with bands, VWAP, EMAs, swing structure, levels, value area, and RSI/MACD panes
  - a macro panel:
    - Brent, USD/INR, US and India 10-year, US futures, Asian markets
    - FII/DII flows and FII futures long ratio
    - stress score, event gate, and the monetary and valuation regime labels
  - alert card with a 3-minute expiry, "took it / skipped" buttons, a fill box, and the chart and macro reasons for and against
  - open-position tracker
  - sound and a browser notification on each alert
- **Journal tab:**
  - paper and real trades
  - equity curve
  - win rate, average win and loss, and EV against the simulation's expected band
  - predicted vs observed probability
  - how often the owner followed the system
- **Research tab:**
  - backtest reports
  - the experiment registry
  - recorder health
  - **replay mode:** any recorded day re-run, showing what the system would have alerted against what actually happened
- **Paper trading:** every alert becomes a paper trade, filled at the live ask + 1 tick and exited at the live bid.
- **Rollout (simulation-first, as the owner prefers):**
  1. The historical simulation passes its gates (section 6.3).
  2. Recorded-day replay validates the pricing model, using 2–4 weeks of recorded data.
  3. Paper trading for **2–4 weeks**, checking mechanics and cost only. It passes when there are no unresolved defects and measured costs are at most 20% above the assumption.
  4. Live trading with 1 lot.
- **Live monitoring and kill-switches** (whichever fires first):
  - the SPRT stop line, with boundaries recomputed from measured breakeven
  - a Bernoulli CUSUM alarm (9 points below the validated win rate, threshold 2.5)
  - capital ≤ ₹7,000
  - live costs more than 30% above assumption
- **Locks:** the daily, weekly and frequency caps from section 2. Unlocking needs a typed reason, which is saved to the journal.
- **Scaling:** stay at 1 lot until capital ≥ ₹20,000, ≥100 live trades, and an SPRT "GO". After that, lots = floor(capital / ₹10,000), with risk per trade ≤ 4% of capital. Drop one stage on a 20% drawdown from peak.

## 8. Cross-cutting tests

- **Parity test:** a recorded day replayed through the live engine must produce exactly the same alerts as the backtester.
- **Leakage tests:** every feature computed with data truncated at time t must equal the same feature computed from the full data. Random-entry and shuffled-signal placebos must show no edge.
- **Cost model** checked against worked examples (about ₹56–58 fixed per round trip at Angel One for the reference trades in the research notes).
- **Pricing model** checked against known Black-76 values and against recorded chains.

## 9. Open items to settle during implementation

1. Can Angel One serve expired futures 1-minute candles? This decides the source of VWAP (section 5.6).
2. Angel One's websocket token limit per connection and the OI update frequency.
3. The current Sensex lot size and tick sizes: confirm from the instrument master.
4. The India VIX expiry rule, needed for business-time scaling.
5. A cheap source of historical expired-option 1-minute data, only if the pricing check fails.

## 10. Risks

- **No edge.** The most likely outcome for any single hypothesis. Handled by pre-registration and alert-off mode.
- **Pricing-model error** inflates backtest results. Handled by the recorded-day validation.
- **Regime change** (2026 war/rates regime, rule changes such as a possible SEBI settlement change). Handled by the 2026 holdout, CUSUM and dates in config.
- **Owner discipline.** Handled by locks, the journal and a 3-minute alert expiry.
