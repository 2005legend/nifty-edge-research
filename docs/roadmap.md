# Roadmap

Status on 21 Oct 2026: SP1, the data foundation, is built, merged to `main` and verified live: all 7 live tests pass, the first session was recorded, and the history backfill is running. Phase 1 still needs the Task Scheduler jobs, a full-day health report and the two open URLs. Everything that turns data into alerts is still to be built.

The design is in [the spec](superpowers/specs/2026-10-06-nifty-sensex-options-signal-system-design.md). Daily operation is in [the runbook](runbook.md). Every decision and its reason is in [decisions.md](decisions.md).

## What is left

| Part | What it does | Status |
|---|---|---|
| SP1 data foundation | Records live ticks and option chains, downloads history, EOD files, macro data and news | Built. Needs your credentials, a live check and the backlog below |
| SP4 analyst desk | Groq LLM writes an evening brief and a morning update. Commentary only, never a trade vote | Not started. The pilot comes next |
| SP2 strategy core and backtester | Chart and macro engines, the H1 signal pipeline, the 2019–2026 simulation, the pre-registered validation | Not started. Needs a design pass first |
| SP3 live engine, dashboard, journal | Alerts at `127.0.0.1:8000`, paper trades, trade journal, locks, kill-switches | Not started. Needs a design pass with dashboard mockups |

So yes, most of the system is still ahead. SP2 is the largest piece and the one that decides whether the system ever sends an alert.

## What sets the pace

Writing code is not the slow part. Collecting data is:

- The option-pricing check needs 2–4 weeks of recorded sessions. Each trading day without the recorder running pushes it back by a day.
- The desk's first honest verdict comes at about 250 scored sessions, roughly one trading year.
- The clean forward test needs about 150 labelled setups after the rules freeze. At 60 eligible setups a year, the lowest rate the D2 checkpoint accepts, that is about 2.5 years. This rate is a guess until the SP2 pilots measure it. Trading more than 1 lot waits for this test.
- Paper trading runs 1–2 months with frozen rules. At 3 trades a week or fewer that is at most about 25 trades: enough to check fills and costs, not enough to prove an edge.

That is why the recorder should run every trading day from now on, long before any strategy code exists.

The research also says the most likely result of SP2 is that no configuration passes its gates. In that case the system runs in alert-off mode, with the recorders and the desk still going. That is a valid ending, and the plan is built to reach it honestly.

## Phases

### Phase 1: SP1 goes live (this week, you)

1. Create `.env` as in runbook step 1. Use new FRED and Groq keys, because the old ones were exposed. Once `.env` works, delete `env.txt`.
2. Run `.venv\Scripts\python -m quantdesk login-check`.
3. During market hours, run `.venv\Scripts\python -m pytest -m live -v` (5 tests).
4. Set up the Windows Task Scheduler jobs from the runbook.
5. Start both one-off backfills (`backfill --what history` and `backfill --what bhavcopy`). They take hours and resume safely.
6. After the first recorded day, run `python -m quantdesk status`. Expect 375 minutes recorded and an empty problem list.
7. Answer spec §9 items 1 and 2 and write the answers into `decisions.md`:
   - Does Angel One serve 1-minute candles for expired futures?
   - What is the real per-connection websocket token limit? `max_tokens_per_connection: 1000` is a guess.
8. Find working URLs for FBIL G-sec yields and the NSE index P/E file, and put them in `config/settings.yaml` (`urls.fbil_gsec`, `urls.nse_index_pe`). Each source also needs a small fetch-and-parse function in `quantdesk/macro/sources.py`; both currently raise `NotImplementedError`.

Phase 1 is done after 5 trading days in a row with full recordings and no unexplained problems in the health report.

### Phase 2: SP1 backlog (done 21 Oct 2026)

All 14 items from the final review are fixed, each with a test that failed first (commits `0d6503d`..`c14e719`):
- the day's token-to-contract map is saved
- a frozen feed forces a reconnect
- the session is renewed after midnight or a `TokenException`
- holidays are checked before downloads
- the end-of-day job retries network errors and block pages hourly and works without Angel credentials
- the news poller survives errors and runs once only
- the master fallback and recorder errors appear in the health report
- the run lock is an OS file lock
- the subscription map is copy-on-write
- bar volume is correct at the open and for out-of-order ticks
- GDELT files are processed once
- the history manifest lives in `data/state`
- recentring respects the token budget
- `last_traded_timestamp` is read as epoch seconds (checked live)

### Phase 3: SP4 desk pilot (starts once SP1 records daily)

The desk goes before SP2 because its scoring clock (about 250 sessions) is the longest one.

1. Install TradingAgents v0.7.0 into a separate `.venv-desk` and point it at Groq (spec §7A.3).
2. Run it on `^NSEI` once a day for 5–10 sessions, logging calls, tokens, the largest request, 413/429 errors and wall time.
3. Apply the decision rule. Use Path A (adapt TradingAgents) if at least 90% of runs complete, no request goes over the per-minute limit and daily tokens stay at or under 150K per model. Otherwise use Path B (a compact desk of about 8 calls a day).
4. Build the chosen path under its own plan: evening run after 19:00, morning update at 08:40, the `desk_calls` table, the number checker and forward scoring.

Until the SP2 engines exist, the desk's input is SP1's raw numbers: index levels, VIX, FII/DII flows, participant OI, the macro series and timestamped headlines.

### Phase 4: SP2 strategy core and backtester (design pass first)

A design pass turns spec §5A and §6 into exact rules, then I write 2–3 implementation plans. The likely build order:

1. Data access: DuckDB views over the recorded and backfilled Parquet, plus a table of market rules by date (lot sizes, STT rates, the Thursday-to-Tuesday expiry change in Sep 2025, the closing auction from 3 Aug 2026).
2. Cost model: ₹20 brokerage per order, STT, exchange charges, SEBI fee, GST and stamp duty. It is checked against the research notes' worked examples, about ₹56–58 fixed cost per round trip.
3. Business-time Black-76 option pricing: checked first against known values, then against recorded chains once Phase 1 has produced them.
4. The technical engine (§5A.1) and the macro engine (§5A.2), each producing its family score.
5. The pipeline, as pure functions: day card → H1 trigger → gates → meta-model → EV gate → strike picker → exit plan → alert.
6. The backtester: entry delays of 0, 1, 3 and 5 minutes; chase and lapse rules; spreads by time of day; report splits at June 2024, 20 Nov 2024, 1 Sep 2025 and 3 Aug 2026.
7. Leakage tests and placebo tests.
8. The research registry: `research/hypotheses.yaml` and `research/experiments.csv`, the eight zero-trial pilots (including pilot 7, pretrained volatility models against HAR, and pilot 8, the headline tone classifier), the D2 checkpoint, then the trials in registry order with a hard cap of 13.
9. The recorded-day pricing check: the median error in modelled premium change must be 15% or less.

Phase 4 ends with a verdict: alert-on for a configuration that passes every gate in spec §6.3, or alert-off.

Items 1–3 are pure functions with known answers and don't depend on any strategy choice. They can start before the design pass. So can the labelling for pilot 8: about 300 collected headlines, each marked for tone and whether it moves the market, done before any model has scored them.

### Phase 5: SP3 live engine, dashboard, journal (design pass with mockups first)

- A FastAPI app at `127.0.0.1:8000` with Today, Journal and Research tabs.
- Alert cards with a 5-minute lapse, "took it / skipped" buttons and a fill box.
- Paper trading, the locks from spec §2, and the kill-switches: SPRT and CUSUM on mean net R, the ₹7,000 capital floor, and costs more than 30% above assumption.
- Replay mode for any recorded day.
- The parity test: a recorded day replayed through the live engine must produce exactly the backtester's alerts.
- The analyst-desk panel, which is the SP4 integration.

### Phase 6: Paper trading (1–2 months, rules frozen)

It passes when there are no open defects and measured costs are no more than 20% above the assumption. Tuning happens only in simulation, never on paper results.

### Phase 7: Live with 1 lot

Monitoring runs as in spec §7. Moving above 1 lot needs all four:
- capital of at least ₹20,000
- at least 100 live trades
- an SPRT "GO"
- a pass on the clean forward test

## Who does what

| Work | Suggested owner | Why |
|---|---|---|
| Phase 1 | You | It needs your credentials, your account and market hours |
| Backlog items | Either | They are well defined and each has a clear test. The two `High` recorder items are a good first task |
| Cost model, Black-76 pricing, market-rules-by-date table | You, if you want a bigger piece | Pure functions checked against known numbers |
| Desk pilot | I set it up, you run it daily | Runs happen in the evening |
| Labelling 300 headlines for pilot 8 | You | You read Indian market news daily, and the labels must be made before any model output is seen. About 1–2 hours |
| SP2 and SP3 design passes, the registry, the validation statistics | Me, with your decisions | This is where a mistake quietly inflates backtest results |
| Reviewing your branches | Me | A second read before merge |

## Rules when you write code here

- Work on a branch from `main` (for example `git switch -c fix/option-meta`) and merge back when the whole suite passes.
- Write the failing test first, then the code. Run `.venv\Scripts\python -m pytest -q`: 124 tests, all offline, about 10 seconds.
- Normal tests never touch the network. Pass the clock, sleep, HTTP and stream in as arguments and use the fakes in `tests/fakes.py` (`FakeClock`, `FakeHttp`, `FakeSmartConnect`, `ScriptedStream` and others). A test that needs Angel One gets `@pytest.mark.live`.
- Never edit or overwrite anything under `data/raw`; `Store.write_raw` refuses. Tables go through `Store.append_parquet`.
- No order-placing code. `test_no_order_methods_exist` in `tests/test_angel.py` enforces this. The app sends alerts; you place orders yourself.
- Secrets live only in `.env`. Don't print them, log them or commit them.
- Don't run P&L backtests of strategy ideas before the registry exists. Every look at historical profit counts as a trial against the 13-trial budget (spec §6.3). Looks that aren't logged make the deflated Sharpe and overfitting numbers meaningless. Pass-rate and excursion studies are fine, because they don't rank P&L.
- Write each design decision into `docs/decisions.md` with its date and reason.
- Commit messages start with `feat:`, `fix:` or `docs:`.

## Asking me for help

- "Design pass for SP2" (or SP3): I go through the open questions with you, update the spec and write the plan.
- "Fix backlog item: …": a test-first fix on its own branch.
- "Review my branch `<name>`": a full review before you merge.
