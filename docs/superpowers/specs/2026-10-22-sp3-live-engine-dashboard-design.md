# SP3 design: live engine, alerts, paper trading, journal, dashboard, replay

**Date:** 22 Oct 2026. **Parent spec:** `2026-10-06-nifty-sensex-options-signal-system-design.md` §7.

The owner delegated the design choices ("the most reliable long-term design"). Phone alerts go through a Telegram bot (owner, 22 Oct 2026). Rulings S1–S12 below are recorded in `docs/decisions.md`.

## What SP3 is for

During market hours, SP3 runs the **same** `decide()` the backtest ran, on what the recorder captures, and does five things with the result:
1. Tells the owner what to do: entry, stop moves and exits, on the phone and the laptop.
2. Paper-trades every alert at the live ask + 1 tick and exits at the live bid.
3. Journals everything: alerts, the owner's took/skipped choice, real fills, overrides, unlock reasons.
4. Enforces the locks and kill-switches of spec §2 and §7.
5. Shows it all on a local dashboard at `127.0.0.1:8000`.

It never places an order (`test_no_order_methods_exist` still holds).

## Rulings

| # | Ruling |
|---|---|
| **S1** | **One live process, `python -m quantdesk live`,** started by Task Scheduler at 09:10 on weekdays and finished by 15:35. It runs the decision loop, the paper-trade manager, the notifier and the dashboard server (uvicorn in a thread, bound to 127.0.0.1). `python -m quantdesk dashboard` serves the journal and research views outside market hours. |
| **S2** | **Mode comes from the verdict.**<br>• **alert-on** (`research/VERDICT.md`): alerts go to the phone and paper trades open.<br>• **alert-off:** *shadow mode*. The same decisions are logged as shadow setups, which feed the clean forward holdout (D4), and are shown on the dashboard marked *shadow*. Nothing is pushed.<br>• **Configuration in shadow mode:** the last accepted trial, else B0, with its model fitted on all labelled signals up to the last session. |
| **S3** | **Parity by construction.** History comes from `DayLoader` (derived tables up to yesterday). Today's frame is built from the recorder's own `bars`, with breadth from `member_breadth` on the recorder's stock bars: the same functions as the derived tables.<br>• **Live quotes:** `RecordedQuotes`, the real bid/ask from `option_snapshots`.<br>• **Parity test:** `ModelQuotes` on recorded bars, so live and backtest decisions can be compared like for like. |
| **S4** | **Check timing.** A check at T runs once the recorder has flushed the bar stamped T − 1, polled every 5 seconds, giving up 60 seconds after T. A check whose bar never arrives is logged as `data_late` and skipped. |
| **S5** | **The journal is SQLite** at `data/journal.sqlite`, append-only apart from the owner's took/skipped/fill fields. Tables: `alerts`, `paper_trades`, `real_trades`, `ratchets`, `events` (locks, unlocks with reasons, shadow pauses, kill-switch firings, overrides), `state`. |
| **S6** | **Telegram messages:**<br>• the "setup forming" pre-alert, 5 minutes before a likely trigger, only when price is within 0.25σ(τ) of the band on the VWAP side<br>• the alert<br>• "move stop to ₹X / index Y"<br>• "exit now (reason)"<br>• the daily summary<br><br>Failed sends are retried 3 times and logged; a notifier failure never stops the engine. |
| **S7** | **Paper trades replay `simulate_exit` incrementally.** Each minute, the exit simulation is re-run on the frame so far. A new ratchet in its schedule becomes a stop-move message. An exit decision becomes an exit message and closes the paper trade at the live bid 2 minutes later, the same R2 rule as the backtest. |
| **S8** | **Locks.** These are recomputed from the journal before every alert:<br>• **Caps:** 1 trade a day, 3 a week, the monthly share of 100 trade-days a year.<br>• **Loss limits:** a ₹400 loss for the day, or a ₹1,000 loss for the week.<br><br>A lock suppresses alerts; it never suppresses exit messages for an open trade. An unlock needs a typed reason, stored in `events`. A *shadow pause* (D6) turns alerts into paper trades until the end of the week. |
| **S9** | **Kill-switches.** These are checked after each closed trade:<br>• **SPRT on mean net R:** a Wald test between H0, the in-control level, and H1 = 0. The variance is the validated per-trade variance. α = 0.10 and β = 0.20 (research SFV:345).<br>• **CUSUM on mean net R:** in-control level = validated − 0.5 × (validated − breakeven). Its threshold is fixed from the validated trades by bootstrap, targeting 1 false alarm per 250 trades.<br>• **Capital floor:** capital ≤ ₹7,000.<br>• **Cost check:** live costs more than 30% above the model.<br><br>A firing switches the mode to shadow and logs the reason; only the owner can lift it, with a typed reason. |
| **S10** | **Monthly calibration check:** observed against predicted probability on all labelled setups (shadow included), shown in the Journal tab. |
| **S11** | **The dashboard** is FastAPI plus one static page (HTML, JS, TradingView Lightweight Charts 4.1.3 from unpkg, pinned) with three tabs, Today, Journal and Research, refreshed by a WebSocket push.<br>• **Phase-one charts:** price, VWAP, bands and levels.<br>• **Not in phase one:** oscillator panes and the display-only indicators of spec §5A.1. They come later, because they never affect a decision. |
| **S12** | **Replay.** `python -m quantdesk replay --day D` runs the live engine on a recorded day with a simulated clock and writes its alerts. The parity test asserts that they equal `decide()` on the same bars with the same quotes source. |

## Data flow

```
recorder (bars, option_snapshots, option_meta) ─┐
derived tables up to yesterday ─────────────────┼─► LiveDaySource ─► decide() ─► alert/shadow ─► journal ─► dashboard
frozen clock, surface, shock, trial model ──────┘                       │                     └──► Telegram
                                                                        └─► paper trade ─► incremental exits ─► messages
```

## Owner steps

1. Create a Telegram bot with @BotFather. Put `TELEGRAM_BOT_TOKEN` in `.env`. Send the bot one message, then run `python -m quantdesk telegram-setup`, which finds `TELEGRAM_CHAT_ID` and prints it for `.env`.
2. Run `scripts\schedule_tasks.ps1` again to add the `live` job at 09:10.
3. Open `http://127.0.0.1:8000` during market hours.

## Testing

All of these run offline:
- simulated clock and fake recorder parts
- fake Telegram HTTP
- the FastAPI `TestClient`
- the parity test on a synthetic recorded day
