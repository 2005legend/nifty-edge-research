"""The local dashboard (spec §7, SP3 design S11): FastAPI on 127.0.0.1:8000, one page, three tabs.

- **Today:** mode and locks, the day card, today's alerts with took/skipped/fill, open paper trades and charts.
- **Journal:** paper and real results, mean net R with its 95% band, average win/loss, win rate (shown, not
  targeted), how often the owner followed the system, and the premium-turnover ledger.
- **Research:** pilot reports, the verdict, the experiment registry, pre-flight and the pricing check.

The page polls every 5 seconds and a WebSocket nudges it on new journal rows. Owner actions are journalled. An
unlock needs a reason of at least 10 characters (spec §7 locks).
"""

import asyncio
import json
import math
from datetime import date
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from quantdesk.costs import round_trip
from quantdesk.live.monitor import effective_mode, lock_period, locks

STATIC = Path(__file__).parent / "static"
EXCHANGE = {"NIFTY": "NSE", "SENSEX": "BSE"}
TURNOVER_BUDGET = 1_000_000


class StatusIn(BaseModel):
    status: Literal["took", "skipped"]


class FillIn(BaseModel):
    premium: float = Field(gt=0)


class ExitIn(BaseModel):
    premium: float = Field(gt=0)
    pnl: float | None = None            # left out: the server costs it at today's charges
    notes: str = ""


class UnlockIn(BaseModel):
    lock: Literal["per_day", "per_week", "per_month", "day_loss", "week_loss", "kill_switch"]
    period: str
    reason: str = Field(min_length=10)


class PauseIn(BaseModel):
    reason: str = Field(min_length=10)


def _records(frame: pd.DataFrame) -> list[dict]:
    return json.loads(frame.to_json(orient="records", date_format="iso")) if len(frame) else []


def _stats(trades: pd.DataFrame) -> dict:
    if trades.empty:
        return {"n": 0, "mean_r": None, "band": None, "avg_win_loss": None, "win_rate": None, "equity": []}
    r = trades["r"].to_numpy(dtype=float)
    n = len(r)
    sd = r.std(ddof=1) if n > 1 else float("nan")
    wins, losses = trades.loc[trades["pnl"] > 0, "pnl"], trades.loc[trades["pnl"] < 0, "pnl"]
    equity = trades.sort_values("exit_at").assign(equity=lambda f: f["pnl"].cumsum())
    return {"n": n, "mean_r": float(r.mean()),
            "band": [float(r.mean() - 1.96 * sd / math.sqrt(n)), float(r.mean() + 1.96 * sd / math.sqrt(n))]
            if n > 1 else None,
            "avg_win_loss": float(wins.mean() / -losses.mean()) if len(wins) and len(losses) else None,
            "win_rate": float((r > 0).mean()),
            "equity": [{"at": a, "equity": float(e)} for a, e in zip(equity["exit_at"], equity["equity"])]}


def create_app(journal, research_dir: Path, h: dict, today, sessions: list[date], snapshot=None) -> FastAPI:
    app = FastAPI(title="quantdesk")
    research_dir = Path(research_dir)

    @app.get("/", response_class=HTMLResponse)
    def page():
        return (STATIC / "index.html").read_text(encoding="utf-8")

    @app.get("/api/today")
    def today_view():
        day = today()
        snap = snapshot() if snapshot else {}
        mode = effective_mode(journal, day, journal.get_state("verdict_mode", "shadow"))
        return {"day": day.isoformat(), "mode": mode, "kill_switch": journal.get_state("kill_switch") or None,
                "locks": locks(journal, day, sessions, h),
                "lock_periods": {k: lock_period(k, day) for k in locks(journal, day, sessions, h)},
                "alerts": _records(journal.alerts(day.isoformat())),
                "real": _records(journal._query("select r.* from real_trades r join alerts a on a.id = r.alert_id "
                                                "where a.at like ?", (f"{day.isoformat()}%",))),
                "open_papers": _records(journal.open_papers()),
                "day_card": snap.get("day_card", {}), "frames": snap.get("frames", {}),
                "shadow_pause": journal.get_state("shadow_pause_until")}

    @app.post("/api/alerts/{alert_id}/status")
    def set_status(alert_id: int, body: StatusIn):
        journal.set_alert_status(alert_id, body.status)
        return {"ok": True}

    @app.post("/api/alerts/{alert_id}/fill")
    def fill(alert_id: int, body: FillIn):
        return {"real_trade_id": journal.add_real_fill(alert_id, body.premium, pd.Timestamp.now(tz="Asia/Kolkata"))}

    @app.post("/api/real/{real_id}/exit")
    def real_exit(real_id: int, body: ExitIn):
        pnl = body.pnl
        if pnl is None:
            rows = journal._query("select r.fill_premium, a.lot, a.idx from real_trades r join alerts a "
                                  "on a.id = r.alert_id where r.id = ?", (real_id,))
            if rows.empty:
                raise HTTPException(404, "no such real trade")
            fill, lot, index = float(rows.loc[0, "fill_premium"]), int(rows.loc[0, "lot"]), rows.loc[0, "idx"]
            costs = round_trip(fill, body.premium, lot, exchange=EXCHANGE[index], day=today()).total
            pnl = (body.premium - fill) * lot - costs
        journal.close_real(real_id, body.premium, pd.Timestamp.now(tz="Asia/Kolkata"), pnl, body.notes)
        return {"ok": True, "pnl": pnl}

    @app.post("/api/unlock")
    def unlock(body: UnlockIn):
        journal.log_event("unlock", f"{body.lock}|{body.period}|{body.reason}")
        if body.lock == "kill_switch":
            journal.set_state("kill_switch", "")
        return {"ok": True}

    @app.post("/api/shadow-pause")
    def shadow_pause(body: PauseIn):
        day = today()
        until = (day + pd.offsets.Week(weekday=6)).date().isoformat()
        journal.set_state("shadow_pause_until", until)
        journal.log_event("shadow_pause", f"until {until}: {body.reason}")
        return {"until": until}

    @app.get("/api/journal")
    def journal_view():
        paper = journal.closed_trades("paper")
        real = journal.closed_trades("real")
        alerts = journal.alerts()
        live = alerts[alerts["mode"] == "live"] if len(alerts) else alerts
        followed = float((live["status"] == "took").mean()) if len(live) else None
        entries = journal._query("select p.entry_at, p.entry_premium, a.lot from paper_trades p join alerts a "
                                 "on a.id = p.alert_id")
        turnover = float((entries["entry_premium"] * entries["lot"]).sum()) if len(entries) else 0.0
        return {"paper": _stats(paper), "real": _stats(real), "followed_share": followed,
                "turnover": turnover, "turnover_budget": TURNOVER_BUDGET,
                "calibration": _calibration(journal)}

    @app.get("/api/research")
    def research_view():
        pilots = {p.stem: p.read_text(encoding="utf-8") for p in sorted((research_dir / "pilots").glob("*.md"))}
        read = lambda name: (research_dir / name).read_text(encoding="utf-8") if (research_dir / name).exists() else ""
        experiments = pd.read_csv(research_dir / "experiments.csv") if (research_dir / "experiments.csv").exists() \
            else pd.DataFrame()
        return {"pilots": pilots, "verdict": read("VERDICT.md"), "preflight": read("PREFLIGHT.md"),
                "pricecheck": read("pricecheck.json"), "experiments": _records(experiments)}

    @app.websocket("/ws")
    async def ws(socket: WebSocket):
        await socket.accept()
        last = None
        try:
            while True:
                stamp = journal.path.stat().st_mtime if journal.path.exists() else 0
                if stamp != last:
                    last = stamp
                    await socket.send_text("refresh")
                await asyncio.sleep(2)
        except WebSocketDisconnect:
            return

    return app


def _calibration(journal) -> list[dict]:
    """Predicted p against the observed share of paper winners, in five bins (spec §7 monthly check)."""
    rows = journal._query("select a.p, p.pnl from paper_trades p join alerts a on a.id = p.alert_id "
                          "where p.exit_at is not null and a.p is not null")
    if rows.empty:
        return []
    rows["bin"] = pd.cut(rows["p"], bins=[0, 0.3, 0.4, 0.5, 0.6, 1.0])
    out = rows.groupby("bin", observed=True).agg(n=("p", "size"), predicted=("p", "mean"),
                                                 observed=("pnl", lambda s: float((s > 0).mean())))
    return [{"bin": str(b), **{k: float(v) for k, v in row.items()}} for b, row in out.iterrows()]
