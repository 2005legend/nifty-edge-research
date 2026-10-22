"""Locks and kill-switches (spec §2, §7; SP3 design S8-S9).

**Locks** are recomputed from the journal before each alert:
- 1 trade a day, 3 a week, and the month's share of 100 trade-days a year
- a ₹400 loss in the day, or ₹1,000 in the week

Each lock can be lifted only by an `unlock` event whose detail is "lock|period|reason", so the reason is kept.

**Kill-switches** fire on:
- an SPRT "stop" on mean net R
- a CUSUM alarm on mean net R
- capital at or below ₹7,000
- live costs more than 30% above the model

A firing turns the system to shadow mode until the owner lifts it with a typed reason.
"""

import math
from datetime import date, timedelta

import numpy as np
import pandas as pd

from quantdesk.validation.hypotheses import param

MODEL_COSTS = 57.0     # ₹ per round trip at today's charges (costs.py, decisions.md 21 Oct 2026)


LIVE_PAPER = ("select p.* from paper_trades p join alerts a on a.id = p.alert_id "
              "where a.mode = 'live' and p.exit_at is not null order by p.exit_at")


def book(journal) -> pd.DataFrame:
    """One row per closed trade from a live alert: the real result where the owner logged one, else the paper
    result. Shadow and suppressed setups are paper only, never money, so no lock or kill-switch counts them."""
    paper = journal._query(LIVE_PAPER)
    if paper.empty:
        return pd.DataFrame(columns=["alert_id", "day", "pnl", "r", "paper_pnl"])
    paper = paper.assign(day=paper["entry_at"].str[:10], paper_pnl=paper["pnl"])
    real = journal.closed_trades("real")
    if len(real):
        paper = paper.merge(real[["alert_id", "pnl"]].rename(columns={"pnl": "real_pnl"}), on="alert_id", how="left")
        paper["pnl"] = paper["real_pnl"].fillna(paper["pnl"])
        paper["r"] = paper["pnl"] / param_risk()
    return paper[["alert_id", "day", "pnl", "r", "paper_pnl"]]


def param_risk() -> float:
    return 400.0


def _entries(journal) -> pd.DataFrame:
    trades = journal._query("select p.entry_at from paper_trades p join alerts a on a.id = p.alert_id "
                            "where a.mode = 'live'")
    return trades.assign(day=trades["entry_at"].str[:10])


def _unlocked(journal, kind: str, period: str) -> bool:
    events = journal.events()
    if events.empty:
        return False
    wanted = f"{kind}|{period}|"
    return bool(((events["kind"] == "unlock") & events["detail"].str.startswith(wanted)).any())


def lock_period(kind: str, day: date) -> str:
    """The period an unlock of `kind` names ("lock|period|reason"), as `locks` checks it."""
    if kind in ("per_week", "week_loss"):
        return (day - timedelta(days=day.weekday())).isoformat()
    return f"{day:%Y-%m}" if kind == "per_month" else day.isoformat()


def locks(journal, day: date, sessions: list[date], h: dict, pending: int = 0) -> list[str]:
    """`pending`: live alerts whose paper fill is not known yet. Each holds a place under every cap until it
    fills or lapses, so two indices signalling in the same minute cannot both alert."""
    entries = _entries(journal)
    week_start = day - timedelta(days=day.weekday())
    days = pd.to_datetime(entries["day"]).dt.date if len(entries) else pd.Series(dtype=object)
    today = (int((days == day).sum()) if len(entries) else 0) + pending
    week = (int(((days >= week_start) & (days <= day)).sum()) if len(entries) else 0) + pending
    month = (int(days.map(lambda d: (d.year, d.month) == (day.year, day.month)).sum()) if len(entries) else 0) + pending
    in_month = sum(1 for d in sessions if (d.year, d.month) == (day.year, day.month))
    in_year = sum(1 for d in sessions if d.year == day.year) or 1
    quota = math.ceil(param(h, "caps.per_year") * in_month / in_year)
    trades = book(journal)
    tdays = pd.to_datetime(trades["day"]).dt.date if len(trades) else pd.Series(dtype=object)
    pnl_day = float(trades.loc[tdays == day, "pnl"].sum()) if len(trades) else 0.0
    pnl_week = float(trades.loc[(tdays >= week_start) & (tdays <= day), "pnl"].sum()) if len(trades) else 0.0
    found = []
    checks = [("per_day", today >= param(h, "caps.per_day"), day.isoformat()),
              ("per_week", week >= param(h, "caps.per_week"), week_start.isoformat()),
              ("per_month", month >= quota, f"{day:%Y-%m}"),
              ("day_loss", pnl_day <= -param(h, "caps.loss_day"), day.isoformat()),
              ("week_loss", pnl_week <= -param(h, "caps.loss_week"), week_start.isoformat())]
    for kind, hit, period in checks:
        if hit and not _unlocked(journal, kind, period):
            found.append(kind)
    return found


def effective_mode(journal, day: date, verdict_mode: str) -> str:
    """Live only when the verdict is alert-on, no kill-switch is standing and no shadow pause covers `day`."""
    if verdict_mode == "idea":                     # the owner's idea feed: never locked, never live alerts
        return "idea"
    if verdict_mode != "live" or journal.get_state("kill_switch"):
        return "shadow"
    pause = journal.get_state("shadow_pause_until")
    return "shadow" if pause and day.isoformat() <= pause else "live"


def sprt(r, mu0: float, mu1: float, sigma: float, alpha: float, beta: float) -> str:
    """Wald's SPRT between H0: mean R = mu0 (the validated, in-control level) and H1: mean R = mu1 (no edge)."""
    upper, lower = math.log((1 - beta) / alpha), math.log(beta / (1 - alpha))
    llr = 0.0
    for x in np.asarray(r, dtype=float):
        llr += ((x - mu0) ** 2 - (x - mu1) ** 2) / (2 * sigma * sigma)
        if llr >= upper:
            return "stop"
        if llr <= lower:
            return "go"
    return "continue"


def cusum_alarm(r, target: float, k: float, h: float) -> bool:
    """One-sided CUSUM for mean R falling below `target`, with slack k and threshold h."""
    s = 0.0
    for x in np.asarray(r, dtype=float):
        s = max(0.0, s + (target - x) - k)
        if s > h:
            return True
    return False


def kill_switches(journal, params: dict, h: dict) -> list[str]:
    """`params`: mu0 (validated mean R), breakeven, sigma (validated per-trade sd), cusum_h."""
    trades = book(journal)
    reasons = []
    capital = param(h, "account.capital") + float(trades["pnl"].sum()) if len(trades) else param(h, "account.capital")
    if capital <= param(h, "account.capital_floor"):
        reasons.append("capital_floor")
    if len(trades):
        r = trades["r"].to_numpy(dtype=float)
        if sprt(r, params["mu0"], 0.0, params["sigma"], 0.10, 0.20) == "stop":
            reasons.append("sprt")
        target = params["mu0"] - 0.5 * (params["mu0"] - params["breakeven"])
        if cusum_alarm(r, target, 0.5 * (params["mu0"] - target), params["cusum_h"]):
            reasons.append("cusum")
        real = trades.dropna(subset=["paper_pnl"])
        slip = (real["paper_pnl"] - real["pnl"]).mean() if len(real) else 0.0
        if slip > 0.30 * MODEL_COSTS:
            reasons.append("costs")
    return reasons
