"""The pricing check on what the recorder captured (R17): option snapshots against the frozen model.

The recorder's minute snapshots give each option's bid and ask. Its index and VIX bars feed the same
`ModelQuotes` the backtest uses, so the check measures exactly the model the trials will price with. The
token-to-contract map is `option_meta`; NSE reuses tokens, so the map is read per day.
"""

from datetime import date, datetime, time

import pandas as pd

from quantdesk.pricing.pricecheck import check_result, price_errors
from quantdesk.pricing.quotes import ModelQuotes

INDEX_TOKENS = {"NIFTY": "99926000", "SENSEX": "99919000"}
VIX_TOKEN = "99926017"
EXPECTED = {"NIFTY": 360, "SENSEX": 360}
FULL_SHARE = 0.95


def _day(value) -> date:
    return value.date() if hasattr(value, "date") else value


def recorded_days(store) -> list[date]:
    snaps = store.read("option_snapshots")
    return sorted({_day(d) for d in snaps["date"]}) if len(snaps) else []


def _frames(bars: pd.DataFrame) -> dict[str, pd.DataFrame]:
    vix = bars[bars["token"] == VIX_TOKEN].set_index("minute")["close"].rename("vix")
    out = {}
    for index, token in INDEX_TOKENS.items():
        rows = bars[bars["token"] == token].set_index("minute")["close"]
        if len(rows):
            frame = pd.concat([rows, vix], axis=1).sort_index().ffill().dropna().reset_index()
            out[index] = frame.rename(columns={"minute": "ts"})
    return out


def run_pricecheck(store, clock, surface, h) -> tuple[pd.DataFrame, dict]:
    errors, sessions = [], {k: {"sessions": 0, "expiry_days": 0} for k in INDEX_TOKENS}
    for day in recorded_days(store):
        snaps, meta, bars = store.read("option_snapshots", day), store.read("option_meta", day), store.read("bars", day)
        if snaps.empty or meta.empty or bars.empty:
            continue
        meta = meta.sort_values("subscribed_at").drop_duplicates("token", keep="last")
        frames = _frames(bars)
        quotes = ModelQuotes(frames, surface, clock, h)
        for index, frame in frames.items():
            full = len(frame) >= FULL_SHARE * EXPECTED[index]
            expiry_today = bool((meta.loc[meta["underlying"] == index, "expiry"] == day).any())
            if full:
                sessions[index]["sessions"] += 1
                sessions[index]["expiry_days"] += int(expiry_today)
            rec = snaps.merge(meta[meta["underlying"] == index][["token", "underlying", "expiry", "strike", "side"]],
                              on="token")
            spot = frame.set_index("ts")["close"]
            rec = rec.assign(spot=rec["minute"].map(spot)).dropna(subset=["spot"])
            if rec.empty:
                continue

            def model_mid(underlying, expiry, strike, side, at, _q=quotes):
                try:
                    return _q.mid(underlying, expiry, strike, side, at)
                except (KeyError, ValueError):          # no recorded bar at that minute, or past the expiry
                    return float("nan")

            day_errors = price_errors(rec, model_mid, [15, 30, 60, "exit"], {day: expiry_today})
            errors.append(day_errors.dropna(subset=["err"]))
    table = pd.concat(errors, ignore_index=True) if errors else pd.DataFrame(columns=["err"])
    return table, check_result(table, sessions, h)
