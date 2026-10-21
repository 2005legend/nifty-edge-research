"""Angel One charges for one round trip in an index option (spec §6.2: unit-tested cost model).

Rates and the formula come from research_notes/Nifty options multifactor quant strategy/
option_trade_construction.md §10 (Angel One's exchange-transaction-charges page; STT from Budget 2026).
Only schedules with a source are listed: a date before the earliest one raises UnknownChargeSchedule
rather than silently using today's rates in a backtest. Exercise STT is not modelled: the system is
always flat before the close.
"""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal


class UnknownChargeSchedule(LookupError):
    """No sourced charge schedule covers this date yet."""


@dataclass(frozen=True)
class Schedule:
    effective_from: date
    brokerage_per_order: float  # Angel One, per executed F&O order
    stt_sell: float             # securities transaction tax on the sell premium
    exchange: dict              # transaction charge on premium, by exchange
    sebi_per_rupee: float       # SEBI turnover fee (Rs 10 per crore)
    stamp_buy: float            # stamp duty on the buy premium
    gst: float                  # on brokerage + exchange + SEBI
    source: str


SCHEDULES = [
    Schedule(effective_from=date(2026, 4, 1), brokerage_per_order=20.0, stt_sell=0.0015,
             exchange={"NSE": 0.0003553, "BSE": 0.000325}, sebi_per_rupee=1e-6, stamp_buy=0.00003, gst=0.18,
             source="angelone.in/exchange-transaction-charges; STT 0.15% from 1 Apr 2026 (Budget 2026)"),
]


@dataclass(frozen=True)
class Costs:
    brokerage: float
    stt: int
    exchange: float
    sebi: float
    stamp: float
    gst: float

    @property
    def total(self) -> float:
        return self.brokerage + self.stt + self.exchange + self.sebi + self.stamp + self.gst


def schedule_for(day: date) -> Schedule:
    usable = [s for s in SCHEDULES if s.effective_from <= day]
    if not usable:
        raise UnknownChargeSchedule(f"no sourced charge schedule for {day}; earliest is {SCHEDULES[0].effective_from}")
    return max(usable, key=lambda s: s.effective_from)


def round_trip(buy_premium: float, sell_premium: float, qty: int, *, exchange: str, day: date) -> Costs:
    """Charges for buying qty units at buy_premium and selling them at sell_premium (two orders)."""
    schedule = schedule_for(day)
    if exchange not in schedule.exchange:
        raise ValueError(f"unknown exchange {exchange!r}; expected one of {sorted(schedule.exchange)}")
    bought, sold = buy_premium * qty, sell_premium * qty
    turnover = bought + sold
    brokerage = 2 * schedule.brokerage_per_order
    stt = int(Decimal(str(schedule.stt_sell * sold)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    exchange_fee = schedule.exchange[exchange] * turnover
    sebi = schedule.sebi_per_rupee * turnover
    stamp = schedule.stamp_buy * bought
    gst = schedule.gst * (brokerage + exchange_fee + sebi)
    return Costs(brokerage=brokerage, stt=stt, exchange=exchange_fee, sebi=sebi, stamp=stamp, gst=gst)
