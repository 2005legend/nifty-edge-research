# quantdesk runbook (SP1 data foundation)

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
| 18:35 | `python -m quantdesk eod` | NSE/BSE bhavcopy, participant OI, FII/DII, VIX daily, Nifty 50 list. Retries hourly until 23:00. |
| 18:35 | `python -m quantdesk macro` | Evening macro pull |
| any time | `python -m quantdesk status [--day YYYY-MM-DD]` | Health summary for a day |

## Windows Task Scheduler

One script registers all six jobs for your Windows user:

```
powershell -ExecutionPolicy Bypass -File scripts\schedule_tasks.ps1
```

Run it again after changing a time; it updates the jobs in place. `-Remove` deletes them all. The jobs are named `quantdesk-news`, `-macro-morning`, `-record`, `-macro-intraday`, `-eod` and `-macro-evening`. Each one:
- runs hidden while you are logged in, so there is no window to close by accident
- appends its output to `logs	asks\<job>.log`
- is never started twice while it is still running
- starts later if the PC was off at its time, and keeps running on battery

`record` and `eod` may also wake the PC from sleep. The news poller runs continuously, so its job has no time limit. Don't also run `python -m quantdesk news` in a terminal, or every headline is stored twice.

The PC must be on during market hours. Turn sleep off while plugged in.

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
| `macro india_gsec10y: failed` / `nifty_fundamentals: failed` | Their URLs are not set up yet (open item) | Ignore until configured |
| `news feed stale: X` | Feed X published nothing for 24 h | Fine on holidays; otherwise check the URL in `config/news_feeds.yaml` |
| `feed stale periods: N` | The live feed stopped for 30+ seconds N times | The recorder reconnects by itself. Check your internet if N is large. |
| `NIFTY: N minutes missing` | Recording started late or the PC slept | Check the PC sleep settings |
| `record already running (pid N) - nothing to do` | A recorder is already running (often the scheduled one) | Nothing. Leave that one running |

## Notes

- **Expiry dates come from Angel One's instrument master.** Holiday shifts (e.g. Nifty expiring Monday 9 Nov 2026 because 10 Nov is a holiday) are handled automatically.
- **Holidays live in `config/events.yaml`**, taken from NSE's holiday API. Refresh the file each December for the next year, and every entry needs a `source_url`.
- **Data lives in `data/`** (git-ignored):
  - `data/raw/` is never edited.
  - `data/reports/` holds the daily reports.
