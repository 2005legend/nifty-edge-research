"""The owner's one-time look at the idea feed on history (owner's choice, 26 Oct 2026).

It runs the feed exactly as the live engine does: the same H1 breakout, the relaxed gates (`IDEAS_RELAXED`),
the same strike picker (nearest expiry first, delta near 0.40, no rupee caps), one open idea per index at a
time, the backtest's fill rule (ask + 1 tick at the bar T + delay - 1, chase cap, 5-minute lapse) and the
same exits. Nothing is tuned.

**This is a look at profit, not a registry trial.** It is recorded in `research/prior_looks.md` and raises N for
any later deflated Sharpe. Its option prices are modelled; the early pricing check put the model at 0.22 median
error against R17's 0.15, so the rupee figures carry that uncertainty. The forward scorecards on real prices
decide.
"""

import math
from datetime import date, timedelta

import numpy as np
import pandas as pd

from quantdesk.backtest.fills import fill
from quantdesk.strategy.exits import OpenTrade, simulate_exit
from quantdesk.strategy.pipeline import _warm, decide, family_scores
from quantdesk.strategy.timeline import check_times, timeline_block
from quantdesk.strategy.trigger import h1
from quantdesk.validation.hypotheses import param

TICK = 0.05


def idea_backtest(source, days: list[date], indices: dict[str, date], cfg, model, h_idea: dict, h: dict, today: date,
                  progress=None) -> pd.DataFrame:
    delay = int(param(h, "backtest.primary_delay_min"))
    record = getattr(source, "record_signal", None)
    rows = []
    for day in days:
        for index, start in indices.items():
            if day < start:
                continue
            try:
                ctx = source.context(index, day)
            except (KeyError, ValueError):
                continue
            if ctx.expiry_1 is None or ctx.session_kind != "regular":
                continue
            frame = source.frame(ctx)
            helpers = source.helpers(ctx, frame)
            busy_until = None
            for at in check_times(day, ctx.is_expiry_day, h):
                if timeline_block(ctx, at, h):
                    continue
                past = frame[frame["ts"] <= at - timedelta(minutes=1)]
                if past.empty:
                    continue
                sig = h1(past, at, ctx, h)
                if sig is None:
                    continue
                if record and _warm(ctx):                    # the z references, exactly as the dataset builds them
                    record(day, family_scores(ctx, past, sig, h)["raw"])
                if busy_until is not None and at <= busy_until:
                    continue
                d = decide(ctx, frame, at, cfg, model, helpers, h_idea, today, idea=True)
                if d.alert is None:
                    continue
                c = d.alert.choice
                res = fill(d.signal, c, frame, helpers.quotes, delay, ctx, h)
                row = {"day": day, "index": index, "at": at, "side": d.signal.side, "expiry": c.expiry,
                       "strike": c.strike, "kind": c.kind, "lot": c.lot, "p": d.p, "p_be": c.p_be,
                       "planned_loss": c.loss, "planned_gain": c.gain, "status": res.status}
                if res.status != "filled":
                    rows.append(row)
                    continue
                trigger = res.premium - c.loss / c.lot
                limit = trigger - max(0.10 * trigger, 5 * TICK)
                out = simulate_exit(OpenTrade(d.signal, c, res.at, res.premium, trigger, limit), frame, helpers.quotes,
                                    ctx, cfg.exit_policy, h_idea, today)
                rows.append({**row, "entry_at": res.at, "entry_premium": res.premium, "exit_at": out.exit_at,
                             "exit_premium": out.exit_premium, "reason": out.reason, "pnl": out.pnl,
                             "r": out.pnl / c.loss if c.loss else math.nan,
                             "roi": out.pnl / (res.premium * c.lot)})
                busy_until = out.exit_at
        if progress:
            progress(day)
    return pd.DataFrame(rows)


def _stats(rows: pd.DataFrame) -> dict:
    filled = rows[rows["status"] == "filled"]
    r = filled["r"].astype(float)
    n = len(filled)
    sd = float(r.std(ddof=1)) if n > 1 else math.nan
    return {"ideas": int(len(rows)), "filled": n,
            "win_rate": float((filled["pnl"] > 0).mean()) if n else math.nan,
            "mean_r": float(r.mean()) if n else math.nan, "median_r": float(r.median()) if n else math.nan,
            "t": float(r.mean() / (sd / math.sqrt(n))) if n > 1 and sd > 0 else math.nan,
            "mean_roi_pct": float(100 * filled["roi"].mean()) if n else math.nan,
            "mean_rs_per_lot": float(filled["pnl"].mean()) if n else math.nan}


def summarise(rows: pd.DataFrame) -> dict:
    years = pd.to_datetime(rows["day"]).dt.year
    out = {"all": _stats(rows), "2019-2025": _stats(rows[years <= 2025]), "2026": _stats(rows[years >= 2026])}
    for y in sorted(years.unique()):
        out[str(y)] = _stats(rows[years == y])
    for index in sorted(rows["index"].unique()):
        out[index] = _stats(rows[rows["index"] == index])
    return out


def report(rows: pd.DataFrame, data_hash: str, written: str) -> str:
    s = summarise(rows)
    keys = ["all", "2019-2025", "2026"] + [k for k in s if k.isdigit() and k != "2026"] + \
        [k for k in ("NIFTY", "SENSEX") if k in s]
    fmt = lambda v, d=2: "-" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{v:.{d}f}"  # noqa: E731
    lines = ["# Idea feed on history (one untuned look; not a registry trial)", "",
             f"- data_hash `{data_hash}`, written {written}",
             "- Settings: `IDEAS_RELAXED`, exits of the live configuration, fill at delay 1, one idea per index at a time",
             "- Option prices are modelled (early pricing check: 0.22 median error vs 0.15 target)", "",
             "| period | ideas | filled | win rate | mean R | median R | t | mean return on premium % | mean Rs per lot |",
             "|---|---|---|---|---|---|---|---|---|"]
    for k in keys:
        v = s[k]
        lines.append(f"| {k} | {v['ideas']} | {v['filled']} | {fmt(v['win_rate'])} | {fmt(v['mean_r'])} | "
                     f"{fmt(v['median_r'])} | {fmt(v['t'])} | {fmt(v['mean_roi_pct'], 1)} | {fmt(v['mean_rs_per_lot'], 0)} |")
    filled = rows[rows["status"] == "filled"]
    if len(filled):
        lines += ["", "## Exits", "", "| reason | count | mean R |", "|---|---|---|"]
        for reason, g in filled.groupby("reason"):
            lines.append(f"| {reason} | {len(g)} | {fmt(float(g['r'].mean()))} |")
    lines += ["", "R = result / the strike's planned loss at the index stop (after charges). A mean R above 0 with t "
              "above 2 in both periods would be worth confirming on the forward scorecards; anything else says the "
              "ideas do not pay as built.", ""]
    return "\n".join(lines)
