"""Stage A, the signal dataset: every H1 signal once, with everything that does not depend on a model.

Each signal row carries:
- **gate outcome:** the first gate it failed, or none
- **scores:** its three family scores
- **label:** its index outcome, whether the target came before the stop and before the hard exit
- **context:** its hurdle components

Signals that passed every gate also get their strike candidates.

There is no P&L here, and nothing summarises the labels (R32): they are training targets for the trials,
read only inside a ticketed run. CPCV then costs one pass over history, not one per split.
"""

import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Protocol

import pandas as pd

from quantdesk.clock import IST
from quantdesk.pricing.quotes import ModelQuotes
from quantdesk.strategy.gates import Helpers, first_failed_gate
from quantdesk.strategy.meta import label
from quantdesk.strategy.pipeline import _warm, family_scores
from quantdesk.strategy.strikes import candidates
from quantdesk.strategy.timeline import check_times, timeline_block
from quantdesk.strategy.trigger import h1
from quantdesk.strategy.types import DayContext
from quantdesk.validation.hypotheses import param

SIGNAL_COLUMNS = ["signal_id", "day", "index", "at", "side", "ref_close", "upper", "lower", "vwap", "stop_level", "b",
                  "target_level", "failed", "technical", "options", "macro", "har_pct", "dte", "label", "delta_event",
                  "delta_shock", "delta_stress", "lot", "vix_prev_close", "weekday", "expiry_day"]
CANDIDATE_COLUMNS = ["signal_id", "index", "expiry", "strike", "kind", "lot", "ask", "delta", "gain", "loss"]


class DaySource(Protocol):
    def context(self, index: str, day: date) -> DayContext: ...
    def frame(self, ctx: DayContext) -> pd.DataFrame: ...
    def helpers(self, ctx: DayContext, frame: pd.DataFrame) -> Helpers: ...
    def record_signal(self, day: date, raw: dict) -> None: ...


class LoaderSource:
    """The real day source: DayLoader plus modelled quotes, with the last day's frame kept in memory."""

    def __init__(self, loader, h: dict):
        self.loader, self.h = loader, h
        self._frames: dict = {}

    def context(self, index, day):
        return self.loader.day_context(index, day)

    def frame(self, ctx):
        key = (ctx.index, ctx.day)
        if key not in self._frames:
            self._frames = {key: self.loader.minute_frame(ctx)}
        return self._frames[key]

    def helpers(self, ctx, frame):
        return Helpers(self.loader.clock, self.loader.surface,
                       ModelQuotes({ctx.index: frame}, self.loader.surface, self.loader.clock, self.h))

    def record_signal(self, day, raw):
        self.loader.record_signal(day, raw)


@dataclass
class SignalDataset:
    signals: pd.DataFrame
    candidates: pd.DataFrame


def build_dataset(source: DaySource, days: list[date], indices: dict[str, date], h: dict, today: date,
                  progress=None) -> SignalDataset:
    """`indices` maps an index to its first tradable day (R11). `days` are the regular sessions to walk."""
    rows, cands = [], []
    for day in days:
        for index, start in indices.items():
            if day < start:
                continue
            try:
                ctx = source.context(index, day)
            except KeyError:
                continue
            if ctx.expiry_1 is None or ctx.session_kind != "regular":
                continue
            frame = source.frame(ctx)
            helpers = source.helpers(ctx, frame)
            hard = datetime.combine(day, ctx.hard_exit, tzinfo=IST)
            for at in check_times(day, ctx.is_expiry_day, h):
                if timeline_block(ctx, at, h):
                    continue
                past = frame[frame["ts"] <= at - timedelta(minutes=1)]
                sig = h1(past, at, ctx, h)
                if sig is None:
                    continue
                sid = f"{index}-{at:%Y%m%d%H%M}"
                row = {"signal_id": sid, "day": day, "index": index, "at": at, "side": sig.side,
                       "ref_close": sig.ref_close, "upper": sig.upper, "lower": sig.lower, "vwap": sig.vwap,
                       "stop_level": sig.stop_level, "b": sig.b, "target_level": sig.target_level,
                       "har_pct": ctx.har_pct, "dte": ctx.dte_1, "lot": ctx.lot_1, "vix_prev_close": ctx.vix_prev_close,
                       "weekday": day.weekday(), "expiry_day": ctx.is_expiry_day,
                       "delta_event": ctx.delta_parts.get("event", 0.0), "delta_shock": ctx.delta_parts.get("shock", 0.0),
                       "delta_stress": ctx.delta_parts.get("stress", 0.0)}
                if not _warm(ctx):
                    rows.append({**row, "failed": "warmup"})
                    continue
                scores = family_scores(ctx, past, sig, h)
                source.record_signal(day, scores["raw"])
                failed = first_failed_gate(sig, ctx, past, helpers, h)
                if scores["technical"] is None:
                    failed = failed or "warmup"
                rows.append({**row, "failed": failed, "technical": scores["technical"], "options": scores["options"],
                             "macro": scores["macro"], "label": label(frame, sig, hard)})
                if failed is None:
                    for c in candidates(sig, ctx, helpers, h, today):
                        cands.append({"signal_id": sid, **c.__dict__})
        if progress:
            progress(day)
    signals = pd.DataFrame(rows).reindex(columns=SIGNAL_COLUMNS)
    return SignalDataset(signals, pd.DataFrame(cands).reindex(columns=CANDIDATE_COLUMNS))


def save_dataset(dataset: SignalDataset, derived) -> None:
    derived.write_frame("signals", dataset.signals.assign(available_at=dataset.signals["at"]))
    derived.write_frame("signal_candidates", dataset.candidates)


def load_dataset(derived) -> SignalDataset:
    signals = derived.read("signals").drop(columns=["available_at"], errors="ignore")
    return SignalDataset(signals.sort_values("at").reset_index(drop=True), derived.read("signal_candidates"))
