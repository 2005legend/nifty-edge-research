"""The Nifty 50's per-minute breadth, and the weights of the VWAP proxy (design §5.1).

One row per minute: the members' traded value (the proxy's numerator), advance/decline from the open, the
count above each stock's own VWAP, and the traded-value-weighted return of the previous session's five
heaviest members. `members_minute` is what the trigger's confirmation gate and the day card read, so it is
computed once here rather than inside the pipeline.

Members with no bar are counted and never filled: HDFC Ltd has no data until it left the index in July
2023, and JIOFIN none before its August 2023 listing. Inventing a price for either would move the proxy
and the breadth counts (R7).
"""

from datetime import timedelta

import pandas as pd

from quantdesk.derived.store import DerivedStore

COLUMNS = ["ts", "members_total", "members_present", "tv", "adv", "dec", "above_vwap", "top5_ret"]


def _typical(bars: pd.DataFrame) -> pd.Series:
    return (bars["high"] + bars["low"] + bars["close"]) / 3.0


def _top_weights(prior_value: dict[str, float], members: set[str], top_n: int) -> dict[str, float]:
    """The `top_n` members with the largest traded value in the previous session (R5).

    Ties break on the symbol, so two builds of the same data give the same table.
    """
    ranked = sorted((s for s in prior_value if s in members), key=lambda s: (-prior_value[s], s))
    return {s: prior_value[s] for s in ranked[:top_n]}


def member_breadth(day_bars: pd.DataFrame, members: set[str], prior_value: dict[str, float],
                   top_n: int) -> pd.DataFrame:
    """One session's minutes, walked in order: each stock carries its open, last close and own VWAP."""
    bars = day_bars[day_bars["target"].isin(members)].sort_values(["ts", "target"])
    # A recorder started mid-session cannot know a stock's first minute's volume (it differences the day's
    # running total), so it stores NA. That minute adds no traded value.
    bars = bars.assign(volume=pd.to_numeric(bars["volume"], errors="coerce").astype("float64").fillna(0.0))
    weights = _top_weights(prior_value, members, top_n)
    seen: dict[str, dict] = {}
    rows = []
    for ts, minute in bars.groupby("ts", sort=True):
        tv = 0.0
        for row in minute.itertuples():
            value = (row.high + row.low + row.close) / 3.0 * row.volume
            state = seen.get(row.target)
            if state is None:
                state = seen[row.target] = {"open": row.open, "close": row.close, "pv": 0.0, "v": 0.0}
            state["close"] = row.close
            state["pv"] += value
            state["v"] += row.volume
            tv += value
        adv = dec = above = 0
        weighted = total = 0.0
        for symbol, state in seen.items():
            adv += state["close"] > state["open"]
            dec += state["close"] < state["open"]
            above += state["v"] > 0 and state["close"] * state["v"] > state["pv"]   # close > pv / v
            weight = weights.get(symbol)
            if weight is not None:
                weighted += weight * (state["close"] / state["open"] - 1.0)
                total += weight
        rows.append({"ts": ts, "members_total": len(members), "members_present": len(minute), "tv": tv,
                     "adv": adv, "dec": dec, "above_vwap": above,
                     "top5_ret": weighted / total if total else float("nan")})
    return pd.DataFrame(rows, columns=COLUMNS)


def _traded_value(bars: pd.DataFrame) -> dict[str, float]:
    """Sum of typical-price × volume per symbol: the next session's top-5 weights."""
    if bars.empty:
        return {}
    return (_typical(bars) * bars["volume"]).groupby(bars["target"]).sum().to_dict()


def build_members_minute(derived: DerivedStore, membership, top_n: int) -> dict:
    """Every session, one query a day.

    Each day's bars are read for every symbol that has ever been a member, so a stock entering the index
    tomorrow already has a traded value to be ranked on; `member_breadth` keeps only today's members.
    """
    symbols = membership.backfill_symbols()
    listing = ", ".join(f"'{s}'" for s in symbols)
    frames = []
    prior_value: dict[str, float] = {}
    for day in sorted(derived.read("sessions", columns="day")["day"]):
        bars = derived.read("minutes", where=f"day = '{day}' and target in ({listing})")
        rows = member_breadth(bars, {membership.listing(s) for s in membership.members_on(day)},
                              prior_value, top_n)
        rows["day"] = day
        rows["available_at"] = rows["ts"] + timedelta(minutes=1)
        frames.append(rows)
        prior_value = _traded_value(bars)
    return derived.write_frame("members_minute", pd.concat(frames, ignore_index=True))
