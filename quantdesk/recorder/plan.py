"""Pure planning of websocket subscriptions: which tokens to record, and re-centring."""

import copy
from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from quantdesk.instruments import UNDERLYING_SEGMENTS, atm_strike, chain_tokens, current_future, option_expiries

EXCHANGE_TYPES = {"NSE": 1, "NFO": 2, "BSE": 3, "BFO": 4}
META_COLUMNS = ["token", "underlying", "expiry", "strike", "side"]


@dataclass
class SubscriptionPlan:
    tokens: dict[int, list[str]]
    option_meta: pd.DataFrame
    depth_tokens: set[str]
    index_tokens: set[str]
    centres: dict[tuple[str, date], float]
    width: int
    reduced: bool = False
    future_tokens: set[str] = field(default_factory=set)

    def count(self) -> int:
        return sum(len(v) for v in self.tokens.values())


def _add(tokens: dict[int, list[str]], segment: str, token: str) -> None:
    bucket = tokens.setdefault(EXCHANGE_TYPES[segment], [])
    if token not in bucket:
        bucket.append(token)


def _chain_rows(master, underlying, expiry, centre, width) -> list[dict]:
    rows = []
    for _, r in chain_tokens(master, underlying, expiry, centre, width).iterrows():
        for side, column in (("CE", "ce_token"), ("PE", "pe_token")):
            if r[column]:
                rows.append({"token": r[column], "underlying": underlying, "expiry": expiry,
                             "strike": float(r["strike"]), "side": side})
    return rows


def _depth(master, underlying, expiry, centre, depth_width) -> set[str]:
    chain = chain_tokens(master, underlying, expiry, centre, depth_width)
    return {t for t in list(chain["ce_token"]) + list(chain["pe_token"]) if t}


def _build(master, spots, today, constituents, settings, width) -> SubscriptionPlan:
    rec = settings["recorder"]
    tokens: dict[int, list[str]] = {}
    index_tokens = set()
    for spec in settings["angel"]["index_tokens"].values():
        _add(tokens, spec["exchange"], spec["token"])
        index_tokens.add(spec["token"])
    meta_rows, depth, centres, futures = [], set(), {}, set()
    for underlying in UNDERLYING_SEGMENTS:
        if underlying not in spots:
            continue
        segment = UNDERLYING_SEGMENTS[underlying][0]
        future = current_future(master, underlying, today)
        _add(tokens, segment, future["token"])
        futures.add(future["token"])
        expiries = option_expiries(master, underlying, today, n=2)
        for i, expiry in enumerate(expiries):
            rows = _chain_rows(master, underlying, expiry, spots[underlying], width)
            for row in rows:
                _add(tokens, segment, row["token"])
            meta_rows += rows
            strikes = sorted({r["strike"] for r in rows})
            centres[(underlying, expiry)] = atm_strike(spots[underlying], strikes)
            if i == 0:
                depth |= _depth(master, underlying, expiry, spots[underlying], rec["depth_width"])
    for token in constituents.values():
        _add(tokens, "NSE", token)
    return SubscriptionPlan(tokens=tokens, option_meta=pd.DataFrame(meta_rows, columns=META_COLUMNS),
                            depth_tokens=depth, index_tokens=index_tokens, centres=centres,
                            width=width, future_tokens=futures)


def plan_subscriptions(master: pd.DataFrame, spots: dict[str, float], today: date,
                       constituents: dict[str, str], settings: dict) -> SubscriptionPlan:
    rec = settings["recorder"]
    plan = _build(master, spots, today, constituents, settings, rec["strike_width"])
    if plan.count() > rec["max_tokens_per_connection"]:
        plan = _build(master, spots, today, constituents, settings, rec["fallback_width"])
        plan.reduced = True
    return plan


def recenter(plan: SubscriptionPlan, spots: dict[str, float], master: pd.DataFrame,
             settings: dict) -> tuple[SubscriptionPlan, dict[int, list[str]]]:
    """Add strikes when ATM has moved more than `recenter_strikes` from a chain's centre.
    Existing subscriptions are never dropped, and the total never exceeds max_tokens_per_connection:
    when room runs out, the strikes nearest the new ATM are added first."""
    rec = settings["recorder"]
    room = rec["max_tokens_per_connection"] - plan.count()
    new_plan = copy.deepcopy(plan)
    existing = set(plan.option_meta["token"])
    added: dict[int, list[str]] = {}
    new_rows = []
    for (underlying, expiry), centre in plan.centres.items():
        if underlying not in spots:
            continue
        all_strikes = sorted(set(master[(master["name"] == underlying) & (master["expiry"] == expiry)
                                        & (master["instrumenttype"] == "OPTIDX")]["strike"]))
        if not all_strikes:
            continue
        new_atm = atm_strike(spots[underlying], all_strikes)
        moved = abs(all_strikes.index(new_atm) - all_strikes.index(atm_strike(centre, all_strikes)))
        if moved <= rec["recenter_strikes"]:
            continue
        segment = UNDERLYING_SEGMENTS[underlying][0]
        fresh = [row for row in _chain_rows(master, underlying, expiry, new_atm, plan.width)
                 if row["token"] not in existing]
        fresh.sort(key=lambda row: (abs(row["strike"] - new_atm), row["side"]))
        for row in fresh:
            if room <= 0:
                break
            room -= 1
            existing.add(row["token"])
            new_rows.append(row)
            _add(new_plan.tokens, segment, row["token"])
            added.setdefault(EXCHANGE_TYPES[segment], []).append(row["token"])
        new_plan.centres[(underlying, expiry)] = new_atm
        if expiry == min(e for (u, e) in plan.centres if u == underlying):
            new_plan.depth_tokens |= _depth(master, underlying, expiry, new_atm, rec["depth_width"])
    if new_rows:
        new_plan.option_meta = pd.concat([plan.option_meta, pd.DataFrame(new_rows, columns=META_COLUMNS)],
                                         ignore_index=True)
    return new_plan, added
