"""The live engine (SP3 design S1-S9): the backtest's decide() on today's recorded market.

`step(now)` is called every few seconds. It does four things:
- **checks:** runs each check time once its bar has been recorded
- **alerts:** journals each alert and pushes it (live mode) or keeps it as a shadow setup (alert-off, or a
  kill-switch has fired), and opens a paper trade either way, filled by the backtest's own rule (`fill`: ask
  + 1 tick at the bar T + delay - 1, with the chase cap and the lapse), once that bar is recorded
- **pre-alerts:** sends the "setup forming" pre-alert 5 minutes ahead
- **paper trades:** walks each open one with the same exit rules as the backtest, turning new ratchets
  into stop-move messages and exits into exit messages

A lock suppresses new alerts, never exit messages. Nothing here places an order.

**Late start or restart** (a power cut, a crash). A check more than 60 seconds old is never run, so no stale
alert is pushed; it is journalled as `missed` (S4). Today's open paper trades are rebuilt from the journal by
re-running their decision, so their stop moves and exit messages carry on; ratchets already sent are not
sent again.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

import pandas as pd

from quantdesk.analysis.bands import band_edges, slot
from quantdesk.backtest.fills import fill
from quantdesk.costs import round_trip
from quantdesk.live import notify as fmt
from quantdesk.live.monitor import effective_mode, kill_switches, locks
from quantdesk.strategy.exits import OpenTrade, _path_a
from quantdesk.strategy.pipeline import decide
from quantdesk.strategy.timeline import check_times
from quantdesk.strategy.types import Signal, StrikeChoice
from quantdesk.validation.hypotheses import param

TICK = 0.05
EXCHANGE = {"NIFTY": "NSE", "SENSEX": "BSE"}
PREALERT_BAND = 0.25


@dataclass
class LiveEngine:
    make_source: object                    # callable(now) -> a DaySource for today
    journal: object
    notifier: object
    cfg: object
    model: object
    h: dict
    today: date
    mode: str = "shadow"                   # the verdict's mode, "live" or "shadow" (S2)
    forced_live: bool = False               # explicit owner override while research verdict is alert-off
    kill_params: dict | None = None        # mu0, breakeven, sigma, cusum_h of the accepted trial (S9)
    push_shadow: bool = True               # shadow alerts and exits to the phone, marked (owner, 22 Oct 2026)
    idea: bool = False                     # the owner's idea feed: every setup as a paper-tracked CALL/PUT idea
    brief: object | None = None            # callable(now, ctxs, frames) -> (text, leans): the 09:20 brief
    indices: tuple = ("NIFTY", "SENSEX")
    sessions: list = field(default_factory=list)
    processed: set = field(default_factory=set)
    prealerted: set = field(default_factory=set)
    _ctx: dict = field(default_factory=dict)
    _open: dict = field(default_factory=dict)  # paper id -> (OpenTrade, alert id, index, mode)
    _frames: dict = field(default_factory=dict)  # index -> chart rows for the dashboard
    _pending: dict = field(default_factory=dict)  # alert id -> (Decision, index, mode), waiting for its fill bar
    _resumed: bool = False

    def snapshot(self) -> dict:
        """What the dashboard shows: a plain-words day card and the latest minute frames."""
        cards = {}
        for index, ctx in self._ctx.items():
            parts = ", ".join(f"{k} +{v:.2f}" for k, v in (ctx.delta_parts or {}).items() if v)
            cards[index] = (f"open {ctx.open:.1f} vs prev close {ctx.prev_close:.1f}; HAR day move "
                            f"{100 * ctx.sigma_day:.2f}% (pct {ctx.har_pct if ctx.har_pct is not None else '-'}); "
                            f"expiry {ctx.expiry_1}{' (today)' if ctx.is_expiry_day else ''}; "
                            f"events {', '.join(e.title for e in ctx.events) or 'none'}; hurdle {parts or 'none'}")
        return {"day_card": cards, "frames": self._frames}

    def step(self, now: datetime) -> list:
        source = self.make_source(now)
        ready = {}
        for index in self.indices:
            try:
                ctx = self._ctx.get(index) or self._ctx.setdefault(index, source.context(index, self.today))
            except (KeyError, ValueError):
                continue
            frame = source.frame(ctx)
            frame = frame[frame["ts"] <= now - timedelta(minutes=1)]
            cols = [c for c in ("ts", "close", "vwap", "upper", "lower") if c in frame]
            self._frames[index] = frame[cols].assign(ts=frame["ts"].astype(str)).to_dict("records")
            ready[index] = (ctx, frame)
        if not self._resumed and ready:
            self._resume(now, source, ready)
        self._morning(now, ready)
        decisions, missed = [], []
        for index, (ctx, frame) in ready.items():
            decisions += self._checks(now, ctx, frame, source, missed)
            self._prealert(now, ctx, frame)
        if missed:
            self.journal.log_event("missed", "checks more than 60 s old, not run: " + ", ".join(missed), at=now)
        self._fill_pending(now, source)
        self._manage(now, source)
        return decisions

    def _resume(self, now, source, ready):
        self._resumed = True
        papers = self.journal.open_papers()
        resumed = 0
        for p in papers.itertuples(index=False):
            if str(p.entry_at)[:10] != self.today.isoformat():
                continue
            at = datetime.fromisoformat(p.at)
            if p.idx not in ready:
                self.journal.log_event("resume_failed", f"paper {p.paper_id}: no {p.idx} data yet", at=now)
                continue
            ctx, frame = ready[p.idx]
            d = decide(ctx, frame, at, self.cfg, self.model, source.helpers(ctx, frame), self.h, self.today,
                       idea=self.idea)
            if d.alert is None:
                self.journal.log_event("resume_failed", f"paper {p.paper_id}: its decision did not recur", at=now)
                continue
            c, premium = d.alert.choice, float(p.entry_premium)
            trigger = premium - self._risk(c) / c.lot
            trade = OpenTrade(d.signal, c, datetime.fromisoformat(p.entry_at), premium, trigger,
                              trigger - max(0.10 * trigger, 5 * TICK))
            self._open[int(p.paper_id)] = (trade, int(p.alert_id), p.idx, p.mode)
            self.processed.add((p.idx, at))
            resumed += 1
        if resumed:
            self.journal.log_event("resume", f"{resumed} open paper trade(s) resumed", at=now)

    def _risk(self, choice) -> float:
        """Rupees between the fill and the backstop: the strike's planned loss for an idea, else the fixed risk."""
        return choice.loss if self.idea else param(self.h, "account.risk_rupees")

    def _morning(self, now, ready):
        key = f"brief_{self.today}"
        if self.brief is None or not ready or now.time() < time(9, 20) or self.journal.get_state(key):
            return
        self.journal.set_state(key, "1")                       # once, even if building it fails
        try:
            text, leans = self.brief(now, {i: c for i, (c, _) in ready.items()}, {i: f for i, (_, f) in ready.items()})
        except Exception as exc:  # noqa: BLE001 - a missing input must not stop the trading day
            self.journal.log_event("brief_failed", f"{type(exc).__name__}: {exc}"[:300], at=now)
            return
        for index, label in leans.items():
            self.journal.set_state(f"lean_{self.today}_{index}", label)
        self.notifier.send(text)

    def _checks(self, now, ctx, frame, source, missed):
        out = []
        for at in check_times(self.today, ctx.is_expiry_day, self.h):
            key = (ctx.index, at)
            if at > now or key in self.processed:
                continue
            has_bar = (frame["ts"] == at - timedelta(minutes=1)).any()
            if has_bar and now - at > timedelta(seconds=60):
                self.processed.add(key)
                missed.append(f"{ctx.index} {at:%H:%M}")
                continue
            if not has_bar:
                if now - at > timedelta(seconds=60):
                    self.processed.add(key)
                    self.journal.log_event("data_late", f"{ctx.index} {at:%H:%M}: bar never recorded", at=now)
                continue
            self.processed.add(key)
            helpers = source.helpers(ctx, frame)
            d = decide(ctx, frame, at, self.cfg, self.model, helpers, self.h, self.today, idea=self.idea)
            out.append(d)
            if d.alert is not None:
                self._alert(d, ctx, now)
        return out

    def _alert(self, d, ctx, now):
        if self.idea:
            mode, held = "idea", []
            busy = any(i == ctx.index for _, i, _ in self._pending.values()) or \
                any(i == ctx.index for _, _, i, _ in self._open.values())
            if busy:                                           # one idea per index at a time
                self.journal.log_event("idea_skipped", f"{ctx.index} {d.at:%H:%M}: an idea is still open", at=now)
                return
        else:
            mode = effective_mode(self.journal, self.today, self.mode)
            pending = sum(1 for _, _, m in self._pending.values() if m == "live")
            held = locks(self.journal, self.today, self.sessions or [self.today], self.h, pending) \
                if mode == "live" else []
        if held:
            mode = "suppressed"
        a, c = d.alert, d.alert.choice
        row = {"at": d.at, "index": ctx.index, "side": a.side, "mode": mode, "expiry": c.expiry, "strike": c.strike,
               "kind": c.kind, "lot": c.lot, "entry_limit": a.entry_limit, "index_stop": a.index_stop,
               "index_target": a.index_target, "backstop_trigger": a.backstop_trigger,
               "backstop_limit": a.backstop_limit, "p": a.p, "ev": c.ev, "delta": a.delta,
               "reasons_for": "; ".join(a.reasons_for), "reasons_against": "; ".join(a.reasons_against),
               "signal_id": f"{ctx.index}-{d.at:%Y%m%d%H%M}", "forced_live": self.forced_live}
        alert_id = self.journal.add_alert(row)
        if mode == "suppressed":
            self.journal.log_event("lock", f"alert {alert_id} held back: {', '.join(held)}", at=now)
        if mode == "idea":
            self.notifier.send(fmt.format_idea(row, c.target_premium, c.p_be))
        elif mode == "live" or (mode == "shadow" and self.push_shadow):
            self.notifier.send(fmt.format_alert(row))      # a shadow alert says "SHADOW - do not trade"
        self._pending[alert_id] = (d, ctx.index, mode)

    def _fill_pending(self, now, source):
        """Paper fills by the backtest's rule, so paper and backtest results compare like for like."""
        delay = int(param(self.h, "backtest.primary_delay_min"))
        for alert_id, (d, index, mode) in list(self._pending.items()):
            ctx = self._ctx[index]
            bar = d.at + timedelta(minutes=delay - 1)
            frame = source.frame(ctx)
            frame = frame[frame["ts"] <= now - timedelta(minutes=1)]
            if not (frame["ts"] == bar).any():
                if now - bar > timedelta(minutes=2):
                    del self._pending[alert_id]
                    self.journal.log_event("paper_unfilled", f"alert {alert_id}: fill bar never recorded", at=now)
                continue
            del self._pending[alert_id]
            c = d.alert.choice
            res = fill(d.signal, c, frame, source.helpers(ctx, frame).quotes, delay, ctx, self.h)
            if res.status != "filled":
                self.journal.log_event("paper_unfilled", f"alert {alert_id}: {res.status}", at=now)
                continue
            paper_id = self.journal.open_paper(alert_id, res.at, res.premium)
            trigger = res.premium - self._risk(c) / c.lot
            trade = OpenTrade(d.signal, c, res.at, res.premium, trigger, trigger - max(0.10 * trigger, 5 * TICK))
            self._open[paper_id] = (trade, alert_id, index, mode)

    def _prealert(self, now, ctx, frame):
        if effective_mode(self.journal, self.today, self.mode) != "live" or frame.empty:
            return
        for at in check_times(self.today, ctx.is_expiry_day, self.h):
            key = (ctx.index, at)
            if key in self.prealerted or not (at - timedelta(minutes=5) <= now < at - timedelta(minutes=4)):
                continue
            row = frame.iloc[-1]
            s = slot(row["ts"])
            sigma = ctx.band_sigma[s] if 0 <= s < len(ctx.band_sigma) else float("nan")
            if sigma != sigma:
                continue
            upper, lower = band_edges(ctx.open, ctx.prev_close, sigma, param(self.h, "h1.band_v"))
            near = PREALERT_BAND * sigma * ctx.open
            side = None
            if row["close"] > row["vwap"] and upper - near <= row["close"] <= upper:
                side = "long"
            elif row["close"] < row["vwap"] and lower <= row["close"] <= lower + near:
                side = "short"
            if side:
                self.prealerted.add(key)
                self.notifier.send(fmt.format_prealert(ctx.index, side, now))

    def _manage(self, now, source):
        for paper_id, (trade, alert_id, index, mode) in list(self._open.items()):
            ctx = self._ctx[index]
            frame = source.frame(ctx)
            frame = frame[frame["ts"] <= now - timedelta(minutes=1)]
            decided, exit_at, reason, schedule, _ = _path_a(trade, frame, ctx, self.cfg.exit_policy, self.h)
            known = len(self.journal.ratchets(alert_id))
            helpers = source.helpers(ctx, frame)
            c = trade.choice
            for effective, index_stop in schedule[known:]:
                trigger = helpers.quotes.mid(c.index, c.expiry, c.strike, c.kind, min(effective, now), spot=index_stop)
                self.journal.add_ratchet(alert_id, effective, index_stop, trigger)
                if mode in ("live", "idea"):
                    text = fmt.format_ratchet(index, index_stop, trigger, effective - timedelta(minutes=2))
                    self.notifier.send(text if mode == "live" else "IDEA " + text)
            if reason == "end_of_data" or exit_at > now:
                if reason != "end_of_data" and decided <= now:
                    self._send_exit(paper_id, mode, index, reason, decided)
                continue
            bid = max(TICK, helpers.quotes.quote(c.index, c.expiry, c.strike, c.kind, exit_at).bid)
            costs = round_trip(trade.fill_premium, bid, c.lot, exchange=EXCHANGE[c.index], day=self.today).total
            pnl = (bid - trade.fill_premium) * c.lot - costs
            self.journal.close_paper(paper_id, exit_at, bid, reason, pnl)
            self._send_exit(paper_id, mode, index, reason, decided)
            del self._open[paper_id]
            self._check_kill(now)

    def _send_exit(self, paper_id, mode, index, reason, decided):
        """Once per trade. Shadow exits go out marked SHADOW, so the owner can follow every call (choice B)."""
        if self.journal.get_state(f"exit_sent_{paper_id}") is not None:
            return
        if mode == "live":
            self.notifier.send(fmt.format_exit(index, reason, decided))
        elif mode == "idea":
            self.notifier.send("IDEA " + fmt.format_exit(index, reason, decided))
        elif mode == "shadow" and self.push_shadow:
            self.notifier.send("SHADOW " + fmt.format_exit(index, reason, decided))
        self.journal.set_state(f"exit_sent_{paper_id}", "1")

    def _check_kill(self, now):
        """S9: after each closed trade. A firing turns new alerts to shadow until the owner lifts it."""
        if not self.kill_params or self.journal.get_state("kill_switch"):
            return
        fired = kill_switches(self.journal, self.kill_params, self.h)
        if fired:
            reasons = ", ".join(fired)
            self.journal.set_state("kill_switch", reasons)
            self.journal.log_event("kill_switch", reasons, at=now)
            self.notifier.send(fmt.format_kill(reasons, now))
