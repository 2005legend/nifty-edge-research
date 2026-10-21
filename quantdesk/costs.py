"""Angel One charges for one round trip in an index option (spec §6.2: unit-tested cost model).

Rates and the formula come from research_notes/Nifty options multifactor quant strategy/
option_trade_construction.md §10 (Angel One's exchange-transaction-charges page; STT from Budget 2026).
Schedules run from 1 Jan 2019 (the backtest's start) with the source of each change; a date before that
raises UnknownChargeSchedule rather than guessing. Whether a backtest prices old trades at the rates of their
day or at today's (what the owner will actually pay) is an SP2 design decision: pass that date as `day`. Exercise STT is not modelled: the system is
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


# Brokerage is the owner's Angel One rate (Rs 20/order) throughout: a backtest asks what the owner would pay.
# Small, unsourced differences are noted rather than guessed (each is well under Rs 1 per round trip):
# SEBI's fee is Rs 10/crore throughout (it was Rs 15 at some point before 2020); stamp duty is the uniform
# 0.003% of 1 Jul 2020 throughout (states charged about 0.002-0.003% before); BSE options before 1 Oct 2024
# use the 0.0495% "old" rate in Zerodha's bulletin (BSE used slabs, and Sensex options barely traded before
# May 2023); NSE's 0.03503% -> 0.03553% step is dated 1 Apr 2026, when Angel One's page was read.
_COMMON = dict(brokerage_per_order=20.0, sebi_per_rupee=1e-6, stamp_buy=0.00003, gst=0.18)
SCHEDULES = [
    Schedule(effective_from=date(2019, 1, 1), stt_sell=0.0005, exchange={"NSE": 0.00053, "BSE": 0.000495},
             source="STT 0.05% from 1 Jun 2016; NSE 0.053% = the rate replaced on 1 Apr 2023 (Zerodha bulletin "
                    "347967); earlier NSE revisions not sourced", **_COMMON),
    Schedule(effective_from=date(2023, 4, 1), stt_sell=0.000625, exchange={"NSE": 0.0005, "BSE": 0.000495},
             source="Zerodha bulletin 347967: STT 0.05 -> 0.0625%, NSE options 0.053 -> 0.05% from 1 Apr 2023",
             **_COMMON),
    Schedule(effective_from=date(2024, 4, 1), stt_sell=0.000625, exchange={"NSE": 0.000495, "BSE": 0.000495},
             source="Zerodha bulletin 373933: NSE options 0.05 -> 0.0495% from 1 Apr 2024", **_COMMON),
    Schedule(effective_from=date(2024, 10, 1), stt_sell=0.001, exchange={"NSE": 0.0003503, "BSE": 0.000325},
             source="Zerodha bulletin 391488: STT 0.0625 -> 0.1%, NSE 0.0495 -> 0.03503%, BSE -> 0.0325% "
                    "(Rs 3,250/crore, BSE circular) from 1 Oct 2024", **_COMMON),
    Schedule(effective_from=date(2026, 4, 1), stt_sell=0.0015, exchange={"NSE": 0.0003553, "BSE": 0.000325},
             source="angelone.in/exchange-transaction-charges; STT 0.15% from 1 Apr 2026 (Budget 2026)",
             **_COMMON),
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
