# Nifty/Sensex options signal system: design spec

- Date: 6 October 2026
- Revised: 19 October 2026 (analyst desk, OpenBB data layer, timing decisions D1–D7)
- Status: draft for the owner's review

## Background reading

**Reports:**
- `reports/RESEARCH_REPORT.md`
- `reports/Nifty options multifactor quant strategy.md`
- `reports/Nifty options strategy timing refinement.md`

**Notes:**
- `research_notes/05_open_source_tools_evaluation.md`
- `research_notes/`

**Decision log:** `docs/decisions.md`

This is a personal research and alerting tool. It is not investment advice. It never places orders.

---

## 1. Purpose and success criteria

**Goal.** Run a local tool that, on the few days a measured edge exists, alerts the owner to buy one Nifty or Sensex weekly option intraday. Each alert gives:
- the contract
- entry, stop and planning target on both the index and the premium
- the exit rules and a hard exit time
- a calibrated probability and the expected value in rupees

On every other day it says "no trade". The owner places all orders manually in Angel One.

An LLM **analyst desk** writes a daily market brief with bull, bear and risk cases. It explains; it does not decide.

**What counts as success:**
1. A historical simulation (2019–2026) shows positive expectancy after full Indian costs. It must pass the pre-registered statistical gates in section 6.3.
2. Recorded live data confirms that the simulation's option-price model is accurate. The median error in the modelled premium change must be 15% or less.
3. Live trading with one lot, monitored by sequential tests on **mean net R per trade**, grows capital without hitting a kill-switch.
   - First goal: ₹10,000 to ₹11,000 (+10%).
   - Then compound towards larger capital.

**Win rate is not the goal.** With trailing exits it is expected to be about 21–35%. Profit comes from winners that are larger than the losers. (D1)

**Possible outcome.** If the free experiments show no directional edge, the system should never fire. That is an acceptable, honest result. The research makes this the single most likely outcome.

## 2. Owner's constraints

| Item | Value |
|---|---|
| Capital | ₹10,000 |
| Risk per trade | ₹400 at the stop (4%), including stop slippage and overshoot |
| Target | Planning target ≥ 2.3× the stop distance on the index, so that the net gain is ≥ 1.5× the net loss. Used for strike choice and the EV gate. Actual exits follow the trailing rule (section 6.1, step 8). |
| Holding | Intraday only, flat by the session cutoff |
| Instruments | Nifty 50 weekly (Tuesday expiry, lot 65) and Sensex weekly (Thursday expiry, lot 20) |
| Broker / data | Angel One SmartAPI (free): read-only data use |
| Global/macro data | OpenBB (lean install, free providers) plus yfinance |
| LLM | Groq free tier, for the analyst desk only. Explanation-only (D7). |
| Execution | Manual. The app has no order code. |
| Where | Windows PC (Ryzen 7, 16 GB RAM, RTX 3050 4 GB), local web dashboard at `127.0.0.1:8000`, watched during market hours |
| Frequency | ≤1 trade a day, ≤3 a week (hard ceiling), and a budget of ≤100 live trade-days a year spread pro-rata by month (D3) |
| Turnover | A premium-turnover ledger aiming to stay under ₹10 lakh a year (D3) |
| Loss limits | Day −₹400 (one loss ends the day), week −₹1,000, capital floor ₹7,000 (falls back to paper mode). An annual review sends a net-negative live year back to shadow mode. |

## 3. What the research changed (summary)

- **Proven long-run track records belong to:**
  - trend followers
  - option sellers, who collect the premium buyers pay
  - algorithmic machines

  No intraday option-buying method has a verified live record anywhere. Only about 0.5% of Indian F&O traders who traded all five years were profitable in every one of them.
- **Direction comes only from price-based triggers that have a mechanism behind them:**
  - H1, a regime-gated noise-band breakout. This is the core trigger.
  - Rest-of-day momentum. Shadow-only until a Nifty test passes.
- **The raw breakout edge has been close to zero since the Tuesday-expiry change** (Nifty +1.0 bp per signal, t 0.2). The pipeline is built to be able to say "alert-off".
- **Opening option-order imbalance (9:15–9:25) is shadow-logged** until enough live data exists to test it.
- **Options-market, macro and sentiment data decide only whether, when, which contract and how big the move should be. They never decide the side.** Macro and global variables explain R² 0.002 of Nifty open-to-close.
- **Draft setups changed:**
  - H2 (pullback) is **dropped**. Resting pullback entries fill on the breakouts that fail.
  - H3 (gap-down recovery) becomes a context feature.
  - H4 (first 30 minutes predicting the last hour) is dropped.
- **Exits matter more than entries.** A trail that starts after one stop-distance of profit, with the stop ratcheted up to VWAP, beat fixed targets in all 21 modelled cells (D1).
- **Regime signals raise the probability hurdle by at most 8 points. They never switch the system off.** Filtering by the strategy's own recent P&L made results worse on Nifty data.
- **Breakeven win rate** is about 40–46% for fixed 1:2 payoffs once real costs are included. Under trailing exits, the scoreboard is net R per trade.
- **Spreads** need about ₹29k of margin, so they are out of scope below about ₹50k of capital.
- **Option prices must use business time.** India VIX on a calendar-time clock underprices expiry-day ATM options by about half.
- **Validation is simulation-first:** historical replay, then a recorded-day replay, then a short paper check.
- **LLM trading agents** (TradingAgents and similar) have no verified out-of-sample record and cannot be replayed honestly on history. The desk is explanation-only and scored forward-only (D7).

## 4. System overview

```
Angel One SmartAPI (read-only)     NSE/BSE end-of-day files     OpenBB + yfinance (free)        India news RSS (free)
 live ticks, depth, option chain,   F&O bhavcopy, participant    US yields, USD/INR, Brent,      ET, BS, Mint, NDTV Profit,
 1-min candles, instrument master   OI, FII/DII, India VIX       global calendar, India macro,   NSE/BSE announcements,
                                                                  global indices and futures      RBI, PIB, GDELT
        │                                │                              │                              │
        ▼                                ▼                              ▼                              ▼
[SP1] DATA FOUNDATION: broker client · instruments · live recorder · depth logger · history backfill · EOD jobs ·
                       macro collector · news collector · calendar · storage · quality reports
        ▼                                                                                   ▼
[SP2] STRATEGY CORE (pure functions, shared by backtest and live)                [SP4] ANALYST DESK (Groq LLM)
        day card → trigger → gates → meta-model → EV gate → strike picker →          evening brief + morning update,
        exit plan → alert object                                                      bull/bear/risk, caution flags,
      + BACKTESTER (replay 2019→today, business-time pricing, costs, registry)        forward-scored, no trade vote
        ▼                                                                                   ▼
[SP3] LIVE ENGINE + DASHBOARD + JOURNAL (alerts, analyst-desk panel, paper/real trade log, replay mode, kill-switches)
```

**Core rule.** The backtester and the live engine call the same strategy-core functions with the same inputs. A parity test (section 8) enforces this. The LLM desk stays outside this path, so the core remains deterministic and replayable.

**Build order.** Each sub-project gets its own implementation plan:
1. **SP1, data foundation.** Specified in full in section 5. Built first so live recording starts as early as possible.
2. **SP4 phase 0, desk pilot and shadow log.** Starts right after SP1, because the desk's forward-test clock is the binding constraint. Specified in section 7A.
3. **SP2, strategy core + backtester.** Section 6. Gets a detailed design pass before its plan.
4. **SP3, live engine + dashboard + journal.** Section 7. Gets a detailed design pass, with dashboard mockups, before its plan.
5. **SP4 integration.** The desk panel goes into the dashboard.

---

## 5. SP1: data foundation (full specification)

### 5.1 Scope

**In scope:**
- Angel One login and session handling
- Instrument resolution
- A live recorder and an option-depth logger
- Historical 1-minute backfill
- End-of-day downloads
- Global, macro and index-fundamental data collection (section 5.7a)
- The India news collector (section 5.7b)
- The event and holiday calendar
- Storage layout
- Data-quality reports
- Command-line entry points

**Out of scope:** signals, backtesting, the analyst desk and the dashboard.

### 5.2 Project layout

```
quantdesk/                 Python package
  config.py                loads config/settings.yaml + .env
  broker/angel.py          SmartAPI wrapper: login, candles, websocket. NO order methods.
  instruments.py           instrument master download, cache, token resolution
  recorder/
    live.py                market-hours recorder (websocket → 1-min snapshots + opening ticks + depth log)
    bars.py                tick → 1-min bar / snapshot aggregation (pure)
  history/backfill.py      1-min candle backfill with rate limiting and resume
  eod/
    nse.py, bse.py         bhavcopy, participant-wise OI, FII/DII downloads
  macro/collect.py         OpenBB + yfinance global/macro/fundamental data (section 5.7a)
  news/collect.py          India news RSS/GDELT poller (section 5.7b)
  calendar/
    events.py              loads config/events.yaml, NSE/BSE holidays
  analysis/                built in SP2: technical.py and macro.py engines (section 5A)
  desk/                    built in SP4: ta_adapter.py or compact.py (section 7A)
  storage.py               Parquet writers, DuckDB views, immutable raw partitions
  quality.py               gap/sanity checks, daily health report
  cli.py                   `python -m quantdesk <command>`
config/settings.yaml       all tunable values (no secrets)
config/events.yaml         dated events (verified sources only)
config/news_feeds.yaml     RSS feed list
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
- `getCandleData` wrapper with a token-bucket limiter set below the published limits (3 requests/second, 120/minute, 5,000/hour, counted per client code; corrected 21 Oct 2026 from the RateLimit page).
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
- **Option-depth logger:** for ATM ± 3 strikes on both weeklies, the full 5-level depth every minute. This measures spreads and depth by time of day, which no published Indian source covers.
- **Opening ticks:** from 09:15 to 09:30, every option tick is also stored raw, for the order-flow research.
- **Latency fields:** each record carries the exchange timestamp and the local receive time.
  - SP3 adds alert time, owner-reported fill time and fill price.
  - Index levels at each of those moments are stored.
  - Every non-fill and override is logged.
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

These feed the fundamental/macro engine (section 5A.2) and the analyst desk.

**OpenBB, lean install** (Apache-2.0):

```
pip install openbb-core openbb-fred openbb-federal-reserve openbb-oecd openbb-imf openbb-nasdaq openbb-ecb openbb-mcp-server
```

- Set `OPENBB_AUTO_BUILD=false` and run `openbb-build` once after install.
- The full `openbb` meta-package is not used, because it is heavy.
- The AGPL `openbb-yfinance` add-on is not used either. Prices come from the plain `yfinance` library, which is already installed.
- The FRED API key (free) goes in `.env` as `FRED_API_KEY`. The owner creates it.

| Series | Source | Call / ticker |
|---|---|---|
| US 10-year yield | OpenBB Federal Reserve (no key); FRED DGS10 as a cross-check | `obb.federal_reserve.treasury_rates()`, field `year_10` |
| USD/INR | yfinance for daily and intraday; FRED DEXINUS as a lagged cross-check | `INR=X`; `obb.fred.economy.fred_series(symbol="DEXINUS")` |
| Brent | yfinance; FRED spot as a cross-check | `BZ=F`; `obb.fred.commodity.price.spot(commodity="brent")` |
| Dollar index | yfinance | `DX-Y.NYB` |
| US index futures and indices | yfinance | `ES=F`, `NQ=F`, `^GSPC` |
| Asian indices | yfinance | `^N225`, `^HSI`, `^KS11` |
| Indian indices and VIX | yfinance (cross-check only; Angel One is primary) | `^NSEI`, `^BSESN`, `^NSEBANK`, `^INDIAVIX` |
| India CPI, real GDP, short and long rates | OpenBB OECD and IMF | `obb.oecd.cpi(country="india")`, `obb.oecd.gdp_real(country="india")`, `obb.oecd.country_interest_rates(country="india")`, `obb.imf.cpi(country="IND")` |
| Global economic calendar | OpenBB Nasdaq (no key) | `obb.nasdaq.economy.calendar(start_date, end_date)` for US and global events |
| India 10-year G-sec | FBIL/CCIL daily benchmark (direct download) | — |
| RBI policy rate and stance | Recorded after each MPC in `config/events.yaml`, with source URL | — |
| Nifty 50 P/E, P/B, dividend yield | NSE daily index data, backfilled to 2015 | — |
| FII/DII flows, FII futures long ratio | Section 5.7 EOD jobs | — |

**Schedule:**
- Daily pulls at 07:30 and 18:30.
- Intraday every 5 minutes during 09:00–15:30 for `ES=F`, `NQ=F`, `INR=X`, `BZ=F`, `^N225`, `^HSI`. Yahoo keeps only about 60 days of 5-minute data, so we store our own copy.

**India-specific events** (RBI, Budget, elections, results of the top-10 weights) come only from `config/events.yaml`, never from a vendor calendar.

**Manual monthly entries:** the results calendar for the top-10 Nifty weights and the Nifty forward-EPS revision direction, each with a source URL.

**OpenBB MCP server.** For research sessions, `openbb-mcp --transport streamable-http --allowed-categories fred,federal_reserve,oecd,imf,nasdaq,ecb` serves `http://127.0.0.1:8001/mcp`. Add it to Claude Code with:

```
claude mcp add --transport http openbb http://127.0.0.1:8001/mcp
```

It is a research convenience. The engine does not depend on it.

### 5.7b India news collector (`news/collect.py`)

- **Feeds (`config/news_feeds.yaml`):**
  - Economic Times markets and economy
  - Business Standard markets and economy
  - Mint markets
  - NDTV Profit
  - NSE corporate announcements
  - BSE notices
  - RBI press releases
  - PIB economy
  - GDELT 15-minute files filtered to India and markets
  - Moneycontrol RSS is excluded: it has not updated since April 2024.
- **Polling:** every 5 minutes from 07:00 to 19:30 on trading days, hourly otherwise.
- **Timestamps:** the time our poller first saw each item, not the feed's `pubDate`. Both are stored.
- **Storage:** raw items (title, link, source, both timestamps, summary) to `data/raw/news/<date>/`, de-duplicated by URL and title hash.
- **Headline filter:** headlines that only restate the market move ("Sensex tanks 800 points") are tagged `price_restatement`, so the desk and any later test can drop them.
- **Users:** the analyst desk (section 7A) and the news-shock veto (section 6.1, step 4).

### 5.8 Calendar (`calendar/events.py`, `config/events.yaml`)

- Fields per event: date, time (IST), type, gate level E0–E3, and a source URL.
- Types: RBI MPC, Union Budget, general/state election results, US FOMC/CPI/NFP, index rebalancing, top-10 weight results, and NSE/BSE holidays.
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
- news items collected per feed
- macro pulls succeeded or failed
- backfill progress

### 5.10 Commands

- `python -m quantdesk login-check`: verifies credentials and prints the session status.
- `python -m quantdesk record`: runs the live recorder and depth logger for today.
- `python -m quantdesk backfill --what history|bhavcopy|fundamentals`.
- `python -m quantdesk eod`.
- `python -m quantdesk macro [--intraday]`.
- `python -m quantdesk news`: runs the news poller.
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
| OpenBB/yfinance/FRED call fails | Retry twice, then mark the series missing for that pull. Never block the recorder. |
| A news feed fails or goes stale for more than 24 h | Mark the feed stale in the health report |

### 5.12 SP1 testing

- **Unit tests:**
  - bar and snapshot aggregation from synthetic ticks
  - token resolution from a saved instrument master
  - the rate limiter
  - backfill chunking and resume
  - bhavcopy parsers on saved files
  - macro-collector parsing on saved OpenBB/yfinance responses
  - news de-duplication and first-seen timestamps
  - the price-restatement tagger
  - event-file validation (every entry has a source)
  - the no-order-methods assertion
- **Recorded-fixture tests:** login, candles and websocket decoding replayed from saved responses.
- **Manual smoke test** on the first live day: the full recording session and the health report.

---

## 5A. Analysis engines (built in SP2, shown in SP3)

The system has two explicit engines that look at the market the way an experienced analyst would. Each engine produces:
- a readable report for the dashboard, so you can see the chart and macro picture yourself
- one numeric **family score** that feeds the meta-model

The research discipline still applies. Every indicator below is a *tested feature*: it earns weight only if a registry trial admits it, and each tested variant counts against the trial budget in section 6.3.

**Shown but never gating** (their tests came out null or reversed):
- trend alignment
- NR7 and inside-day flags
- candle and chart patterns
- RSI and other oscillator extremes
- pivot/CPR levels
- 200-DMA, ADX, VIX-level, Brent and rupee gates

### 5A.1 Technical chart engine (`analysis/technical.py`)

| Area | What it computes | Timeframes | Role |
|---|---|---|---|
| Trend structure | 20/50/200-DMA position and slope; swing highs/lows (fractal pivots) giving higher-high/higher-low or lower-high/lower-low structure; EMA 9/21 on 5-min | Daily, 60-min, 15-min, 5-min | Displayed; the slow-trend part feeds the hurdle layer (RV-3) |
| Momentum | RSI(14), MACD histogram, ADX with +DI/−DI, rate of change | Daily, 15-min | Displayed |
| Volatility | ATR(14), Bollinger bandwidth, opening range, noise band, HAR-IV-ON remaining-day move and its percentile (or the forecaster chosen by pilot 7 in §6.3) | Daily, intraday | Sets stops and targets. The HAR percentile is the meta-model's regime feature. |
| Volume and flow | Futures VWAP and its bands; anchored VWAP from the day open and from the last swing; previous-day volume profile (POC, value-area high/low); 5-level order-flow imbalance | Intraday | Location score, trailing-stop anchor, OFI veto |
| Level map | Prior day/week high, low and close; round 100s; swing pivots; classic pivot/CPR (shown only); expiry-day OI walls | Daily and intraday | Room-to-run gate, targets and stops |
| Chart and candle patterns | Inside bar / narrow-range day; engulfing and rejection candles at key levels; flag/consolidation break; double top/bottom at prior extremes | 15-min, daily | Displayed only |
| Breadth and leaders | Nifty 50 advance/decline, % of constituents above VWAP, weighted direction of the top-5 heavyweights, Bank Nifty vs Nifty relative strength | Intraday | Confirmation gate |
| Intermarket (intraday) | 5-min moves in S&P/Nasdaq futures, USD/INR, Brent, Nikkei/Hang Seng during Indian hours | Intraday | Shadow feature, to be tested; no published Indian evidence |

**Technical family score:** sign-aligned to the proposed side, winsorized at ±3. Two sub-scores, equal-weighted as the research recommends for small samples:
- location (VWAP, value area, levels)
- confirmation (breadth, leaders, order flow)

### 5A.2 Fundamental / macro engine (`analysis/macro.py`)

The research showed macro data predicts *range, risk and timing*, not intraday direction (R² 0.002 for open-to-close). The engine is built for those jobs. Its sources are listed in section 5.7a.

| Area | Inputs | Output |
|---|---|---|
| Event risk | RBI MPC, Budget, elections, US FOMC/CPI/NFP, index rebalances, top-10 weight results | Gate level E0–E3, entry-time rules, range multiplier, exit 5 minutes before scheduled announcements |
| Global overnight | US session return, S&P/Nasdaq futures, Asian indices, overnight gap size | Expected gap, overnight-shock range multiplier, shock hurdle (RV-2) |
| Stress (oil, rupee, rates) | Brent level and 5-day change; USD/INR 5-day change; US 10-year and India 10-year 5-day change; dollar index; geopolitical headline flag | 0–9 stress score. Raises the hurdle by at most +0.02 unless trial RV-1 passes. |
| Flows and positioning | FII/DII cash 5-day sum; FII index-futures long ratio and its flips; PCR-OI z-score | Displayed; context |
| Domestic macro | Latest CPI/GDP change vs previous (OECD/IMF); RBI rate and stance; India 10-year trend | Monetary regime label: easing, neutral or tightening. Displayed. |
| Fundamentals | Nifty P/E and P/B percentile vs 10-year history; earnings yield minus India 10-year; EPS revision direction; results season of top weights | Valuation/earnings regime label. Slow; displayed. |
| Calendar effects | Post-holiday, expiry day, turn of month | Context flags |

**Macro family score:**
- A capped direction tilt of at most ±8 probability points, only from the context effects that showed in our data: post-holiday fade, the expiry-Tuesday pattern, and FII-flip events.
- It also feeds the range multipliers and the hurdle layer.

### 5A.3 How the engines combine

1. The day card shows both engines' readings in plain words, for example "Trend: down on daily, up on 15-min; Momentum: oversold; Macro: tightening, stress 5/9, RBI day".
2. A trade needs the H1 trigger, all gates, the meta-model probability and the EV gate.
3. The meta-model sees the family scores (technical, options-implied, macro/context), a call/put side dummy and the HAR percentile. Sentiment is a veto only.
4. Every alert lists the chart reasons and macro reasons that supported or opposed it.
5. The analyst desk's brief (section 7A) sits beside the alert as commentary.

---

## 6. SP2: strategy core + backtester (design constraints for its own design pass)

### 6.1 Strategy pipeline (pure functions)

**1. Day card** (evening inputs, finalised about 09:05):
- **Event gate E0–E3.**
  - Election results: no trade.
  - Budget: only after the speech, at a higher hurdle.
  - RBI: no entries until 30–45 minutes after the decision.
  - Rebalance days: flat by 15:00.
- **Expected range** = VIX-implied move × event multiplier × overnight-shock multiplier. The multipliers are shrunk towards 1.0 until re-validated.
- **Hurdle layer Δ** (≤ 0.08 in total) from the shock, stress and slow-trend components that pass their trials.
- Context flags: post-holiday, expiry day, gap size.
- The **instrument of the day**, from the affordability calendar. With ₹10k, closer-to-the-money strikes are affordable on more days.

**2. Timeline:**
- No entries before **09:45**. The 09:15–09:25 option flow is shadow-logged.
- H1 is checked on the **completed 1-minute bar at :00, :15, :30 and :45**.
- The **last entry** is 13:30 on the contract's expiry day and **14:00** otherwise.
- A "setup forming" pre-alert goes out 5 minutes before a likely trigger.
- Rest-of-day momentum at 14:45 is **shadow-logged only** (trial ROD).
- Spot prints after 15:15 are never used.

**3. Trigger (H1):**
- Price closes outside the noise band (open ± V × 14-day average absolute move from the open at this time of day, gap-adjusted, **V = 1.0**) on the same side as VWAP.
- Separate bands on expiry days.
- No extra confirmation bar. No pullback variant.

**4. Gates, in this order. All must pass:**
1. **Event and shock gate:** no severe unscheduled headline in the last 15–30 minutes (from the news collector, read by the classifier chosen in pilot 8), and intraday VIX within about ±8%.
2. **Stop fit:** the structural stop (band edge or VWAP) × a 1.3 overshoot factor fits the ₹400 budget, and the index planning target is ≥ 2.3× the stop. Re-checked at the fill.
3. **Room in time:** the expected remaining excursion is at least 2 × (target distance + theta drag), with the multiplier fixed in advance.
4. **Room to run:** no opposing level (round 100s, prior-day high/low, multi-touch session extremes) before the target.
5. **Volatility gate:** the remaining-session implied move is not rich against the HAR-IV-ON forecast.
6. **Confirmation:** breadth agrees with the side, and 5-level order-flow imbalance over the last 3–5 minutes is not more than 1 SD against it.
7. **Spike guard:** no entry within 5 minutes of an abrupt ATM premium spike.

**5. Meta-model:**
- Pooled ridge logistic regression with at most 9 columns:
  - the technical, options-implied and macro/context family scores
  - a **call/put side dummy**
  - the **HAR volatility percentile** as the single regime feature
  - one days-to-expiry or time-of-day feature
- Trend and gamma live in the hurdle layer, not here, to avoid double counting.
- Sentiment is a veto only.
- Estimates P(target before stop before deadline).
- Platt recalibration only if needed.

**6. EV gate:**
- p ≥ measured breakeven + 0.04 + Δ (hurdle layer, Δ ≤ 0.08)
- EV ≥ +0.10R after measured costs
- Kelly check: f* ≥ loss / capital
- Plan around a probability uplift of only 2–4 points. No live intraday method shows more.

**7. Strike picker:**
- Candidates: Nifty and Sensex, this and next weekly expiry, from 1 strike ITM to 1.5% OTM.
- Priced with a business-time Black-76 model calibrated to recorded chains, with skew and the spot–vol beta.
- A strike is kept only if:
  - premium × lot + ₹60 ≤ ₹9,500
  - loss at the stop, including three half-spreads and the overshoot factor, ≤ ₹400
  - net gain/loss at the planning target ≥ 1.5
  - delta is 0.25–0.55, **never relaxed to make a trade fit**
  - spread ≤ 2 ticks or 1.5% for Nifty (4 ticks or 2% for Sensex), with ≥5 lots on each side
  - EV ≥ ₹75
- The survivor with the highest EV is chosen. If none survives: no trade.

**8. Orders and exits:**
- **Entry:** a marketable limit at the ask + ≤ 2 ticks, with a chase cap on the index level. Re-price once, then abandon. The alert lapses after 5 minutes or at the next check, whichever is first.
- **Backstop:** an SL-limit order on the premium, placed within 30 seconds of the fill and ratcheted to the trail every 5–10 minutes. If the backstop is breached without a fill, exit immediately with a marketable order. Overrides are logged. SL-M orders are banned for options.
- **Exit rules, E-trail (D1):**
  - **Initial stop:** the structural stop b.
  - **Trail:** once the index has moved +1b in favour, trail the stop at 1.5b behind the best price, with stop = max(trail, VWAP).
  - **No move to breakeven.**
  - **Laggard time stops:** a trade that never reached +1b exits at 30 minutes if the index is within ±0.05% of entry, and at 60 minutes in any case.
  - **Events:** exit 5 minutes before any scheduled announcement.
  - **Hard exits:** 15:00 on expiry days (before the 15:15 closing auction) and 15:10 otherwise.
- Nothing is held overnight.

### 6.2 Backtester

- Replays 1-minute data from 2019 to today through the same functions.
- **Simulates the whole delay, chase and expiry policy.** Skipped or lapsed signals score zero. Results are reported per signal and per available day.
- Entry delays of 0, 1, 3 and 5 minutes. **Any signal whose sign flips at 3 minutes is rejected.**
- **Option P&L** uses the business-time pricing model. It is labelled "modelled" until the recorded-day replay validates it (median premium-change error ≤ 15%). If that check fails, outcomes are translated through recorded deltas instead.
- **Spreads:** time-of-day half-spread multipliers until the depth logger replaces them:
  - ×2 before 09:30 and after 14:45
  - ×1.5 for 09:30–10:00
- **Rules applied as they were on each historical date:**
  - lot sizes
  - STT rates
  - expiry weekdays (Thursday → Tuesday in Sep 2025)
  - closing auction from 3 Aug 2026
- **Report splits** at June 2024, 20 Nov 2024, 1 Sep 2025 and 3 Aug 2026.
- **Costs** come from a unit-tested cost model (brokerage ₹20 per order, STT, exchange charges, SEBI fee, GST, stamp duty) plus the spread and slippage table.

### 6.3 Validation protocol (pre-registered)

**Records:**
- `research/hypotheses.yaml` lists each hypothesis, its fixed parameters and its pass gates **before** any outcome is seen.
- `research/experiments.csv` records every run: commit, data hash, parameters, metrics and the cumulative trial count.

**Zero-trial pilots run first** (they rank no P&L, so they cost no trials):
1. stop-fit, strike-picker and trigger pass rates by VIX tercile
2. maximum favourable and adverse excursion paths, with time to MFE, on 2019–22 only
3. validation of the gamma engine against realised volatility
4. the Nifty daily AR(1) and MAC(5) estimate
5. OI walls against settlement
6. the option-depth and latency logs
7. **Volatility forecaster comparison** (decided 21 Oct 2026). Does a pretrained time-series model forecast Nifty/Sensex volatility better than our HAR-IV-ON?
   - **Candidates, zero-shot:**
     - Kronos-mini and Kronos-small (MIT licence)
     - IBM Tiny Time Mixer (TTM)
     - the equal-weight average of HAR-IV-ON and the best of these
   - **Targets:** the same ones HAR-IV-ON forecasts. These are next-day realized variance, and the remaining-session move at each 15-minute check time.
   - **Window:** only data after each model's public release; Kronos from 1 Sep 2025. Earlier data may have been in its training set (its corpus dates are unpublished, and its 45 exchanges probably include NSE). The window grows as recorded sessions accumulate.
   - **Scoring:** QLIKE loss (MSE as a secondary check), pooled across Nifty and Sensex. Diebold–Mariano test against HAR-IV-ON with HAC errors, at 5%.
   - **Decision rule, fixed before any run:**
     - A candidate replaces HAR-IV-ON only if its QLIKE is lower and the test rejects at 5%.
     - Otherwise HAR-IV-ON stays.
     - The choice is made before trial B0 and then frozen.
   - **Stage 2, fine-tuning on Indian data.** Runs only if stage 1's best candidate is better than HAR-IV-ON or within 5% of its QLIKE.
     - One recipe, fixed in advance; no hyperparameter search.
     - Annual vintages, each trained only on data up to the end of the year before it is used. A model trained on 2019–2025 has seen those years' answers, so it cannot score them in the backtest.
     - Same decision rule as stage 1.
   - **If a pretrained model is adopted:** backtest periods before its release are reported as "forecaster may have seen this data", in the same way 2026 is reported as touched (D4). The clean forward holdout stays the deciding test.
   - **Expected result:** keep HAR-IV-ON, or use the average. Published gains over log-HAR are narrow, and about 280 sessions may not be enough to detect them.
8. **Headline tone classifier check** (decided 21 Oct 2026). Which model reads Indian market headlines best, for the shock gate (§6.1, gate 1) and the desk?
   - **Test set:**
     - The owner hand-labels about 300 headlines sampled from the news collector, across all feeds and without price restatements.
     - Two labels each: tone (negative, neutral, positive) and whether it is market-moving.
     - Labelled blind, before any model output is seen.
   - **Candidates:**
     - FinBERT-tone
     - a FinBERT model fine-tuned on Indian news (for example `kdave/FineTuned_Finbert`; check its licence)
     - a Groq model, zero-shot
     - a keyword baseline
   - **Scoring:** macro-F1 on tone, plus recall on market-moving negative headlines. That recall is what the gate needs.
   - **Decision rule:**
     - Pick the highest macro-F1.
     - A local model is preferred to Groq when it is within 0.03, because it gives the same answer on every run, so recorded days replay exactly.
     - If no candidate reaches macro-F1 0.70, the gate stays keyword-based and the classifier output is only displayed.
   - **Never a direction signal.** Sentiment stays a veto (§5A.3).

**Registry: hard cap of 13 cumulative trials**, including 2 reserve (D5):

| Order | ID | Configuration | Run condition |
|---|---|---|---|
| 1 | B0 | H1 with the a priori timing and order rules, fixed-target exits (X0), flat margin breakeven + 0.04, Platt-calibrated equal-weight family consensus | Always |
| 2 | X1 | B0 with E-trail exits | Always |
| 3 | M1 | Exit winner + pooled ridge logistic meta-model (≤ 9 columns, side dummy, HAR percentile) | Always |
| 4 | RV-2 | M1 + shock hurdle | Always |
| 5 | RV-1 | + stress-score hurdle | Always; keeps or removes the stress element |
| 6 | RV-3 | + slow-trend hurdle | If H1 passes on B0 or X1 and ≥ 4 slots remain |
| 7 | RV-4 | + gamma hurdle | Only if the gamma engine passes its own validation |
| 8 | ROD | 14:45 rest-of-day momentum, one pre-fixed gamma sign convention, research only | Only if the gamma engine passes |
| 9 | RV-5 | RV-2 + RV-3 + RV-4 combined, Δ ≤ 0.08 | Only if at least two of them are accepted |
| 10 | CTX | One reversal-context feature added to M1 | Only if the MAC(5) pilot is significantly negative after 2015 and ≥ 3 slots remain |
| 11 | X2 | VWAP-runner exit | Only if the owner opts in |
| — | Reserve | Forced re-runs, e.g. after a failed pricing check | As needed, ≤ 13 in total |

**Not run as trials:**
- payoff-shape grids
- the H2 pullback
- gradient boosting (deferred until about 300 live labelled setups)
- extra gamma sign conventions
- band-width, check-grid or cutoff variants
- equity-curve switches
- any grid over trail, target or time-stop parameters

**Splits:**
1. Combinatorial purged cross-validation on 2019–2023 (10 half-year groups, 2 test groups, 5-day embargo).
2. Frozen walk-forward on 2024–2025.
3. **2026, reported as "touched" (D4).** This research already examined 2023–2026 descriptively, so 2026 is no longer a clean holdout. A 2026 failure still counts. A 2026 pass is not treated as confirmation.

**Clean forward holdout (D4).** The first ~150 labelled setups after rules freeze form the clean test. Scaling beyond one lot waits for it.

**Pass gates:**
- out-of-sample t ≥ 2 on net returns
- ≥ 30 trades per fold
- positive after costs
- consistent sign across years
- permutation test
- deflated Sharpe ≥ 0.95
- probability of backtest overfitting ≤ 0.2
- survives the 3-minute delay test
- **Post-publication rule:** a trigger whose edge after June 2024 is under half its earlier edge is demoted.
- **Regime add-ons** must also:
  - not lower net P&L per available day
  - raise per-trade expectancy with t ≥ 1
  - improve in at least 4 of 6 out-of-sample years with ≥ 30 trades per fold

**D2 checkpoint (stop geometry).** If the pilots show fewer than about 60 eligible setups a year, or a high-VIX stop-fit pass rate under half the low-VIX rate, the owner chooses before go-live between:
- raising capital to ₹15,000 with a ₹600 stop (still 4%)
- alert-off

**Expected outcome:** if nothing passes, the system ships in alert-off (research) mode, with the desk and the recorders still running.

## 7. SP3: live engine, dashboard, journal (design constraints for its own design pass)

- **Tech:** FastAPI backend, a single clean page (plain HTML/JS with TradingView Lightweight Charts) and WebSocket updates. Bound to 127.0.0.1 only.
- **Today tab:**
  - status bar: session, data freshness, trades left (day, week, yearly trade-day budget), P&L, locks
  - day card with the technical and macro readings in plain words
  - Nifty and Sensex charts (1, 5, 15 and 60-minute and daily) with bands, VWAP, EMAs, swing structure, levels, value area, and RSI/MACD panes
  - a macro panel:
    - Brent, USD/INR, US and India 10-year, US futures, Asian markets
    - FII/DII flows and FII futures long ratio
    - stress score, event gate, and the monetary and valuation regime labels
  - an **analyst-desk panel** (section 7A):
    - the evening brief and morning update
    - bull, bear and risk cases
    - caution flags
    - the desk's running forward-test record, with a "commentary only" label
  - "setup forming" pre-alert and alert card:
    - 5-minute lapse
    - "took it / skipped" buttons and a fill box
    - the chart and macro reasons for and against, plus any desk caution flag
  - open-position tracker showing the live trail level and the next backstop ratchet
  - sound and a browser notification on each alert
- **Journal tab:**
  - paper and real trades
  - equity curve
  - **mean net R per trade** with its confidence band against the simulation's expected band
  - average win ÷ average loss, and win rate (shown, not targeted)
  - predicted vs observed probability on all labelled setups
  - how often the owner followed the system
  - the premium-turnover ledger against ₹10 lakh a year
- **Research tab:**
  - backtest reports
  - the experiment registry
  - recorder, news and macro health
  - **replay mode:** any recorded day re-run, showing what the system would have alerted against what actually happened
- **Paper trading:** every alert becomes a paper trade, filled at the live ask + 1 tick and exited at the live bid.
- **Rollout (simulation-first, as the owner prefers):**
  1. The historical simulation passes its gates (section 6.3).
  2. Recorded-day replay validates the pricing model, using 2–4 weeks of recorded data.
  3. Paper trading for **1–2 months with rules frozen** (decision of 18 Oct). Mechanics and cost only. It passes when there are no unresolved defects and measured costs are at most 20% above the assumption.
  4. Live trading with 1 lot.
- **Live monitoring and kill-switches** (whichever fires first):
  - the SPRT stop line, on **mean net R per trade**, with boundaries recomputed from measured costs
  - a CUSUM alarm on mean net R. In-control level = validated − 0.5 × (validated − breakeven). Thresholds calibrated by bootstrap with regime clustering.
  - capital ≤ ₹7,000
  - live costs more than 30% above assumption
  - **monthly calibration check** on all labelled setups
- **Locks:**
  - The daily, weekly, frequency and yearly trade-day caps from section 2. Unlocking needs a typed reason, which is saved to the journal.
  - **No automatic loss-streak pauses (D6).** The owner can invoke a logged **"shadow pause"**: alerts continue as paper trades until the end of the week.
- **Scaling:**
  - Stay at 1 lot until all of these hold:
    - capital ≥ ₹20,000
    - ≥ 100 live trades
    - an SPRT "GO"
    - a pass on the clean forward holdout (D4)
  - After that, lots = floor(capital / ₹10,000), with risk per trade ≤ 4% of capital.
  - Drop one stage on a 20% drawdown from peak.

## 7A. SP4: analyst desk (Groq LLM, explanation-only)

### 7A.1 Role and limits (D7)

- **Purpose:** a TradingAgents-style desk that writes a daily Indian-market brief, with:
  - technical, macro, options-flow and news analyst views
  - a bull case and a bear case
  - a risk manager's view
  - a judge's summary: bias, confidence, expected range and caution flags
- **No vote in trades.** The desk cannot change any alert. Its caution flags are displayed and logged.
- **Possible later role:** after about 150–300 shadow-scored days, one registry trial may test whether its caution flags predict losing alerts. Only then could a flag become a veto.
- **Why:**
  - LLM agents have no verified out-of-sample record. TradingAgents' published Sharpe of 5.6–8.2 comes from one 3-month rally.
  - Their outputs vary from run to run.
  - They may remember historical prices, so they cannot be honestly backtested.

### 7A.2 Provider and models

- **Groq free tier**, key `GROQ_API_KEY` in `.env`. The owner creates the key.
- **Quick tier:** `qwen/qwen3.8-27b`, for the analysts, bull, bear and trader roles.
- **Deep tier:** `openai/gpt-oss-120b`, for the judge and risk roles.
- The two tiers use separate per-model limit pools.
- **Free limits per model:** 30 requests/minute, 1,000/day, 8K tokens/minute, 200K tokens/day. 131k context. Tool calls and JSON supported.
- **Pinning.** The same models stay in use for the whole scoring year. A model change starts a new scoring series.
- **Fallback.** Local Ollama (Qwen3 4B/8B on the RTX 3050 4 GB) when Groq is unavailable. Fallback days are tagged and excluded from scoring.

### 7A.3 Phase 0 pilot (week 1 after SP1), then choose the path

**Setup:**
- Install TradingAgents v0.7.0 from its release wheel into a **separate venv `.venv-desk`**. Its pandas and langchain version pins differ from the main project.
- Config:
  - `llm_provider="groq"`, with the two models above
  - `selected_analysts=["market","news"]`
  - `max_debate_rounds=1`, `max_risk_discuss_rounds=1`
  - `max_tokens` about 1,500, `max_tool_rounds` about 4
  - India-specific `global_news_queries`
- A client-side token-bucket limiter at ≤ 7K tokens/minute per model, with requests serialised.

**Run:** `^NSEI` once a day for 5–10 sessions, with `cli/stats_handler.StatsCallbackHandler` attached. Record:
- calls
- tokens in and out
- the largest single request
- 413/429 errors
- wall time

**Decision rule:**
- **Path A** if:
  - ≥ 90% of runs complete
  - no request exceeds the per-minute limit
  - daily tokens stay ≤ 150K per model
- **Path B** otherwise.

The pilot's own calls are logged but not scored.

**Path A, adapted TradingAgents** (`quantdesk/desk/ta_adapter.py`):
- Register our data at runtime through `tradingagents.dataflows.router.VENDOR_METHODS` and `tool_vendors`:
  - the India news collector for news
  - the macro engine summary for macro indicators
  - the technical engine summary for indicators
- Reuse the `fundamentals` analyst slot as a **Macro & Options-flow analyst**, fed from our engines and Angel One chain statistics.
- Pin the version.
- A smoke test fails loudly if an upgrade breaks the monkeypatches.
- Its 5-tier rating is mapped to bias up/down/neutral.

**Path B, compact desk** (`quantdesk/desk/compact.py`):
- The same roles: Technical, Macro, Options-flow, News, Bull, Bear, Risk manager, Judge.
- Each prompt ≤ 5K tokens, built only from our computed numbers and timestamped headlines.
- Pydantic JSON outputs.
- About 8 calls a day, roughly 40–60K tokens a day.
- Prompts borrow TradingAgents' role design, credited under its Apache-2.0 licence.

### 7A.4 Schedule

- **Evening full run** after 19:00, once EOD data, the macro pull and the next day's events are in. No rush, and spreading calls keeps within the per-minute limits.
- **Morning update** at 08:40: 2–3 short calls using the overnight US close, ES/NQ futures, Asian markets and overnight headlines.
- One combined "Indian market" brief, plus a Nifty note on Tuesdays and a Sensex note on Thursdays. The two indices move about 98% together.
- The desk never blocks or delays the trading engine.

### 7A.5 Output, checks and scoring

**Output** (`desk_calls` table plus a JSON file per day):
- date and run type (evening or morning)
- model IDs and versions
- path (A or B)
- bias (up / down / neutral) and confidence (0–1)
- expected range vs VIX-implied
- caution flags (list with reasons)
- bull case, bear case, risk notes
- input-data hash
- token usage

**Number-faithfulness checker.** Every number in the brief must match a value in the input bundle within tolerance. A brief that fails is shown as "unverified" and excluded from scoring.

**Forward scoring** (our own; TradingAgents' built-in backtest scores `^NSEI` against SPY and is not used):
- bias vs the open→close sign
- confidence calibration (Brier score)
- expected range vs actual range
- outcomes of the system's shadow and live alerts on flagged vs unflagged days

**Power:** about 100 sessions give only about 1.6 SE between 58% and 50% accuracy. The first verdict is due at about 250 sessions.

### 7A.6 Privacy, failures, tests

**Privacy:**
- Only public market data and our computed numbers go to Groq.
- Never credentials, account data or positions.
- `.env` is never committed.

**Failures:**
- 429: back off and retry within the minute window.
- 413 or request too large: shrink the input bundle and retry once, then log "skipped".
- Groq down: Ollama fallback, tagged.

**Tests:**
- the token-budget limiter
- Pydantic schema validation
- the number checker with planted errors
- the Path A adapter smoke test
- a dry run on recorded inputs with a mocked LLM

## 8. Cross-cutting tests

- **Parity test:** a recorded day replayed through the live engine must produce exactly the same alerts as the backtester.
- **Leakage tests:** every feature computed with data truncated at time t must equal the same feature computed from the full data. Random-entry and shuffled-signal placebos must show no edge.
- **Cost model** checked against worked examples (about ₹56–58 fixed per round trip at Angel One for the reference trades in the research notes).
- **Pricing model** checked against known Black-76 values and against recorded chains.

## 9. Open items to settle during implementation

1. ~~Can Angel One serve expired futures 1-minute candles?~~ **Settled 2026-10-21: no.**
   - The Nifty Sep-2026 future (token 68407, from NSE's bhavcopy) returned 0 candles.
   - Control: the still-trading Oct future (token 48704, identical in NSE's file and Angel's master) returned 376 candles for the same day.
   - So historical futures VWAP (2019–2026) cannot come from Angel One. Choosing the VWAP source for the backtest is an SP2 design-pass decision.
   - F&O trades through the 15:15 closing auction: futures have bars to 15:30, while the index pauses.
2. Angel One's websocket token limit per connection and the OI update frequency.
3. ~~The current Sensex lot size and tick sizes.~~ **Settled 2026-10-20** from Angel One's live instrument master:
   - Sensex lot 20, Nifty lot 65.
   - Option tick ₹0.05 on both.
   - Strike steps 100 and 50.
   - Index tokens 99926000 / 99919000 / 99926017 confirmed.
   - The master also shows the Nifty weekly of 10 Nov 2026 shifted to Monday 9 Nov (holiday). This confirms expiries must come from the master.
4. The India VIX expiry rule, needed for business-time scaling.
5. A cheap source of historical expired-option 1-minute data, only if the pricing check fails.
6. Whether Angel One supports index-triggered or trailing orders on options. If not, trail ratchets stay manual, and backtests model a 1–2 minute exit latency.
7. The desk pilot's outcome (Path A or B).
8. Whether Groq accepts forced `tool_choice` on gpt-oss and qwen.
9. Whether `max_tokens` counts against Groq's per-minute limit.
10. A clean OpenBB lean install on Windows with Python 3.11. That combination is supported but not CI-tested.
11. The pretraining date range of Kronos and TTM, and whether it includes NSE/BSE data. This decides how much of the backtest pilot 7 must label as possibly seen.

## 10. Risks

- **No edge.** The most likely outcome for any single hypothesis, and the raw breakout edge has been near zero since Sep 2025. Handled by pre-registration and alert-off mode.
- **Stop geometry.** The ₹400 stop (about 0.08% of the index) sits inside the typical 0.21% adverse move, so setups may be rare and concentrated on calm days. Handled by the D2 checkpoint.
- **Pricing-model error** inflates backtest results. Handled by the recorded-day validation.
- **Regime change** (2026 war/rates regime, rule changes such as a possible SEBI settlement change). Handled by the clean forward holdout, CUSUM and dates in config.
- **Owner discipline.** Handled by locks, the journal, alert lapse, broker-side backstop orders and the shadow-pause option.
- **LLM persuasion.** Fluent desk prose could pull the owner away from the numbers. Handled by the "commentary only" label, number checking and forward scoring.
- **Free-tier changes.** Groq or Yahoo limits could change without notice. Handled by limiters, health reports and the Ollama fallback.
