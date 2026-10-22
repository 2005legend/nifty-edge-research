"""The live engine (SP3 design S1-S9): the backtest's decide() on today's recorded market.

`step(now)` is called every few seconds. It does four things:
- **checks:** runs each check time once its bar has been recorded
- **alerts:** journals each alert and pushes it (live mode) or keeps it as a shadow setup (alert-off, or a
  kill-switch has fired), and opens a paper trade either way
- **pre-alerts:** sends the "setup forming" pre-alert 5 minutes ahead
- **paper trades:** walks each open one with the same exit rules as the backtest, turning new ratchets
  into stop-move messages and exits into exit messages

A lock suppresses new alerts, never exit messages. Nothing here places an order.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

import pandas as pd

from quantdesk.analysis.bands import band_edges, slot
from quantdesk.costs import round_trip
from quantdesk.live import notify as fmt
from quantdesk.live.monitor import locks
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
    mode: str = "shadow"                   # "live" or "shadow" (S2)
    indices: tuple = ("NIFTY", "SENSEX")
    sessions: list = field(default_factory=list)
    processed: set = field(default_factory=set)
    prealerted: set = field(default_factory=set)
    _ctx: dict = field(default_factory=dict)
    _open: dict = field(default_factory=dict)  # paper id -> (OpenTrade, alert id, index)

    def step(self, now: datetime) -> list:
        source = self.make_source(now)
        decisions = []
        for index in self.indices:
            try:
                ctx = self._ctx.get(index) or self._ctx.setdefault(index, source.context(index, self.today))
            except (KeyError, ValueError):
                continue
            frame = source.frame(ctx)
            frame = frame[frame["ts"] <= now - timedelta(minutes=1)]
            decisions += self._checks(now, ctx, frame, source)
            self._prealert(now, ctx, frame)
        self._manage(now, source)
        return decisions

    def _checks(self, now, ctx, frame, source):
        out = []
        for at in check_times(self.today, ctx.is_expiry_day, self.h):
            key = (ctx.index, at)
            if at > now or key in self.processed:
                continue
            if not (frame["ts"] == at - timedelta(minutes=1)).any():
                if now - at > timedelta(seconds=60):
                    self.processed.add(key)
                    self.journal.log_event("data_late", f"{ctx.index} {at:%H:%M}: bar never recorded", at=now)
                continue
            self.processed.add(key)
            helpers = source.helpers(ctx, frame)
            d = decide(ctx, frame, at, self.cfg, self.model, helpers, self.h, self.today)
            out.append(d)
            if d.alert is not None:
                self._alert(d, ctx, frame, helpers, now)
        return out

    def _alert(self, d, ctx, frame, helpers, now):
        held = locks(self.journal, self.today, self.sessions or [self.today], self.h)
        mode = "shadow" if self.mode != "live" else ("suppressed" if held else "live")
        a, c = d.alert, d.alert.choice
        row = {"at": d.at, "index": ctx.index, "side": a.side, "mode": mode, "expiry": c.expiry, "strike": c.strike,
               "kind": c.kind, "lot": c.lot, "entry_limit": a.entry_limit, "index_stop": a.index_stop,
               "index_target": a.index_target, "backstop_trigger": a.backstop_trigger,
               "backstop_limit": a.backstop_limit, "p": a.p, "ev": c.ev, "delta": a.delta,
               "reasons_for": "; ".join(a.reasons_for), "reasons_against": "; ".join(a.reasons_against),
               "signal_id": f"{ctx.index}-{d.at:%Y%m%d%H%M}"}
        alert_id = self.journal.add_alert(row)
        if mode == "suppressed":
            self.journal.log_event("lock", f"alert {alert_id} held back: {', '.join(held)}", at=now)
        if mode == "live":
            self.notifier.send(fmt.format_alert(row))
        ask = helpers.quotes.quote(ctx.index, c.expiry, c.strike, c.kind, d.at).ask
        premium = ask + param(self.h, "fill.entry_ticks_over_ask") * TICK
        paper_id = self.journal.open_paper(alert_id, d.at, premium)
        trigger = premium - param(self.h, "account.risk_rupees") / c.lot
        trade = OpenTrade(d.signal, c, d.at, premium, trigger, trigger - max(0.10 * trigger, 5 * TICK))
        self._open[paper_id] = (trade, alert_id, ctx.index, mode)

    def _prealert(self, now, ctx, frame):
        if self.mode != "live" or frame.empty:
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
                if mode == "live":
                    self.notifier.send(fmt.format_ratchet(index, index_stop, trigger, effective - timedelta(minutes=2)))
            if reason == "end_of_data" or exit_at > now:
                if reason != "end_of_data" and decided <= now and mode == "live" and \
                        self.journal.get_state(f"exit_sent_{paper_id}") is None:
                    self.notifier.send(fmt.format_exit(index, reason, decided))
                    self.journal.set_state(f"exit_sent_{paper_id}", "1")
                continue
            bid = max(TICK, helpers.quotes.quote(c.index, c.expiry, c.strike, c.kind, exit_at).bid)
            costs = round_trip(trade.fill_premium, bid, c.lot, exchange=EXCHANGE[c.index], day=self.today).total
            pnl = (bid - trade.fill_premium) * c.lot - costs
            self.journal.close_paper(paper_id, exit_at, bid, reason, pnl)
            if mode == "live" and self.journal.get_state(f"exit_sent_{paper_id}") is None:
                self.notifier.send(fmt.format_exit(index, reason, decided))
            del self._open[paper_id]
