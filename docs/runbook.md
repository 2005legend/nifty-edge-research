# quantdesk runbook (SP1 data foundation, SP3 live alerts)

How to run the data foundation every day, and what to do when something goes wrong.

## One-time setup

1. **Create `.env`.** Copy `.env.example` to `.env` in the project folder and fill in each value after the `=`:
   - `ANGEL_API_KEY`: from your SmartAPI app at smartapi.angelbroking.com
   - `ANGEL_CLIENT_CODE`, `ANGEL_PIN`: your Angel One login
   - `ANGEL_TOTP_SECRET`: the secret shown when you enable TOTP for SmartAPI
   - `FRED_API_KEY`: free, from fredaccount.stlouisfed.org/apikeys
   - `GROQ_API_KEY`: from console.groq.com/keys (used later by the analyst desk)

   `.env` is git-ignored, so it never goes to GitHub. Never paste these values into a chat.
2. **Check the login:** `.venv\Scripts\python -m quantdesk login-check`. It should print `session ok: <your name>`.
3. **Run the live checks:** `.venv\Scripts\python -m pytest -m live -v`. The websocket check only runs during market hours.
4. **One-off history downloads.** These take hours and can be stopped and resumed safely.
   - `.venv\Scripts\python -m quantdesk backfill --what history`: 1-minute Nifty, Sensex, VIX and Nifty 50 stocks from 2019
   - `.venv\Scripts\python -m quantdesk backfill --what bhavcopy`: NSE and BSE F&O end-of-day files from 2019

## Daily schedule (Monday to Friday)

| Time (IST) | Command | What it does |
|---|---|---|
| 06:55 | `python -m quantdesk news` | News poller: every 5 minutes 07:00–19:30 on trading days, hourly otherwise. Runs continuously. |
| 07:30 | `python -m quantdesk macro` | Global and macro daily pull: yields, USD/INR, Brent, US/Asian indices, India CPI/GDP/rates, economic calendar |
| 08:55 | `python -m quantdesk record` | Live recorder 09:15–15:30. Writes 1-minute data and the health report. Exits by itself on holidays. |
| 08:58 | `python -m quantdesk macro --intraday` | 5-minute global prices during 09:00–15:30 |
| 09:10 | `python -m quantdesk live` | Alerts, paper trades, Telegram and the dashboard at http://127.0.0.1:8000, until 15:35 (see "Live alerts and the dashboard") |
| 18:35 | `python -m quantdesk eod` | NSE/BSE bhavcopy, participant OI, FII/DII, VIX daily, Nifty 50 list. Retries hourly until 23:00. |
| 18:35 | `python -m quantdesk macro` | Evening macro pull |
| any time | `python -m quantdesk status [--day YYYY-MM-DD]` | Health summary for a day |

## Windows Task Scheduler

One script registers all the daily jobs for your Windows user:

```
powershell -ExecutionPolicy Bypass -File scripts\schedule_tasks.ps1
```

Run it again after changing a time; it updates the jobs in place. `-Remove` deletes them all. The jobs are named `quantdesk-news`, `-macro-morning`, `-record`, `-macro-intraday`, `-live`, `-eod`, `-macro-evening`, `-backfill-history` and `-desk-pilot`. Each one:
- runs hidden while you are logged in, so there is no window to close by accident
- appends its output to `logs\tasks\<job>.log`
- is never started twice while it is still running
- starts later if the PC was off at its time, and keeps running on battery

`record`, `live` and `eod` may also wake the PC from sleep. The news poller runs continuously, so its job has no time limit. Don't also run `python -m quantdesk news` in a terminal, or every headline is stored twice.

The recorder asks Windows to stay awake while it runs, as a video player does, so neither the plugged-in nor the battery sleep setting stops it. The screen may still turn off. On 21 Oct 2026 a power cut put the laptop on battery, which sleeps after 15 idle minutes, and 73 minutes were lost. The laptop must still be on, with internet: if the router loses power in a cut, the feed stops anyway.

### Long one-off jobs (backfills)

Don't run long jobs in a terminal inside an app such as the Claude desktop app or VS Code: they die when that app closes or restarts, which happened on 21 Oct 2026. Run them as one-off scheduled jobs instead:

```
powershell -ExecutionPolicy Bypass -File scripts\run_detached.ps1 -Name backfill-history -Run "-m quantdesk backfill --what history"
powershell -ExecutionPolicy Bypass -File scripts\run_detached.ps1 -Name backfill-bhavcopy -Run "-m quantdesk backfill --what bhavcopy"
powershell -ExecutionPolicy Bypass -File scripts\run_detached.ps1 -Name backfill-fundamentals -Run "-m quantdesk backfill --what fundamentals"
```

Each job is hidden, logs to `logs\tasks\<Name>.log` and resumes where it stopped if run again. Check on it in Task Scheduler (`quantdesk-oneoff-*`) or in its log.

## Live alerts and the dashboard (SP3)

**Telegram, once.** Open your bot in Telegram and send it any message ("hi"). Then run:

```
.venv\Scripts\python -m quantdesk telegram-setup
```

It saves `TELEGRAM_CHAT_ID` in `.env` and sends a test message. It prints neither the token nor the chat id. Until it has run, the live process works but sends nothing to the phone.

**Every trading day.** The `quantdesk-live` job starts `python -m quantdesk live` at 09:10 and stops at 15:35. It needs the signal dataset (`python -m quantdesk dataset`). Without it, the job logs `not_started` and exits, so it never logs shadow setups from an unfitted model.

The dashboard runs at http://127.0.0.1:8000 while the job is running. Outside market hours, run `python -m quantdesk dashboard` to see it.

**Mode.** The mode comes from `research/VERDICT.md`:
- **alert-on (live):** alerts go to the phone and the dashboard.
- **alert-off, or no verdict yet (shadow):** the same decisions are journalled and shown marked *shadow*, and nothing is pushed. These shadow setups are the clean forward holdout, so don't trade them.

**Messages** (the same text on the phone and the dashboard):
- **ALERT:** buy the named option with a limit order, up to the stated price. It lapses after 5 minutes. Place the SL-limit backstop at the stated trigger and limit as soon as you are filled.
- **MOVE STOP:** move your stop to the new level. At most one every 10 minutes.
- **EXIT NOW:** sell at market. This replaces your old 12:00–12:30 hold-or-exit decision. If you override it, log the override on the dashboard.
- **KILL SWITCH:** new alerts are shadow only from now on. Open trades still get their exit messages.

**After an alert,** press *took it* or *skipped* on the Today tab. If you took it, type your fill price. When you exit, log the exit. The Journal tab compares your results with the paper trade.

**Locks.** The system stops alerting after any of these:
- the trade caps: 1 a day, 3 a week, or the month's share of 100 a year
- a ₹400 loss in a day, or ₹1,000 in a week
- a kill-switch firing: SPRT or CUSUM on mean net R, capital at or below ₹7,000, or costs more than 30% above the model

A lock lifts only with a typed reason of at least 10 characters, which is journalled. *Shadow pause* switches alerts to shadow for the rest of the week.

**Replay a recorded day:**

```
.venv\Scripts\python -m quantdesk replay --day 2026-10-22
```

This runs that day through the live engine and checks every decision against the backtest's `decide()`. The scratch journal goes to `data\replay\`.

## Reading the health report

`python -m quantdesk status` shows:
- `minutes_recorded` for Nifty, Sensex and VIX. Expect 360 on a full trading day (09:15–15:14; the index has no 1-minute bars during the 15:15 closing auction, from 3 Aug 2026), 0 on holidays.
- `problems`: a plain list. Empty is good.

## What to do when…

| Message | Meaning | Action |
|---|---|---|
| `recording holiday` | Not a trading day (weekend or listed holiday) | Nothing |
| `Missing secret(s): …` | `.env` is missing values | Fill them in |
| `eod nse_fo: not_published` | NSE hadn't published by 23:00 | Run `python -m quantdesk eod --day YYYY-MM-DD` the next morning |
| `eod …: bad_download` | NSE/BSE returned a block page | Wait and re-run. NSE sometimes blocks for a while. |
| `macro dgs10: missing_key` | No `FRED_API_KEY` in `.env` | Add the key |
| `macro india_gsec10y_price: failed` / `nifty_fundamentals: failed` | NSE's daily index file could not be fetched (block page or network) | Re-run `python -m quantdesk macro` later |
| `news feed stale: X` | Feed X published nothing for 24 h | Fine on holidays; otherwise check the URL in `config/news_feeds.yaml` |
| `feed stale periods: N` | The live feed stopped for 30+ seconds N times | The recorder reconnects by itself. Check your internet if N is large. |
| `NIFTY: N minutes missing` | Recording started late, or the PC or internet was off | Check `logs\tasks\record.log` for when it started and stopped |
| `record already running (pid N) - nothing to do` | A recorder is already running (often the scheduled one) | Nothing. Leave that one running |
| `live` `not started: no signal dataset yet` | The model has nothing to train on | Run `python -m quantdesk dataset` (long: start it with `run_detached.ps1`) |
| `live` `not started: the derived tables end on …` | Last night's derive didn't run or failed | Check `logs\tasks\derive.log`, run `python -m quantdesk derive`, then start `quantdesk-live` again in Task Scheduler |
| The laptop restarted during market hours | The live process stopped with it | Start `quantdesk-live` again in Task Scheduler. It skips the checks it missed (journalled as `missed`) and picks up open paper trades, so stop-move and exit messages carry on. |
| `paper_unfilled` in the journal | The paper fill lapsed (the index ran past the chase cap) or its bar never arrived | Nothing. The alert stays journalled. |

## Notes

- **Expiry dates come from Angel One's instrument master.** Holiday shifts (e.g. Nifty expiring Monday 9 Nov 2026 because 10 Nov is a holiday) are handled automatically.
- **Holidays live in `config/events.yaml`**, taken from NSE's holiday API. Refresh the file each December for the next year, and every entry needs a `source_url`.
- **Data lives in `data/`** (git-ignored):
  - `data/raw/` is never edited.
  - `data/reports/` holds the daily reports.
