# quantdesk handbook

This is the one document to read first. It covers what the system is, what it sends you each day, how to run
and repair it, where everything lives, what the research found, and how to continue the work. It assumes no
memory of the conversations that built it.

Status on 22 Oct 2026: **everything is built and runs by itself every weekday.** 546 automated tests pass.

- Daily operations in more detail: [runbook.md](runbook.md)
- Every design decision and the reason for it: [decisions.md](decisions.md)
- The full design: [the spec](superpowers/specs/2026-10-06-nifty-sensex-options-signal-system-design.md)

---

## 1. What this is

A personal, local signal system for **Nifty 50 and Sensex weekly options**, running on your Windows laptop
with live data from your **Angel One SmartAPI** account. It:

- records the market every minute: indices, VIX, the 50 Nifty stocks, and the option chains
- sends you a **morning brief**, **CALL/PUT trade ideas** with entry, stop and target, and an **evening
  summary** on Telegram
- paper-trades every idea, so you can see whether the ideas actually make money
- writes an **AI analyst brief** each morning through Groq's free LLM tier
- keeps a journal of your own fills and exits, and compares them with the system's

**It never places an order.** You place every trade yourself in Angel One.

### The honest headline

The strategy was pre-registered and tested properly, and its verdict is **alert-off**.

The noise-band breakout fires often, but at ₹400 risk a single lot gives only a ~12-point Nifty stop. That's
smaller than ordinary market noise, and the option's spread, charges (~₹57) and time decay eat the target.
Result: 0.7 testable setups a year at ₹400, 1.7 at ₹600, against about 60 needed. So the system will not tell
you "this is a validated trade".

What it gives you instead, by your choice, is the **idea feed**: the same breakout logic with the rupee caps
removed. Each idea shows its real ₹ risk per lot, you size it, and every idea is scored on paper. **Treat the
ideas as untested until the Friday scorecards say otherwise.**

---

## 2. Your day

All times are IST, Monday to Friday. Every job runs from Windows Task Scheduler. The laptop must be on, with
internet, from about 08:30 to 15:35.

**Keep it awake before 08:30.** On 26 Oct it slept until 10:08 and missed the morning. Either leave it on
overnight, or enable *Power Options → Change plan settings → Advanced → Sleep → Allow wake timers*. If it
starts late anyway:
- The recorder and live engine also start at logon, and retry at 09:05/09:30 and 09:20/09:40.
- A late recorder first fetches the missed morning minutes from Angel, so the day's open and bands stay right.

| Time | What happens | You get on Telegram |
|---|---|---|
| 06:55 | News collector starts (runs all day) | – |
| 07:30 | Global macro pull: US close, Asia, oil, rupee, yields | – |
| **08:30** | **AI analyst desk** (8 Groq calls) | **DESK BRIEF**: bias, confidence, expected range, bull and bear cases, cautions, with numbers verified against our data |
| 08:55 | Recorder starts (09:15–15:30 data) | – |
| 09:10 | Live engine starts; the dashboard opens at http://127.0.0.1:8000 | – |
| **09:20** | Morning brief | **MORNING BRIEF**: global cues, FII positioning, news tone, and for each index the open and gap, expected range, VIX, put/call ratio, levels, expiry, events, and an up/down/flat lean |
| **During the day** | Every 15–30 minutes the engine checks for a breakout | **IDEA – CALL/PUT** when one qualifies, then **IDEA MOVE STOP** and **IDEA EXIT NOW** |
| **15:35** | Day ends | **DAY SUMMARY**: each index's move against the forecast range, whether the lean and the desk were right, ideas in ₹ per lot |
| **Fri 15:35** | Week ends | **WEEKLY SCORECARD**: ideas, targets hit, net ₹ per lot, how often the lean and the desk were right |
| 18:35 | End-of-day files: bhavcopy, participant OI, FII/DII; evening macro | – |
| 20:30 | 1-minute history top-up | – |
| 23:30 | Derive: rebuilds the tables the next morning needs | – |

**How often ideas come:** in 2026 so far, on 79 of 196 sessions, about 2 days a week. Often there are 2–4
on those days. Flat days give none. There is one open idea per index at a time.

### An idea, and what to do with it

```
IDEA 11:00 - BUY NIFTY 26100 CE (CALL), expiry 2026-01-06, lot 65
Entry: buy at or below Rs 83.25 (skip if not filled in 5 min)
Target: Rs 94.80 on the option | NIFTY 26072.5
Stop-loss: Rs 74.70 on the option (SL-limit Rs 67.23) | NIFTY 26032.5
System odds 25% vs 45% needed. Unvalidated, paper-tracked; your call, not advice.
```

The picker prefers the **nearest expiry** and a strike near 0.40 delta (slightly out of the money, so a cheaper
contract). There are no rupee amounts and no rupee filters: you size the trade (owner's choice, 26 Oct).

1. **Decide.** "System odds" is the model's own estimate, often low; it's shown, not used to block.
2. **If you take it:** buy with a limit order at or below the entry price within 5 minutes. Then place the SL-limit order at the
   stop-loss and limit shown, and a sell at the target if you want it to exit by itself.
3. **On the dashboard:** press **took it** and type your fill, or press **skipped**. When you exit, type the exit
   price in **log exit** (the P&L after charges is computed for you). If you override an exit message, say so in the note.
4. **Follow the messages.** MOVE STOP means move your stop. EXIT NOW means sell at the bid.
5. **On Friday, read the scorecard.** It's the evidence: a few weeks of positive net ₹ per lot before any real
   size, and still small.

---

## 3. Commands

Run these from the project folder (`C:\Users\USER\sidaarth\Trading project`) as `.venv\Scripts\python -m quantdesk <command>`.

| Command | What it does |
|---|---|
| `live` | The live engine, Telegram and the dashboard, 09:10–15:35 (scheduled) |
| `dashboard` | The dashboard outside market hours |
| `desk [--day D] [--dry-run] [--no-send]` | The AI analyst desk brief (scheduled 08:30) |
| `record` | The market recorder (scheduled 08:55) |
| `derive [--only TABLE]` | Rebuild the derived tables from raw data (scheduled 23:30) |
| `eod [--day D]` | End-of-day NSE/BSE downloads (scheduled 18:35) |
| `macro [--intraday]` | Global and macro data |
| `news [--once]` | News collector |
| `status [--day D]` | Data health for a day |
| `telegram-setup` | Save your Telegram chat id after you message the bot |
| `replay --day D` | Run a recorded day through the live engine and check every decision against the backtest |
| `precheck` | Early pricing check of the option model on Angel's 1-minute option candles |
| `pricecheck` | The real pricing check on the recorder's quotes (needs 15+ sessions, 4 expiry days per index) |
| `pilot P1/P2/P4/P9/P10/D2 [--scenario base/d2_600/ideas/ideas_relaxed]` | The zero-trial research pilots |
| `dataset` | Rebuild the signal dataset 2019 to yesterday (about 1 hour) |
| `ideas-backtest` | Look 47: the idea feed on history, untuned. Writes `research/pilots/IDEAS-BACKTEST.md` |
| `live --force-live` | Live alerts by the strict research rules despite alert-off. About 0–2 a year; the idea feed is the default |
| `freeze`, `preflight`, `trial <id>`, `verdict` | The pre-registered validation (only for a future strategy) |
| `backfill --what history/bhavcopy/fundamentals/participant_oi/macro` | Download history |
| `login-check` | Check the Angel One login |

**Long jobs** (`dataset`, `backfill`, `derive`) must run detached, so closing an app can't kill them:

```
powershell -ExecutionPolicy Bypass -File scripts\run_detached.ps1 -Name dataset -Run "-m quantdesk dataset"
```

**Tests:** `.venv\Scripts\python -m pytest -q`. Expect `546 passed`. Run them after any change.

---

## 4. Setting it up again (new laptop or a broken install)

1. **Install Python 3.11+**, then in the project folder:
   ```
   python -m venv .venv
   .venv\Scripts\python -m pip install -e ".[dev]"
   ```
2. **Create `.env`** (copy `.env.example`). Never commit it, never paste it into a chat.
   - `ANGEL_API_KEY`, `ANGEL_CLIENT_CODE`, `ANGEL_PIN`, `ANGEL_TOTP_SECRET`: Angel One SmartAPI
   - `FRED_API_KEY`: free, fredaccount.stlouisfed.org
   - `GROQ_API_KEY`: free, console.groq.com (the analyst desk)
   - `TELEGRAM_BOT_TOKEN`: from @BotFather (your bot is t.me/Dailytradinginfobot)
   - `TELEGRAM_CHAT_ID`: written by `telegram-setup` after you send the bot a message
3. **Check the login:** `.venv\Scripts\python -m quantdesk login-check`
4. **Restore the data.** `data\` isn't in git, so copy the old `data\` folder across. Without a copy, run the
   backfills (`backfill --what history`, then `bhavcopy`, `participant_oi`, `macro`, `fundamentals`), then
   `derive`, then `dataset`. All are long, so run them detached.
5. **Register the daily jobs:**
   ```
   powershell -ExecutionPolicy Bypass -File scripts\schedule_tasks.ps1
   ```
6. **Telegram:** message your bot, then run `.venv\Scripts\python -m quantdesk telegram-setup`. A test message should arrive.

---

## 5. How it works

```
 Angel One live feed ──► recorder ──► data/raw (bars, option snapshots, meta)        ┐
 NSE/BSE EOD files, macro, news ──► eod / macro / news ──► data/raw                  ├─► derive (23:30) ──► data/derived
 1-minute history (Angel) ──► backfill ──► data/raw/history_*                        ┘        (minutes, daily, options_eod,
                                                                                                expiries, macro, fii_ratio,
                                                                                                members_minute, sessions)
                                     │
 09:10  live engine  ◄───────────────┘  + today's recorder files, rebuilt each time the recorder writes
   day card (open, gap, HAR expected move, noise bands, events, expiry)
   └► every check time: H1 breakout (close beyond the noise band, on VWAP's side)
        └► gates (event/shock, stop size, room, volatility, breadth, spike guard)
             └► strike picker (gain/loss, delta band, rupee risk)
                  └► IDEA (alert-off) or ALERT (alert-on)  ──► Telegram + dashboard + journal
                       └► paper trade: backtest fill rule, E-trail exits, MOVE STOP / EXIT messages
 08:30  desk: our numbers + headlines ──► 8 Groq calls ──► verified brief ──► Telegram, scored daily
```

- **The same code decides live and in the backtest.** `strategy/pipeline.py:decide()` serves both. The parity test and
  `replay` prove it on recorded days.
- **No look-ahead.** Every derived row carries `available_at`, and a check at T uses only bars up to T−1 minute.
- **Option prices in the backtest are modelled** (Black-76 on a business-time clock, with VIX and a fitted skew),
  because no source keeps intraday option prices for expired contracts. The recorder now stores real
  ones, so future tests can price from real quotes.

---

## 6. Where things live

| Path | What |
|---|---|
| `quantdesk/` | All code: `cli.py` holds the commands |
| `quantdesk/recorder/`, `eod/`, `macro/`, `news/`, `history/` | Data collection (SP1) |
| `quantdesk/derived/` | The derived tables and as-of reads |
| `quantdesk/analysis/`, `vol/`, `pricing/` | Engines: VWAP proxy, bands, levels, breadth, HAR, the business clock, Black-76, the skew surface, quotes |
| `quantdesk/strategy/` | Day card, trigger, gates, strike picker, meta-model, exits, `decide()` (SP2) |
| `quantdesk/backtest/`, `validation/` | Backtester, dataset, registry, CPCV, statistics, verdict, pilots (SP2) |
| `quantdesk/live/` | Live engine, live source, journal, Telegram, dashboard, locks and kill-switches, the brief and scorecard, replay (SP3) |
| `quantdesk/desk/` | Analyst desk: `compact.py` (in use), `pilot.py` (the finished pilot) (SP4) |
| `research/` | `hypotheses.yaml` (every parameter, with its source), `VERDICT.md`, `pilots/*.md` (results), `experiments.csv`, `prior_looks.md` |
| `config/` | Settings, index membership history, event history, `frozen/` fitted models (clock, surface, shock) |
| `data/raw/` | Everything downloaded or recorded, by kind and date (never edited) |
| `data/derived/` | Rebuilt tables (`derive`) |
| `data/journal.sqlite` | Alerts and ideas, paper trades, your real trades, ratchets, events, state |
| `data/desk/` | Each day's desk brief (JSON) and `desk_calls.jsonl` |
| `logs/tasks/<job>.log` | Each scheduled job's output (UTF-16; open in Notepad) |
| `scripts/` | `schedule_tasks.ps1` (daily jobs), `run_detached.ps1` (long one-offs) |
| `docs/` | This handbook, runbook, decisions, roadmap, specs and plans |
| `tests/` | 546 tests |

---

## 7. What the research found

These are all zero-trial results: they count and measure, and never look at profit. The 13 trial slots are
unspent.

| Pilot | Finding | Consequence |
|---|---|---|
| CLOCK | Business-time weights fitted on 2019–22 (overnight share 0.35) | Frozen in `config/frozen/clock_v1.yaml` |
| P4 | No day-to-day autocorrelation (AR(1) −0.03, t −0.8) | The CTX trial doesn't run |
| P9 | VWAP proxy vs futures VWAP: the side agrees 96% of the time; the gap is 0.23 b, failing ≤ 0.1. The fallback is worse (0.44) | The proxy is kept; re-run at 40+ futures days |
| P1 / D2 | 4 eligible setups in 7 years at ₹400, 16 at ₹600, about 60 a year needed | **Verdict alert-off** (your choice, 22 Oct) |
| P10 | 0% / 2% chance that every validation gate could pass | Confirms D2 |
| Ideas, rupee caps removed | 38 setups in 7 years | Too few for a feed |
| Ideas, relaxed | 2,795 setups, about 82 days a year; 2026: 79 of 196 sessions | **The live feed setting** |
| Early pricing check | Model error 0.22 against the 0.15 pass mark (trade prices, no expiry days) | The option model needs work before any future backtest |
| Desk pilot | TradingAgents requests up to 20,515 tokens against Groq's 7,000 a minute | **Path B**, the compact desk |

---

## 8. Settings you might change

| What | Where |
|---|---|
| Idea filters (gates skipped, gain/loss minimum, no rupee caps) | `IDEAS_RELAXED` in `quantdesk/validation/pilots/run.py` |
| How strong the morning lean must be | `LEAN_AT` in `quantdesk/live/brief.py` (1.0) |
| Desk models and prompt size | `QUICK`, `DEEP`, `MAX_PROMPT_TOKENS` in `quantdesk/desk/compact.py` |
| Telegram shadow pushes | `push_shadow` in `quantdesk/live/engine.py` |
| Job times | `scripts/schedule_tasks.ps1`, then run it again |
| Every strategy parameter (bands, gates, exits, costs) | `research/hypotheses.yaml`. Changing it after a freeze is a new pre-registration. |

After any change: run the tests, then `replay --day <a recorded day>`, and commit.

---

## 9. When something goes wrong

| Symptom | Fix |
|---|---|
| No 09:20 brief | Open `logs\tasks\live.log`. `not started: the derived tables end on …` means last night's derive didn't run: run `derive`, then start `quantdesk-live` in Task Scheduler. `no signal dataset yet` means run `dataset` (detached). |
| No messages at all | Check the internet. Run `telegram-setup` again, which sends a test message. |
| The laptop restarted mid-day | Start `quantdesk-live` in Task Scheduler. It skips missed checks and resumes open paper trades. |
| No 08:30 desk brief | Open `logs\tasks\desk.log`. Groq may be down or over its limit; the trading feed isn't affected. |
| "UNVERIFIED" on the desk brief | The AI wrote a number that isn't in our data. Ignore that brief; it isn't scored. |
| Recorder gaps (`NIFTY: N minutes missing`) | Power or internet loss. The recorder holds a keep-awake request; a router without power still stops it. |
| A job still running from yesterday | Task Scheduler never starts it twice. Check its log; end it in Task Scheduler if it's stuck. |

More cases are in [runbook.md](runbook.md), "What to do when…".

---

## 10. Rules the project keeps

- **Never places trades.** Alerts and ideas only; you execute.
- **Secrets stay in `.env`.** They're never printed, logged (the Telegram token is masked in errors) or committed.
- **No look-ahead.** Anything computed at time T uses only data available at T.
- **Pre-registration.** A strategy is judged by rules fixed before its test. A new idea gets its own
  pre-registration, ticketed trials from the 13-slot registry, and the deflated-Sharpe, PBO and permutation gates. 2026 data
  counts as "touched", so the validation window is 2019–2025, with a clean forward record after that.
- **Alert-off unless validated.** Only an alert-on verdict turns ideas into "real" alerts.
- **Git:** commits carry only your identity, with no AI attribution. Push only when you decide to (`git push origin main`).

---

## 11. What's left, and what could come next

**Nothing is required.** The system runs as is. Optional next steps, most useful first:

1. **Read four Friday scorecards** before putting real money on ideas, and then only small size.
2. **Real pricing check (from about mid-November):** once 15+ sessions with 4 expiry days per index are
   recorded, run `pricecheck`. A future strategy test needs it to pass.
3. **Re-run P9** once the recorder has 40+ front-month futures days: `pilot P9`.
4. **A new strategy idea**, for example wider stops, longer holds or ITM options, which the D2 finding points to. Brainstorm
   it, pre-register it in a new spec, and test it on the real recorded quotes. It's a separate project and uses no
   existing slots.
5. **Optional extras:**
   - the desk's Ollama fallback for Groq outages
   - Bank Nifty recording (monthly options only since Nov 2024)
   - labelling `data/labels/pilot8_headlines.csv` to grade the news classifier

---

## 12. For a future AI session: start here

Paste this to a new session in the project folder:

> Read `docs/HANDBOOK.md`, then `docs/decisions.md` (the newest entries are at the end). Run
> `.venv\Scripts\python -m pytest -q` and confirm everything passes. The project never places trades, never prints or
> commits secrets from `.env`, and commits without AI attribution. Push only when I say so. Long jobs run via
> `scripts\run_detached.ps1`. Write the failing test before changing code, and record every design decision in
> `docs/decisions.md`. Then help me with: …

---

## Glossary

| Term | Meaning |
|---|---|
| **H1** | The trigger: the close leaves the gap-adjusted noise band (the 14-day average move from the open at that time of day), on the same side as VWAP |
| **b** | The structural stop distance in index points: the tighter of the band edge and VWAP |
| **R** | Result in units of the planned risk; mean net R per trade is the scoreboard |
| **VWAP proxy** | The index's VWAP weighted by its member stocks' traded value; the index has no volume of its own |
| **HAR** | The volatility forecast behind the "expected range" |
| **E-trail / X1** | The exit: trail the stop 1.5 b behind the best price once +1 b is reached, never below VWAP |
| **Shadow / idea / live** | Shadow means logged, not acted on. Idea means sent to you to judge and size. Live means a validated alert (needs alert-on). |
| **D2** | The checkpoint that found too few setups; you chose alert-off |
| **Desk** | The AI analyst brief; explanation only, never a vote on trades |
| **Pre-registration** | Parameters and tests fixed before looking at results (`research/hypotheses.yaml`) |
