"""When an entry may be considered (spec §6.1 step 2): completed bars at :00, :15, :30 and :45 from 09:45, the
last at 14:00, or 13:30 on the traded index's expiry day. Irregular sessions and event windows block entries.
"""

from datetime import date, datetime, time, timedelta

from quantdesk.analysis.macro import event_block
from quantdesk.clock import IST
from quantdesk.strategy.types import DayContext
from quantdesk.validation.hypotheses import param


def check_times(day: date, is_expiry_day: bool, h: dict) -> list[datetime]:
    first = time.fromisoformat(param(h, "time.first_check"))
    last = time.fromisoformat(param(h, "time.last_entry_expiry" if is_expiry_day else "time.last_entry"))
    minutes = set(param(h, "time.check_minutes"))
    at, end = datetime.combine(day, first, tzinfo=IST), datetime.combine(day, last, tzinfo=IST)
    out = []
    while at <= end:
        if at.minute in minutes:
            out.append(at)
        at += timedelta(minutes=1)
    return out


def timeline_block(ctx: DayContext, at: datetime, h: dict) -> str | None:
    if ctx.session_kind != "regular":
        return "irregular_session"
    times = check_times(ctx.day, ctx.is_expiry_day, h)
    if at not in times:
        last = times[-1] if times else None
        return "after_last_entry" if last is not None and at > last else "not_a_check_time"
    return event_block(ctx.events, at, h)
