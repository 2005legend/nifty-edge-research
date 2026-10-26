# InstaBox pilot (before moving anything)

The laptop stays the primary system until this pilot passes. Nothing here uses your credentials.

## Why a pilot

InstaBox's free machine (4 vCPU, 8 GB, 20 GB) is big enough; the system uses 4.7 GB of data. But three things decide
whether it can run a trading recorder, and the docs don't answer them:

1. **Idle pause.** Free machines pause after 30 idle minutes; a paused machine runs nothing. A visit to its public URL
   wakes it, so a free web-cron service can keep it up. Does that hold through a whole market day?
2. **Location.** Does NSE serve its files to InstaBox's address? NSE often blocks cloud servers, which would break the
   evening downloads.
3. **Angel One** must be reachable from there.

## Steps

1. On your laptop: `npx instabox@latest sh` (signs you in and opens a machine; your call, under their terms).
2. On the machine:
   ```
   git clone https://github.com/2005legend/nifty-edge-research.git && cd nifty-edge-research
   bash deploy/instabox/probe.sh
   ```
3. Expose port 8080 as a public URL (InstaBox dashboard or CLI), and open it once: it should say `ok <time>`.
4. At cron-job.org (free), add a job that opens that URL **every 10 minutes**, all day.
5. Disconnect. The next day, on the machine: `python3 deploy/instabox/heartbeat.py --report`.

## Pass / fail

| Check | Pass |
|---|---|
| NSE bhavcopy and Nifty 50 list | 200 (or 404 for a holiday date), never 403 / 000 |
| BSE bhavcopy, Angel One, Telegram, Groq | anything but 000 |
| Heartbeat report | "no pauses longer than 2 minutes" across 09:00-16:00 and the evening |

Paste the probe output and the report to Claude. If everything passes, the move is: Python environment, a copy of
`data/` (4.7 GB), the scheduled jobs as a Linux timetable, and **you** copy `.env` yourself (it holds your Angel One
PIN and TOTP secret, which can log into your account; never paste it into a chat). Run both side by side for a week
before switching off the laptop.
