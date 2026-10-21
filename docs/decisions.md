# Decision log

## 2026-10-19: Analyst desk on Groq free tier, explanation-only, pilot first

**Owner's choice:** Groq free tier as the LLM provider. Paid models only after the system shows profit.

**What matters:**
- Free limits per model are 8K tokens/minute and 200K tokens/day. Stock TradingAgents prompts are about 7K tokens each, so a full run may be rejected.
- A model switch resets the forward-test record.

**Decisions:**
- **D7, explanation-only.** The desk writes briefs, bull/bear/risk cases and caution flags, but has no trade vote. Reason: LLM agents can't be honestly backtested (memorisation, non-determinism), and TradingAgents' published results come from one 3-month rally. After 150–300 scored days, one registry trial may test its caution flags as a veto.
- **Pilot first.** Week 1 after SP1: run trimmed TradingAgents v0.7.0 on Groq (quick tier `qwen/qwen3.8-27b`, deep tier `openai/gpt-oss-120b`) for 5–10 sessions.
  - **Path A (adapt TradingAgents)** if ≥90% of runs complete, no request exceeds the per-minute limit, and daily tokens stay ≤150K per model.
  - **Path B (compact desk with the same roles, prompts ≤5K tokens)** otherwise.
- **Pinning.** Keep the same models for the scoring year. Ollama fallback days are tagged and not scored.
- **Scoring.** Forward-only. The first verdict comes at about 250 sessions; at about 100 sessions the test reaches only about 1.6 SE.

**Can't be known yet:** real token use on Groq, and whether Groq accepts forced tool calls. The pilot measures both.

## 2026-10-19: OpenBB lean install as the global/macro data layer

**Decision:**
- Install only the free providers needed (`openbb-core`, `-fred`, `-federal-reserve`, `-oecd`, `-imf`, `-nasdaq`, `-ecb`, `-mcp-server`).
- Keep the plain `yfinance` library for prices.
- Do not use the AGPL `openbb-yfinance` add-on.

**Why:**
- OpenBB v5 removed yfinance, FMP and EconDB from the core.
- The full meta-package is heavy.
- It has no NSE/BSE options and no Indian news feeds, so Angel One and our own RSS collector remain the sources for those.

**Repository check:** `OpenBB-finance/OpenBB` redirects to `openbq-org/OpenBB` (same GitHub repo ID), so the owner's link is the official repo.

## 2026-10-19: Timing-report decisions D1–D6 accepted as defaults

Source: `reports/Nifty options strategy timing refinement.md`, section "Six decisions only the owner can make". The owner accepted the recommendations.

- **D1, exits.**
  - E-trail is the default: after +1b in favour, trail at 1.5b with stop = max(trail, VWAP); no breakeven move; laggard time stops at 30/60 minutes.
  - The 50% win-rate goal is retired, and the scoreboard is mean net R per trade.
  - **Why:** E-trail beat fixed targets in all 21 modelled cells, by about ₹10–85 a trade at ₹400 scale.
  - **Would change if:** the excursion pilot shows the system's setups peak within about 30 minutes and then revert.
- **D2, stop geometry.**
  - Keep ₹400 for the simulation.
  - If fewer than about 60 eligible setups a year, or the high-VIX pass rate is under half the low-VIX rate, choose between ₹15k/₹600 and alert-off before go-live.
- **D3, frequency.** ≤100 live trade-days a year spread pro-rata by month, ≤3 a week as a hard ceiling, and a premium-turnover ledger aiming for under ₹10 lakh a year.
  - **Why:** SEBI data ties high frequency and turnover relative to capital to 94–98% loss rates.
  - **Cost:** the live verdict takes about 12 months instead of about 8.
- **D4, holdout.**
  - 2026 is reported as "touched", because the timing research examined 2023–2026 descriptively.
  - Go live on the agreed timeline, but scale beyond 1 lot only after a clean forward holdout of about 150 labelled setups.
- **D5, trial budget.** A registry of 6 core trials (B0, X1, M1, RV-2, RV-1, RV-3) plus up to 5 conditional ones, hard cap 13 including reserves.
  - **Why:** the deflated Sharpe falls from 0.947 at 10 trials to 0.869 at 30.
- **D6, pauses.** No automatic loss-streak pauses: on Nifty, P&L-based filters skipped the better trades (t = −2.34). The owner may invoke a logged "shadow pause" (paper-only until the end of the week).

**Correction.** The 18 Oct entry below said "2–4 week paper check". The agreed paper phase is **1–2 months with rules frozen**, as the first 18 Oct entry records.

## 2026-10-18: Paper trade 1–2 months with frozen rules; tune only in simulation

**Owner's request:** paper trade 1–2 months and improve the system until the win rate crosses 50%.

**Concern raised:**
- 1–2 months gives about 8–20 alerts. With 16 trades, the observed win rate varies by about ±12 points from luck alone.
- A true 40% system shows 50% or more about 1 time in 4.
- Tuning until paper shows 50% would fit noise.
- At a 2:1 payoff, breakeven is 40%, so the scoreboard is net profit per trade, not win rate.

**Decision (confirmed in substance by the owner's acceptance of the full design on 19 Oct):**
- All rule changes are made and evaluated in the 2019–2026 simulation, within the trial budget.
- Paper trading runs 1–2 months with rules frozen.
- Go live only if the simulation passes its gates *and* paper results are not clearly worse than the simulated range.
- If the simulation result is borderline, extend paper trading towards about 100 alerts.

## 2026-10-18: Validation is simulation-first, with a short paper phase

**Decision.** The edge verdict comes from a historical simulation (2019–2026) run under pre-registered gates. After that comes only a 2–4 week paper check of mechanics and costs, then live trading with 1 lot.

**Why.** The owner did not want to wait months. The research shows that distinguishing a 46% win rate from 40% with live trades alone needs about 100 trades, which at about 8 trades a month is about a year.

**Trade-off we accept.** Live trading starts before live results can confirm the simulation.
- The kill-switches (SPRT, CUSUM, ₹7,000 capital floor) can catch a clearly broken system.
- They cannot prove a good one quickly.

**Mitigation.** Every alert is paper-tracked whether it is taken or not, and skipped setups are labelled too. This builds evidence faster at no cost.

**Expectations recorded at decision time.** These are guesses, not measurements:
- About 50–60% chance the simulation finds no cost-surviving edge. In that case the system stays alert-off.
- About 30–40% chance of a 42–46% win rate, i.e. roughly +₹200–600 a month on ₹10k with 8 trades a month.
- About 5–10% chance of 50% or better.
- Breakeven is 40% at ₹400 risk, ₹800 target and about ₹80 all-in cost per trade.

## 2026-10-07: Capital ₹10,000, risk ₹400 per trade, target ≥1.5× net

**Why.** At ₹5,000, a ₹400–500 risk per trade was 8–10% of capital, above Kelly at plausible edges. At ₹10,000, ₹400 is 4%.

## 2026-10-20: SP1 data foundation built; live smoke run waits for Angel One credentials

**Built:** 17 of 18 plan tasks, with 99 offline tests. A first live run without broker credentials worked:
- NSE holiday API
- all 9 news feeds (516 items)
- Federal Reserve, OECD and Nasdaq calendar via OpenBB
- yfinance
- Angel One's public instrument master (lot sizes, ticks and index tokens verified)

**Still open (needs the owner):**
- `.env` with Angel One SmartAPI credentials
- the live smoke tests (`pytest -m live`)
- one full recorded session on a trading day
- websocket token limit and expired-futures checks (spec §9 items 1–2)
- FBIL G-sec and NSE index P/E URLs (series show `failed` until configured)

**Notes:**
- 20 Oct 2026 was a market holiday (Dussehra).
- GDELT's newest GKG file returned 404 during the run; the collector reports it and continues.

## 2026-10-20: SP1 final review — fixes, rulings, deferred items

A fresh whole-branch review found 1 critical and 8 important issues. All are fixed, each with a test that failed first, and the suite is 124 passed (5 live tests deselected). Two minors were promoted and fixed: atomic Parquet writes, and positive checks on downloaded files.

**Critical fix:** the Angel One SDK printed and wrote the PIN, API key and JWT on failed requests. Its logging is now silenced and its log file closed, and `logs/` is git-ignored.

**Rulings (with what they cost if wrong):**
- The recorder starts at 09:10 and plans strikes from the previous close; recentring fixes the chain after the open. *Cost:* on a big gap, the first minutes cover shifted strikes.
- If one index's start-up price call fails, that index's options are skipped for the day; the error is printed and saved. The live test `test_live_index_ltp_used_at_recorder_start` checks both symbols first. *Cost:* one index's options lost on such a day.
- Minutes flush on exchange time; late ticks are dropped and counted. *Cost:* a few late ticks missing from a bar's close.
- The websocket token limit (1000) and the `last_traded_timestamp` unit are guesses until the first live session.
- Special sessions (Budget Sunday, Muhurat) are not recorded. *Cost:* 1–2 short sessions a year.
- Survivorship bias from today's Nifty 50 list in the 2019 backfill is left to the SP2 design.

**Deferred minor items (backlog):**
1. Holiday check runs after the master and constituents downloads; a failed constituents fetch blocks option recording.
2. Run lock: a reused stale PID blocks recording; switch to `msvcrt.locking`.
3. Health report never shows the master-fallback flag.
4. A frozen feed on an open socket is only logged, not reconnected.
5. First bar per token undercounts volume.
6. GDELT rows are tripled by 5-minute polling.
7. EOD: errors are not retried hourly; `vix_daily` duplicates on re-run; no holiday check; bhavcopy backfill aborts on one network error.
8. The option token-to-contract map is not saved daily (NSE reuses tokens).
9. News loop: no exception guard or single-instance guard; runbook's 12-hour stop.
10. `manifest.jsonl` lives in `data/raw`; move it to `data/state`.
11. Session-expiry errors (HTTP 403, camelCase `errorCode`) may not trigger relogin — verify live.
12. `_subscribed` is shared across threads without a lock.
13. `last_traded_timestamp` fallback assumes milliseconds.
14. `recenter` does not re-check the token budget.

## 2026-10-21: Open-source finance models, measured as pilots, never as a direction signal

**Decision.** Spec §6.3 gains two zero-trial pilots:
- **Pilot 7:** pretrained volatility models (Kronos-mini/small, IBM TTM, and their average with HAR) against HAR-IV-ON. Tested zero-shot, only on data after each model's release.
- **Pilot 8:** a headline tone classifier (FinBERT-tone, an Indian FinBERT fine-tune, Groq, keywords). Tested on about 300 headlines the owner labels blind.

Both have their decision rules fixed in the spec before any run. Neither looks at P&L, so neither uses up any of the 13 trials. No pretrained model is used to pick the trade direction. A fine-tuned Kronos is not used as the desk's model either.

**Why.**
- **Direction.** A 2026 benchmark found pretrained models beat a random walk on stock returns with significance in only 2 of 10 cases. A direction signal would use up a trial on the least likely idea.
- **Volatility.** A 2026 study of 9 models on 50 assets found only IBM's TTM beat log-HAR at every horizon, and narrowly. Kronos reports 9% lower volatility error, zero-shot.
- **Headline tone.** The shock gate needs some tone classifier anyway. A local model gives the same answer every time, so recorded days replay exactly.

**Why not fine-tune on Indian data straight away.** Compute is not the blocker: Kronos-small (24.7M parameters) can be fine-tuned on the owner's 4 GB GPU.
- **The evidence for a gain is thin and mixed.** A Nov 2025 study found ready-made models stayed poor on financial data even after fine-tuning.
- **Honest use is expensive.** A model fine-tuned on 2019–2025 Nifty has seen those years' answers, so it cannot score them in the backtest. It would have to be retrained once per year on past data only, with no tuning on test data.
- **So fine-tuning is stage 2 of pilot 7.** It runs only if the zero-shot result comes within 5% of HAR or beats it.

**Expected outcome.** Pilot 7 most likely ends with "keep HAR, or use the HAR + TTM average". About 280 sessions since Sep 2025 may not detect a narrow gain. This is a guess; the pilot measures the noise.

**Open.** Kronos's and TTM's training date ranges are unpublished (spec §9 item 11).

## 2026-10-21: First live run; the closing auction changes the index minute count

**Live results (owner's credentials, 11:44 IST).** Each of these worked:
- `login-check` logged in.
- The instrument master returned the expected tokens and lot sizes.
- The start-up price lookups for Nifty, Sensex and VIX returned prices.
- The live feed delivered ticks at the right price scale.
- The regular Trading API key also returned 1-minute historical candles, so no separate historical-data key is needed.

The first recording started at 11:45, so the day is partial.

**Finding.** The candles for Mon 19 Oct 2026 had 361 Nifty bars, not 375. They run 09:15–15:14 without a gap, followed by a single 15:29 bar with open = high = low = close. This matches the closing auction that started on 3 Aug 2026: during it the index is not computed, and only the close is published.

**Decision.**
- The health report now counts index minutes only in the continuous session. From 3 Aug 2026 that is 09:15–15:14 (360 minutes); before that it is the full 375.
- The rule lives in `settings.yaml` as `session.closing_auction` and in `continuous_session()` in `calendar/events.py`, so SP2's market-rules-by-date table can reuse it.
- The live candle test now checks Nifty, Sensex and VIX against the same rule.
- Without this change, the report would have flagged "14 minutes missing" every day, and real gaps would get lost in that noise.

**Still to observe.** Do Sensex and VIX also stop during the auction? The 3-index live test will show it. Does the live feed send index ticks during 15:15–15:29? Today's recording will show it.

## 2026-10-21: Historical-data limit is 120 per minute, and plain-text refusals are retried

**Finding.** In the second live run, Angel One refused 2 of 3 candle requests with the plain-text reply "Access denied because of exceeding access rate". The Angel One library turns that reply into a `DataException`. Our retry only recognised Angel's JSON error format, so the requests failed straight away instead of waiting and trying again. Angel One's RateLimit page now gives `getCandleData` as **3 per second, 120 per minute and 5000 per hour**, counted per client code across every program using the account. Our limiter assumed 180 per minute.

**Decision.**
- The limiter is set to 3 per second, 120 per minute and 5000 per hour; it allows one fewer call than each limit.
- Any error that says "exceeding access rate" is retried with backoff.
- The spec's figure is corrected.

**Why it matters.** The history backfill sends calls back to back for hours. At 180 per minute it would have hit the limit every minute and logged failed chunks.
