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

**Follow-up, same day.** In the third live run the Nifty candle request was refused for more than 15 s. The final refusal came back as JSON, `AB1021: Too many requests`, which wasn't on the retry list.
- `AB1021` and the message "too many requests" are now retried.
- Rate refusals are now retried for just over a minute (waits of 1, 2, 4, 8, 16 and 32 s), so a per-minute block can clear.
- Sensex and VIX candles passed the continuous-session check (09:15–15:14 present).

## 2026-10-21: SP1 verified live

- All 7 live tests pass (12:2x IST):
  - login
  - the instrument master
  - the start-up price lookups for all three indices
  - 1-minute candles for Nifty, Sensex and VIX, complete for 09:15–15:14
  - the live feed's price scale
- **First recorded session.** It recorded 11:45–11:59, then from 12:10 to the close. The gap is from a closed terminal. One websocket connection carried 303 subscriptions, so spec §9 item 2's per-connection limit is at least 303.
- **History backfill.** Started at 12:22. The first two minutes saved 18 Nifty chunks, all ok. At that pace the whole job takes about 10 hours, and it resumes where it stopped.
- **Still open from Phase 1:**
  - Task Scheduler jobs
  - the first full-day health report
  - expired-futures candles (§9 item 1)
  - the FBIL and NSE P/E URLs

## 2026-10-21: SP1 backlog closed; daily jobs scheduled

- **Scheduled jobs.** `scripts/schedule_tasks.ps1` registers the six daily jobs in Windows Task Scheduler. They run hidden, write to `logs/tasks/`, never start twice, run on battery, and catch up after the PC was off. The owner asked for this ("go full and complete all").
- **Backlog.** All 14 items from the SP1 review are fixed, test-first; see the roadmap's Phase 2.
- **Live finding.** `last_traded_timestamp` is epoch *seconds*, while `exchange_timestamp` is milliseconds. The old fallback would have dated those ticks to 1970.
- **Transition note.** Today's recorder, history backfill and terminal news poller still run the code they started with. The terminal poller holds no lock, so it must be stopped before tomorrow's 06:55 scheduled job.

## 2026-10-21: NSE F&O bhavcopy before July 2024 comes from the old archive

**Finding (live).** NSE serves the UDiFF F&O bhavcopy only from about July 2024. Earlier days return 404 at the UDiFF address, but they exist in the old layout at `content/historical/DERIVATIVES/YYYY/MON/foDDMONYYYYbhav.csv.zip`, which was checked for 2019, 2023 and 5 Jul 2024. Turnover ÷ (price × volume) equals the lot size in both layouts, so volume is in contracts in both.

**Decision.**
- Days before 8 Jul 2024 try the old archive first and fall back to UDiFF on a 404.
- Both layouts parse to the same columns. Instrument codes are mapped to UDiFF (`FUTIDX→IDF`, `OPTIDX→IDO`, `FUTSTK→STF`, `OPTSTK→STO`), futures get a blank strike and option type, and `underlying` is empty for old-layout days.
- BSE files before UDiFF are not covered. Sensex weekly options restarted only in May 2023.

**Consequence.** The bhavcopy backfill started at 12:29 runs the old code. It will mark 2019 to mid-2024 as `not_published` and only save files from July 2024 onward. Re-running `backfill --what bhavcopy` with the new code fills the missing years and skips files already saved.

## 2026-10-21: Expired futures have no 1-minute candles at Angel One (spec §9 item 1)

The Nifty September 2026 future (expired 29 Sep) returned 0 candles for 25 Sep. The October future, whose token is identical in NSE's bhavcopy and Angel's master, returned 376 candles for the same day. So 1-minute futures history exists only while a contract trades: the backfill's current-future window, plus our own recordings from now on.

**Open for the SP2 design pass: where historical VWAP comes from.** Candidates:
- (a) a volume-weighted proxy built from the 50 constituents' 1-minute bars, which the history backfill is downloading
- (b) running the H1 backtest only where futures 1-minute data exists, which is short
- (c) an index-only VWAP substitute, such as a time-weighted average, with its limits stated

Each changes what the backtest can claim, so this needs the owner's decision.

## 2026-10-21: India 10-year and Nifty P/E come from NSE's daily index file; stored dates fixed

- **Nifty P/E.** `nifty_fundamentals` gives Nifty 50 P/E, P/B and dividend yield from NSE's public `ind_close_all_DDMMYYYY.csv`. It covers 2015 to today; before 9 Nov 2015 the index was named "CNX Nifty".
- **India 10-year.** `india_gsec10y_price` is the "Nifty 10 yr Benchmark G-Sec (Clean Price)" index from the same file.
  - FBIL's par yield was rejected. Its terms of use call back-testing and risk management commercial use, which needs a paid subscription. Its public archive also lagged by a week.
  - The SP2 macro engine will turn price changes into approximate yield changes (Δy ≈ −ΔP/P ÷ modified duration). That is enough for the stress score's 5-day change, but it gives no yield level.
- **Bug found while checking this.** `Store.read` and the DuckDB views let the folder name `date=YYYY-MM-DD` (the day rows were stored) overwrite a table's own `date` column. So every macro series read back dated by collection day. Now:
  - a table's own `date` is kept, and the folder date becomes `stored_on`
  - tables without a `date` column still get the folder date as `date`
  - the files on disk were always right
- The two series backfill with `backfill --what fundamentals`: about 2,900 files from 2015, at 1.5 s each, roughly 75 minutes.

## 2026-10-21: Desk pilot first runs; long jobs run from Task Scheduler only

**Desk pilot (SP4 phase 0).** TradingAgents v0.7.0 is installed in `.venv-desk`. `desk/run_pilot.py` runs nightly at 19:30 (`quantdesk-desk-pilot`) and stops after 10 runs with the same settings.
- **Run 1, TradingAgents defaults.** Failed. Groq rejected a News Analyst request of 8,810 input tokens with HTTP 413. The free-tier limit for `qwen/qwen3.8-27b` is **7,000 input tokens per minute**, not the 8K the spec assumed. The client limiter is now 6,500.
- **Ruling.** The spec asks for a "trimmed" TradingAgents, so the news limits were cut from 20 + 10 articles to 5 + 5. Only runs with these exact settings count toward the Path A/B rule; run 1 stays in the log as evidence that the defaults don't fit. *Cost if wrong:* a fairer trim might have let Path A pass, but every count is logged and the rule is unchanged.
- **Run 2, trimmed.** No 413 errors, and the largest request was 4,377 tokens. It ended with a connection error, because the PC went to sleep and the app restarted at the same time. The 19:30 scheduled run retries.
- Any 413 in a counted run now rules out Path A directly, and the meter reads the rejected request's size from Groq's error.

**Operations.** Jobs started inside the Claude app's terminals and shells died when the app restarted: the recorder, the history, fundamentals and bhavcopy backfills, and the terminal news poller. Only Task Scheduler jobs survived. Long jobs now run via `scripts/run_detached.ps1`, and the runbook says so. The PC must not sleep in market hours; that power setting is the owner's to change.

## 2026-10-21: Cost model and Black-76 built (SP2 building blocks)

- **`quantdesk/costs.py`** prices an Angel One round trip.
  - It reproduces all five worked examples in the research notes to the paisa.
  - Sourced charge schedules start on 1 Jan 2019, 1 Apr 2023, 1 Apr 2024, 1 Oct 2024 and 1 Apr 2026, from Zerodha's exchange bulletins and Budget 2026. Dates before 2019 raise an error.
  - Unsourced small items are noted in the code, each well under ₹1 per round trip.
  - A Nifty 65 × ₹60 → ₹74 round trip costs ₹54.77 (Jun 2020), ₹55.47 (Jun 2023), ₹55.93 (Jan 2025) and ₹57.98 (Oct 2026).
- **Open for SP2.** Should old trades be charged at their day's rates (the spec's "as they were") or today's (what the owner will pay)? Today's are higher, so they are the conservative choice.
- **`quantdesk/black76.py`** gives price, greeks and implied vol.
  - Checked against Hull's example (1.12), put-call parity, finite differences and an IV round trip.
  - On live data at 14:35, the Nifty 22700 call and put both gave 14.34% IV, with India VIX at 15.88.
  - The business-time clock is still SP2 (spec §9 item 4).

## 2026-10-21 (evening): Three data faults found after the first full day

- **Angel One caps candle replies at 8,000 and drops the oldest.**
  - A 30-day one-minute chunk with 22 trading days needs 8,250 candles, so it lost the first 250 minutes of its first day.
  - 150 of the first 1,329 chunks were cut.
  - A reply at the cap is now split in two and fetched again. Cut chunks are refetched: their manifest rows have no `pieces` field.
  - Readers already de-duplicate on (target, ts), so the overlap is harmless.
- **NSE's index files before mid-2015 write dates as 24/03/2015.** The parser now reads both forms. The first fundamentals backfill skipped those days, and `backfill --what fundamentals --start 2015-01-01 --end 2015-06-30` refetches only that gap.
- **The 13:50 sleep was a power cut.**
  - The laptop went on battery, which sleeps after 15 idle minutes. The plugged-in setting is 3 hours.
  - The recorder now holds a Windows keep-awake request while it runs (`quantdesk/power.py`), the request a video player makes, so no power setting needs changing.
  - If the router loses power in a cut, the feed still stops.
- After a fresh macro run, all 24 macro series report ok, including the NSE bond index and Nifty fundamentals.

## 2026-10-21: SP2 data conventions (owner: "go with the most reliable long-term design")

The full rules are in spec §6.0.

- **VWAP comes from the stock-volume proxy, in the backtest and live alike.**
  - Each minute's index price is weighted by the Nifty 50 stocks' traded value in that minute.
  - Why: it uses data we already download and reflects each day's real volume. Using it live too keeps the backtest and the live engine on the same number.
  - Rejected: dropping VWAP, because the D1 exit research rests on it, and paid futures history, because of the cost and the daily futures-premium adjustment.
  - A zero-trial check against real front-month futures VWAP comes before any P&L look. If it fails (sides disagree in more than 5% of minutes, or the median gap is over 0.1 × the median stop), every VWAP rule switches to the open-anchored average price, in the backtest and live.
  - *Cost if wrong:* entries and trails sit slightly off the level traders watch. The check measures how far.
- **Charges are today's for every trade, with each date's own shown beside them.**
  - Why: today's charges are what the owner will pay, and they are the higher figure, so the error can only make results look worse.
  - The difference is about ₹3 per round trip, under 1% of the ₹400 risk.
  - *Cost if wrong:* old periods look slightly worse than they were.
- **Time to expiry uses weighted business time.**
  - Minute weights come from the 1-minute Nifty history. Night, weekend and holiday weights come from bhavcopy at-the-money implied vols against India VIX. Both are fitted on 2019–2022 and then frozen.
  - The recorded chains check the clock (median premium-change error ≤ 15%), and it is refitted only if that check fails.
  - Why: calendar time misprices expiry-day options by about half, and a plain trading-minute clock ignores overnight gaps, which overprices intraday options.
  - *Cost if wrong:* modelled premiums are off. The recorded-chain check catches it before any verdict.

## 2026-10-21: SP2 design pass, rulings R1–R38 (owner: "the most reliable long-term design")

The plan was approved on 21 Oct 2026. The rulings are in spec §6.4, and every value with its source and provenance is in `research/hypotheses.yaml`.

**Departures from earlier text, each the stricter option:**
- **CPCV embargo 20 days, not 5.** The features look back 14–20 days, so 5 days would let training and test overlap.
- **Pricing check needs at least 15 recorded sessions with at least 4 expiry days per index.** Expiry days are where the clock matters most, and 10 sessions might hold only 2.
- **Earlier looks count.** The design research printed outcomes for 46 rule variants before the registry existed (`research/prior_looks.md`). DSR uses N = 46 + trials. The shock and slow-trend parameters were chosen after full-sample looks, so those add-ons also need the forward holdout.
  - *Cost:* the DSR gate becomes much harder to pass. P10 measures how much before any trial is spent.
- **Exits follow how the owner trades.** The owner sees alerts within minutes but doesn't watch charts all day. The backtest therefore uses the more conservative of an index-trail alert with a 2-minute delay and a premium SL-limit backstop.

**New, smaller rules that the spec left undefined.** Each is marked `design_ruling` in the YAML:
- the stop cap (b ≤ 0.5 × the VIX-implied daily move, from RESEARCH_REPORT L174)
- breadth as 2 of 3 signals
- the spike guard on modelled premium
- the "rich" volatility percentile
- Sensex round levels at 500
- the 0–8 stress points
- ridge λ = 10

**Scope moved to SP3:**
- pilot 8 (it only serves the live headline veto)
- OFI and depth gates
- display-only indicators
- the "setup forming" pre-alert

**What the owner sees next:** pilots P1, P2 and P10 at the D2 checkpoint, with the X2 opt-in.

## 2026-10-21: SP2 plan 1 - two data traps found building `daily` and `macro`

- **`daily` takes the day from the candle timestamp, never from a `date` column.**
  - Why: the `date` on a `history_one_day` part is the day the chunk was *stored*, not the bar's day. The
    `date=2015-01-01` part holds bars for 2015-01-02, 2015-01-05 and onward, so every row but the first
    would be misdated. `day` is `cast(timezone('Asia/Kolkata', ts) as date)` instead.
  - The table dedupes on (target, day), not (target, ts): overlapping backfill chunks store the same day
    under two folder dates, and the later file must win, as in `minutes`.
  - *Cost if wrong:* every band anchor and every HAR input shifts by up to a chunk length.
- **The macro lag table classifies all 22 stored series, including the NSE index file.**
  - Why: plan 1's lag list omitted `india_gsec10y_price` and `nifty_fundamentals`, but design section 4
    stamps the NSE index file at d 20:00 IST, and the stress score reads the India 10-year from the G-sec
    clean-price index. `available_at` raises `KeyError` on an unclassified series by design, so the omission
    would have stopped `derive` outright.
  - A test now walks `config/settings.yaml` and fails if any collected series has no lag rule.
  - *Cost if wrong:* an unlagged series reads as same-day knowledge, which is look-ahead.

## 2026-10-21: SP2 plan 1 - contract parser rulings

- **Legacy `turnover` is `VAL_INLAKH` x 1e5.**
  - Why: plan 1 defined `turnover` only for UDiFF (`TtlTrfVal`, rupees). The pre-July-2024 layout reports
    traded value in lakh rupees, so it is scaled to rupees and `options_eod` keeps one unit throughout.
- **`lot` is nullable `Int64`, never 0.**
  - Why: a legacy file whose futures row has no contracts or no settle price cannot yield a lot. That row
    stays missing instead of becoming 0, which would silently size a position at nothing. All 1,234 legacy
    NSE files in `data/raw` do yield one, and the recovered sizes are 50 and 75, so {25, 50, 75} covers
    every lot era NSE has used.
  - *Cost if wrong:* a 0 lot passes the affordability screen and then divides the stop budget by nothing.
- **R6 confirmed on stored data:** 23 NSE UDiFF days have `FininstrmActlXpryDt` different from `XpryDt`
  (Oct 2024, Dec 2024-Jan 2025, Apr/May/Oct 2025), so keying chains by the scheduled expiry would misdate
  them. `parse_fo_contracts` uses the actual expiry and falls back to the scheduled one only if it is blank.

## 2026-10-21: SP2 plan 1 - which sessions have no option chain

- **`expiries` falls back per day, not per symbol.**
  - Why: of the 1,900 sessions from 2019-02-11, exactly 7 have no NSE F&O file and the same 5 of those have
    no BSE file either, so a per-symbol fallback would recover nothing. Six of the seven are `irregular`
    weekend sessions (1 Feb 2020, 1 Feb 2025 and 1 Feb 2026 Budget sittings, 20 Jan 2024, 2 Mar 2024,
    18 May 2024): NSE keeps the derivatives segment closed for them, which is why there is no bhavcopy.
    The seventh, 2021-03-30, is the archive gap the design already documents, and the fallback covers it -
    that day reads the 26 March chain.
  - A day with no chain gets no `expiries` row, so it cannot produce a signal (R12). No day is filled from
    a stale chain whose expiries have all passed.
- **`expiries` carries `available_at` = d 09:00 IST.** Design section 5's column list omits it, but section 4
  opens "every derived row has `available_at`", and the `AsOf` reader adds `available_at <= T` to every
  table it reads. Without the column the day card could not read its own expiry calendar.
- **57% of chain rows are untraded** (measured on a 19-session sample), so the `traded` flag is not a
  formality: every surface and skew fit must filter on it.

## 2026-10-21: SP2 plan 1 - members_minute, and one interface change to plan 1

- **`member_breadth` and `build_members_minute` take `top_n`; plan 1 showed them without it.**
  - Why: plan 1's global constraint is that every number comes from `research/hypotheses.yaml` via
    `param`, and `gate.breadth_top_n` is already registered there as 5. Hard-coding 5 in the table that
    the breadth gate reads would let the two disagree. `cmd_derive` passes it, exactly as it passes
    `backtest.nifty_from` and `backtest.sensex_from`.
- **Each day's bars are read once, for every symbol that has ever been a member.**
  - Why: the top-5 weights are the previous session's traded value of *today's* members. Reading the
    previous session again with today's list would double the queries; reading the whole ever-member set
    once and letting `member_breadth` keep today's members is exact and halves the run.
- **Coverage is not ready for the real `derive` run (plan 1 task 8, owner step).** 14 former members have
    no bars anywhere yet (BPCL, BRITANNIA, GAIL, HDFC, HEROMOTOCO, INDUSINDBK, INDUSTOWER, IOC,
    SAMMAANCAP, UPL, VEDL, WIPRO, YESBANK, ZEEL), so `members_present` is 36 of 50 on 2019-06-14 and 42
    of 50 on 2023-07-12, against 50 of 50 on 2026-10-19. The table is built as designed - members are
    counted, never filled - but the VWAP proxy would be a 36-stock proxy until the history backfill runs.
- **Stray bars after the session are kept.** On auction-era days the stock candles include a few prints
    at 15:24-15:29 (98 shares across 51 stocks at 15:29 on 2026-10-19), so those minutes get a row with a
    near-zero `tv`. Nothing reads them: no entry after 14:00, hard exits at 15:00 and 15:10, and no spot
    print after 15:15 is ever used.

## 2026-10-21: SP2 plan 1 - vectorised Black-76 conventions

- **Rows with no time value are not masked by the caller.** `price`, `delta` and `theta_bt` accept
  T <= 0 or sigma <= 0 and return intrinsic value, the exercise decision (+/-1 in the money, 0 out of
  it, and 0 exactly at the money, where the limit is 1/2 either way and the option is worthless), and
  zero theta. Why: a frame of strikes spans an expiry, and the scalar model raises there, so every
  caller would need the same mask; the plan only fixed the price case.
- **`theta_bt` is d(price)/dT, positive, and `kind` does not change it.** With r = 0 put-call parity
  makes the time value identical, so the caller applies decay as -theta_bt * dBT (design section 7).
  `kind` is still taken, and still validated, so all three functions share one call shape.
- **Agreement with the scalar model is absolute, not relative.** Over 4000 random Nifty-scale rows
  (T from 1e-4 to 0.06 years, sigma 0.05-0.9, strikes +/-15%) the worst price difference is 1.1e-11
  and the worst delta difference 2.2e-16; on the 3787 rows with real time value the worst theta
  relative difference is 4.9e-16. The 1e-10 tolerance in the design is an absolute one, and deep
  out-of-the-money rows are worth under 1e-8, so a relative test would be meaningless there.

## 2026-10-21: SP2 plan 1 - HAR rulings, and one gap in the design

- **x5 uses the official open, and the 09:16 caller must not.** `har_design` reads O_t from `daily`, whose
  `available_at` is 16:00, so the design matrix is an end-of-day artefact used for fitting. A forecast made
  at 09:16 (plan 2, `DayLoader`) has to build x5 from the 09:15 bar's open instead: the same print, but
  knowable at the time. Everything else in the row is already a day old.
- **A hole in the India VIX costs exactly one HAR row, and is never filled.** `x4` is the previous session's
  VIX close reindexed onto the index's sessions; a missing day leaves the next row's x4 NaN, `fit_har` drops
  it and `har_series` reports NaN. On real data INDIAVIX has no daily candle for 2021-02-12 and 2021-03-30
  (the second is the day with no option chain either), so NIFTY and SENSEX each lose 2 of 2912 rows on top
  of the 22-session warm-up.
- **A refit needs six complete rows, so the first forecast lands in the second month of history.** `fit_har`
  raises below that (six coefficients, no unique least-squares solution), and `har_series` simply keeps
  forecasting from the previous fit or reports NaN. For NIFTY from 2015 that is 43 sessions with no
  `rv_hat`, and 103 with no `har_pct` (43 + the 60 the percentile floor needs). All of it is before
  `backtest.nifty_from` (2019-02-11).
- **Measured on real data, 2015-2026 (temp store, nothing written to data/derived).** Median sigma_day is
  0.64% of the index (5th percentile 0.44%, 95th 1.10%) against a realised 0.56%; the last fit has n = 750,
  s2 = 0.64 and beta = (-1.38, 0.16, 0.15, -0.05, 0.65, 0.01), so the VIX term carries most of the level and
  the three RV lags sum to 0.27. The exp(s2/2) correction matters: mean rv_hat / mean rv is 0.98 with it and
  0.71 without. By year the ratio stays inside 0.89-1.10 from 2016 on; 2015 is 1.6 because those fits see
  only a few dozen rows.
- **Gap: the design's `har_fits` audit table has no task in plan 1 or plan 2.** Design section 6 asks for
  beta, s2 and n per refit to be saved to a derived table. `HarFit` carries all three, but nothing writes
  them yet. It should land with plan 3 (the registry and its audit trail), or as a `derive --only har_fits`
  table if the owner wants it sooner.

## 2026-10-21: SP2 plan 1 - clock rulings

- **`bt` refuses an endpoint that is not a session rather than inventing a weight for it.** The design
  formula is written for two session days; a Saturday or a holiday has no minute weights, so any answer
  would be a guess. `sigma_bt` already rolls a non-session expiry back to the previous 15:30 (design §7),
  and every other caller decides inside a session, so raising is both safe and loud.
- **Holidays come from the session list, not from config/events.yaml.** A weekday strictly between two
  consecutive sessions is a holiday by construction, which is what the plan says and keeps the frozen clock
  independent of a hand-maintained calendar. On the real 1929 sessions the longest gap is five days
  (2021-11-03 to 2021-11-08, Diwali week: two weekend days and two holidays), and the six weekend sessions
  (2020-02-01, 2024-01-20, 2024-03-02, 2024-05-18, 2025-02-01, 2026-02-01) simply shorten the gap around them.
- **`Clock` is frozen with eq=False.** A 375-value ndarray field has no scalar ==, so the generated
  `__eq__` would raise on any comparison; identity comparison is the honest behaviour for a frozen artefact.
  The weights are validated at construction (375 values, summing to 1 within 1e-9) because a truncated YAML
  would otherwise misprice every option silently.
- **Irregular sessions still count as sessions** (design §7): 15 of the 1929 real sessions are irregular,
  including 2025-10-21 with 72 bars and 2026-07-23 with 299. They are excluded from signals and band
  windows, but time passes on them, so `bt` gives them a full unit.

## 2026-10-21: SP2 plan 1 - clock fit rulings

- **The ATM strike needs no spot input: it is the traded strike with the smallest |C - P|.** Design §7 step 1
  says "nearest to F" and step 2 says F = K + C - P, so |K - F| = |C - P|. Picking the strike that way is
  self-consistent with the forward the two implied vols are then inverted at, and keeps `atm_implied_variance`
  free of an index-level argument. Ties go to the lower strike.
- **`atm_implied_variance` gained two arguments, `dte` and `sessions`.** The plan's signature `(eod, vix_close)`
  cannot express the design's "2-6 trading days left" without either hard-coding the window or inferring the
  calendar from whatever rows happen to be in the frame, which would make the fit's meaning depend on its input
  slice. Both now arrive from outside: `clock.atm_dte` (new, [2,3,4,5,6], design §7 step 1) and the derived
  `sessions` table. `clock.fit_dte` stays [1..6] for the surface's R(dte), which the design defines on 1-6.
- **Trading days left counts the expiry day itself** - the number of sessions in (d, e] - so a chain on the day
  before expiry has dte 1 and is outside the window. Weeklies are five sessions apart, so on four days in five
  only one of the two nearest expiries qualifies: 2019 gives 237 ATM observations over 220 days, about 950 for
  the four-year frozen fit. That is the whole sample the weekend and holiday weights rest on.
- **A gap with a hole in the chain is dropped, not stretched.** The difference in scaled implied variance is only
  one night plus one session wide when the two days are consecutive sessions. NSE published nothing for
  2021-03-30, a real trading day, so pairs spanning it would carry two nights and bias both betas.
- **theta_n pairs each night with the session that follows it**: r_on,d = ln(O_d / C_d-1) against ln(C_d / O_d)
  for the same d, which is also the order the clock lays a gap and a session out. Both means run over the same
  back-to-back pairs, and a pair whose day is missing from `daily` is skipped rather than filled.
- **The reported standard errors are beta1's and beta2's from (X'X)^-1 s^2, scaled by (1 + theta_n) / beta0** onto
  the theta scale, ignoring beta0's own uncertainty (the delta method for a ratio would need Cov(beta0, beta1),
  and the plan asks for (X'X)^-1 s^2). They go in the CLOCK pilot report and gate nothing.
- **`gap_days` came out of `_gap_weights`** so the clock and its fit count weekend days and weekday holidays the
  same way by construction, not by two copies of the same loop agreeing.
- **Slot 0 is measured from the official open in `daily`, not from the first minute bar's print** - the same
  anchor the noise band uses. A bar missing on one day leaves that slot and the return spanning it out of the
  mean; nothing is filled in, because a filled hole moves variance to the wrong minute of the day.
- **Measured on real data, 2019-2022, 981 regular sessions.** theta_n = 0.5356, an overnight share of 0.349,
  against research's 0.38-0.43 (theta_n 0.61-0.75): inside the plan's 0.3-1.0 sanity band but at its low end, so
  CLOCK.md must say so rather than quote the range as confirmed. Minute weights: 18.1% of a session's variance in
  the first 15 minutes, 2.6% at midday, 5.1% in the 15:00-15:15 block, and the 09:15 slot alone carries 8.5%.
  On 2019 chains only, theta_w = 0.203 +/- 0.107 and theta_h = 0.235 +/- 0.374; the holiday error is wide because
  a year has some fifteen holidays, and the four-year fit should roughly halve it.
- **Only 10.6% of 2019 bhavcopy option rows dealt** (81,539 of 770,822). The `traded` filter is what makes the
  ATM choice meaningful: an untraded row carries a close but no price, and at the money that close is often a
  stale settle far from anything tradable.

## 2026-10-22: R40, z references for signal-only features

The distance to VWAP and the room to the nearest level are measured in stop-distances, which exist only when a signal fires. Scoring them against "the same check time in earlier sessions" (R10) would need years of signals per check time before any score is defined.
- **Ruling.** These two features are z-scored against earlier signals, pooled across check times (key `(feature, "*")`), with the same window of 250 and minimum of 60.
- **Unchanged.** Breadth keeps its per-check-time reference, and the option inputs a per-day reference.
- **Causal.** Every reference uses sessions before the day being scored (`DayLoader.z_refs`).
- *Cost if wrong:* early-2019 signals have no technical score until 60 earlier signals exist, so they don't count (R12).

## 2026-10-22: SP3 phone alerts via a Telegram bot (owner)

- **Decision.** Alerts, stop-move instructions and exits reach the owner's phone through a private Telegram bot, alongside the laptop dashboard and its sound alert.
- **Why.** Free, reliable push to any phone, and a private chat with the owner's own bot.
- **Owner step.** Create the bot with @BotFather, then put `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env`. Never commit them.
- **Privacy.** Messages carry only public market levels and the system's own suggestions. No credentials, account data or positions held at the broker.

## 2026-10-22: SP3 build rulings (live engine, dashboard, replay)

The SP3 design's rulings S1-S12 are in `docs/superpowers/specs/2026-10-22-sp3-live-engine-dashboard-design.md`. These are the calls made while building it.

- **No dataset, no live run.** `live` refuses to start without the signal dataset and logs `not_started`. Shadow setups from an unfitted model would go into the clean forward holdout (D4) and spoil it. *Cost if wrong:* no shadow log on days before the dataset first exists.
- **Effective mode.** Live only when all three hold: the verdict is alert-on, no kill-switch is standing, and no shadow pause covers the day. A kill-switch firing sets journal state `kill_switch`, and the owner's typed unlock clears it. Pauses are journalled. The dashboard reads the same state, so the phone and the screen always agree.
- **Kill-switch levels.** They come from the accepted trial's median-path trades:
  - mu0 = mean net R; sigma = sd; breakeven = 0 net R
  - CUSUM threshold bootstrapped from those trades for a mean run length of 250 in control
  - In shadow mode there are no levels and no switches, because there is no validated edge to monitor.
- **The monthly cap uses the whole calendar year's NSE sessions,** not the sessions so far. Counting only sessions so far gives early months too small a share.
- **When the source is rebuilt.** The live source is rebuilt only when the recorder writes a new file (bars, snapshots or meta), not on a timer. A check then runs within about 5 seconds of its bar landing, and the frame is built once per write rather than on every 5-second poll.
- **No day card before the first index bar.** Without a recorded open there is no gap, no HAR forecast and no band, so the engine waits rather than caching a card built without today's open.
- **Telegram failures are logged with the token masked.** requests puts the URL, which carries the bot token, into its error messages, so the token is masked before logging. Test: `test_a_failed_send_never_logs_the_token`.
- **Shadow mode logs every setup, not only the capped ones.** The caps (1 a day, 3 a week, monthly share) are applied when the holdout is analysed, as R31 does in the backtest. Locks apply only to live alerts.

## 2026-10-22: P9 failed; the stock-volume VWAP proxy is kept (no P&L seen)

- **What P9 found.** P9 ran on 11 front-month futures days, 3,971 minutes.
  - **Side test (passed):** the sides disagree in 4.1% of minutes, against a pass mark of at most 5%.
  - **Gap test (failed):** the median gap is 0.23 b, against a pass mark of at most 0.1 b. It failed on all 11 days, so this is not a small-sample fluke.
- **The pre-registered rule.** It said a fail switches every VWAP rule to the average typical price since the open.
- **What the fallback measured.** Measured the same way, the fallback is worse: a median gap of 0.44 b and 6.6% side disagreement. Following the rule literally would move every VWAP rule further from the real VWAP. That defeats the fallback's purpose, which was to stop pretending to track VWAP when the proxy can't.
- **Ruling: keep the proxy.** Both choices were made before any P&L was seen, and P9 costs no trial, so this is not a forking path on profit.
- **Wording.** Every result must say that "VWAP" is the proxy, a median 0.23 b (about 8 points) from the futures VWAP.
- **Re-check.** Re-run P9 at 40 or more futures days.
- *Cost if wrong:* VWAP-based rules (the side check, the structural stop, the trail ratchet) sit about 8 points from where a futures trader's VWAP is. The backtest and live engine share the proxy, so the measured edge is the edge of the rule as built, not of a futures-VWAP rule.

## 2026-10-22: P4, no reversal context

- **Result.** AR(1) = -0.027 (t = -0.81) and MAC(5) = 0.076 (t = 0.80) over 2,911 days. There is no significant daily autocorrelation.
- **Consequence.** `ctx_runs` is False, so trial CTX does not run and its reversal feature is not built (R37). The slot stays unused.

## 2026-10-22: locks and kill-switches count only live alerts

- **Bug found in self-review.** Shadow and suppressed setups also open paper trades. Before this fix, their P&L counted toward the day and week loss locks and the ₹7,000 capital floor, and their R values fed the SPRT and CUSUM. Shadow P&L is not money, so a run of shadow losses could have locked live alerting or fired the capital floor.
- **Fix.** `book()` and the cap counter now read only trades from alerts whose mode is `live`.
- **Test.** `test_shadow_paper_trades_are_not_money`.

## 2026-10-22: actual expiries, the nightly derive, and the stale-table guard

- **What crashed.** P1 and the signal dataset both crashed on 2023-06-29. That day was the listed expiry of the June 2023 Nifty contracts, but it became a holiday at short notice (Bakri Id), so the contracts expired on 2023-06-28. The old bhavcopy layout carries only the listed date. Six expiries are affected:
  - NIFTY 2023-03-30, 2023-06-29, 2026-03-26, 2026-03-31
  - SENSEX 2024-11-01, 2026-01-15
- **Ruling: actual expiry.** `options_eod.expiry` is now the last session on or before the listed date (the exchanges' rule). Past dates are checked against recorded sessions, future ones against the published holiday calendar. The printed date is kept as `expiry_listed`. Every reader (the expiries table, the options score, strike candidates, the live source) now sees the date the contract really expired.
  - *Small look-ahead, accepted:* a chain dated before a late holiday announcement is treated as already knowing the new date. That shifts time to expiry by one session on contracts many sessions out.
  - Test: `test_an_expiry_on_a_holiday_moves_to_the_session_before`.
- **Nightly derive at 23:30.** It runs after the evening downloads: eod at 18:35 and the history backfill at 20:30. Without it, the 09:10 live run would start on stale tables and take an older close as yesterday's, which makes every band and gap wrong.
- **Stale-table guard.** `live` refuses to start, and logs `not_started`, when the derived tables don't reach the previous trading day. Test: `test_the_live_engine_needs_last_nights_derived_tables`.

## 2026-10-22: paper trades fill by the backtest's rule

- **The mismatch.** Live paper trades opened at the moment of the alert, at the previous minute's ask. The backtest instead fills one minute later, at the bar T + delay − 1 (delay 1), at ask + 1 tick, with the chase cap and the 5-minute lapse. So the forward record and the backtest weren't comparable.
- **Ruling.**
  - The live engine waits for the fill bar, then calls the backtest's own `fill()`.
  - An unfilled alert is journalled as `paper_unfilled` with its reason (`lapsed`, `rejected_flip`, or "fill bar never recorded").
  - Test: `test_a_live_alert_is_journalled_pushed_and_paper_traded`, which compares against `fill()` directly.
- **The cap while a fill is pending.** The backtest counts the cap on filled trades, NIFTY first at equal times. Live can't know at T whether the first alert will fill, so a pending live alert holds a place under every cap until it fills or lapses.
  - *The one divergence:* both indices signal in the same minute and the first one lapses. The backtest would then trade the second, but live has already held it back. This is rare, and the error is on the safe side (one alert too few, never one too many).
  - Test: `test_a_second_index_alert_at_the_same_check_is_held_by_the_pending_first`.

## 2026-10-22: late starts and restarts of the live process

- **Late start.** A check more than 60 seconds old is never run, even when its bar exists, so no stale alert reaches the phone (S4's "give up 60 seconds after T"). Such checks are journalled as `missed`. The forward holdout loses nothing, because the `dataset` command rebuilds those decisions from the recorded day.
- **Restart.** Today's open paper trades are rebuilt from the journal by re-running the decision at their alert time, which is deterministic on the same bars. Their stop-move and exit messages then carry on. Ratchets already sent are counted from the journal and not sent again.
  - *Not covered:* an alert whose fill was still pending at the moment of the crash. It stays journalled, but no paper trade opens.
- **Tests.** `test_a_late_start_never_alerts_on_old_checks`, `test_a_restart_resumes_the_open_paper_trade_and_its_exit_messages`.

## 2026-10-22: owner's choice B (shadow alerts on the phone, early pricing pre-check), and what D2 found

- **Shadow alerts on Telegram (owner).** Each shadow alert goes to the phone marked "ALERT (SHADOW - do not trade)", and each shadow exit as "SHADOW EXIT NOW". Stop moves stay on the dashboard to keep the phone quiet. This amends S2, which pushed nothing in shadow mode. Switch: `LiveEngine.push_shadow`.
- **Early pricing pre-check.** `python -m quantdesk precheck` uses R17's own metric on Angel's 1-minute candles of listed contracts. It costs no trial and gates nothing. It has no expiry days, and its prices are last trades rather than quotes.
  - **First read (29 Sep to 21 Oct; 132 contracts, 15 sessions, 28,958 moves):** median error 0.22 against R17's pass mark of 0.15.
  - **By horizon:** 0.26 at 15 minutes and 0.20 at 60 minutes.
  - **What it means:** an early warning that the model may fail R17. The recorded check (quotes, expiry days) decides.
- **D2 is triggered, and not by a bug.** P1 found 4 eligible signals in 7 years (0.67 a year) against a threshold of about 60. Of the 546 dataset signals that pass every gate, only 4 have a strike reaching gain/loss ≥ 1.5. The best strike per signal has a median G/L of 0.74.
  - **Why:** the median structural stop on those signals is 6 index points, so the planning target is about 14 points. A 14-point move doesn't pay for the spread, about ₹57 of charges and an hour of theta at ₹400 risk. This is the convexity problem flagged at the clock fit, now measured.
- **D2 scenario measured before the owner chooses.** P1, P2, P10 and D2 were re-run with D2 option 1 (₹15k capital, ₹600 stop) as `pilot ... --scenario d2_600`, writing `*-600.md`. They count setups and never look at profit.
  - *Ruling:* at ₹15k the premium budget is ₹14,500, the same ₹500 margin under capital as ₹9,500 at ₹10k. The spec gives no figure.

## 2026-10-22: D2, the owner chooses alert-off; no X2

- **Evidence.** D2 was triggered at both stakes:
  - ₹400: 0.67 eligible setups a year (4 in 2019-2025)
  - ₹600: 1.7 a year (16)
  - Needed: about 60 a year. P10 gives a 0% and a 2% chance that every gate could pass.
  - The cause is a median 6-point structural stop against an option's fixed frictions. Breakeven needs about a 57% hit rate; the index target is reached about 38% of the time.
- **Owner's decision.** Alert-off (`owner.d2_choice`), and no X2 (`owner.x2_opt_in: false`). `research/VERDICT.md` records the verdict.
- **What this means.**
  - No trial slot was spent. The live engine stays in shadow mode, with shadow calls on Telegram, and records a forward log.
  - The pricing check, freeze and trials for this hypothesis are no longer needed.
  - The recorder keeps collecting quotes, so any future, newly pre-registered idea can be priced and tested properly.

## 2026-10-22: the owner's daily feed (morning brief, CALL/PUT ideas, day summary, Friday scorecard)

- **What the owner asked for.** A daily market update with sentiment, and call or put ideas with entry, target and stop when the market moves. They size every trade themselves and test on paper before using real money.
- **What runs while the verdict is alert-off.**
  - **09:20 morning brief:**
    - global cues, from the morning macro pull
    - FII index-futures positioning
    - a rough news tone (word counts on headlines since the previous close)
    - for each index: the open and gap, the expected range (the HAR forecast), VIX, put/call ratio, levels, expiry and events
    - an experimental direction lean (options score + flows score + overnight US futures, threshold ±1.0), scored at the close
  - **Intraday CALL/PUT ideas:**
    - **Same as the strategy:** the H1 breakout, all seven gates and the strike picker's G/L ≥ 1.5 and delta band.
    - **Removed: the rupee caps** (₹400 stop, ₹9,500 premium budget). The owner sizes each idea.
    - **Not enforced: the EV gate.** The system's odds and breakeven are shown instead.
    - **The backstop** sits at the strike's planned loss at the index stop.
    - **Message:** each idea is sent with its rupee risk and planned gain per lot.
    - **Tracking:** each idea becomes a one-lot paper trade by the backtest's fill and exit rules. Stop moves and exits are sent, marked IDEA.
    - **Limit:** one open idea per index at a time.
  - **15:35 day summary:** the move against the forecast range, the lean scored, and the ideas in ₹ per lot.
  - **Friday scorecard:** the week's ideas (count, filled, targets hit, net ₹ per lot) and how often the lean was right.
- **Honest wording, in every message.** "Paper-tracked; your call, not advice". The lean is "experimental". Research puts intraday direction close to a coin flip, which is why everything is scored.
- **Unchanged.** The pre-registered verdict, the trial slots and the registry. The feed is not a validated strategy, and its scorecard is not a backtest.
- **The feed's settings were measured before going live** (P1 counts only, no profit seen):
  - **Rupee caps removed only:** 38 setups in 2019-2025, about 4 a year. Too few for a daily feed.
  - **Relaxed (the live default):** rupee caps removed, the two "room" gates skipped, and gain/loss ≥ 1.0 instead of 1.5. That gives 2,795 setups, on about 82 trading days a year (roughly 1 day in 3).
  - **Gates kept:** event/shock days, stop size against the day's move, rich volatility, breadth confirmation and the spike guard.
  - **Cost if wrong:** more ideas of lower quality. The Friday scorecard will show it, and the setting is one constant (`IDEAS_RELAXED` in `validation/pilots/run.py`).

## 2026-10-22: the live process warms its signal references (bug fix)

- **The bug.** The technical score's signal-only features (R40) are z-scored against earlier signals. Only `build_dataset` records those, as it walks history. A freshly started live process (and `replay`) had none, so with a model every decision stopped at `warmup`, and the live engine could never alert, strict or idea. The 22 Oct replay showed parity only because both sides shared the gap. Found by replaying a past setup day in idea mode.
- **The fix.** `warm_signal_refs` walks the last 90 regular sessions exactly as the dataset builder does (same days, indices and order) and records their signals. The references keep the last 250 signals (about 45 sessions), so live and backtest use the same values.
  - Test: `test_a_fresh_process_rebuilds_the_signal_references_from_recent_sessions`.
  - Check: replaying 31 Dec 2025 in idea mode now gives 4 ideas with their exits.

## 2026-10-22: SP4, the pilot's rule picks Path B, and the compact desk is built

- **Pilot result.** All 3 measured TradingAgents runs (and the earlier run with default settings) failed. Groq rejected requests as too large (HTTP 413; the largest was 20,515 tokens against the 7,000-a-minute limit), and one run had a connection error.
  - Path A needs ≥ 90% of runs complete and no request over the per-minute limit.
  - A 413 can't be undone by later runs, so `decide()` now returns Path B as soon as one is seen ("decided early").
  - Test: `test_a_reason_more_runs_cannot_undo_decides_path_b_early`. The nightly pilot job is removed.
- **Path B: the compact desk** (`quantdesk/desk/compact.py`, `python -m quantdesk desk`), as spec §7A.3-7A.6 specifies:
  - **Calls:** four analysts (technical, macro, options flow, news) and bull/bear on `qwen/qwen3.8-27b`; the risk manager and judge on `openai/gpt-oss-120b`. 8 calls a day.
  - **Prompts:** our numbers and timestamped headlines only, each ≤ 5K tokens, with the pilot's token bucket per model.
  - **Replies:** Pydantic JSON, retried once if invalid. A 413 shrinks the prompt once, then the role is skipped.
  - **Number-faithfulness check:** every number in the text must match an input within 0.5%, otherwise the brief is UNVERIFIED and not scored.
  - **Output:** `data/desk/<day>.json` and `desk_calls.jsonl`.
  - **Scoring:** a verified bias is scored against Nifty open to close in the day summary, and counted in the Friday scorecard.
  - **Delivery:** the brief goes to Telegram.
- **Schedule ruling.** The spec had an evening full run plus an 08:40 update. Instead there is **one full run at 08:30**, after the nightly derive (fresh chain, daily and FII tables) and the 07:30 macro pull (overnight US and Asia). Everything is current in one pass, and it lands before the 09:20 brief. *Cost if wrong:* no evening read; the morning one is the one that matters for the day.
- **Not built.** The Ollama fallback, which the spec marks optional. A Groq outage means no desk brief that day, logged as a failed role.
- **First live call (22 Oct, for 23 Oct, not sent):** bias DOWN 65%, range ±0.91%, numbers verified.
