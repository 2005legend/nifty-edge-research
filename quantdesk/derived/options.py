"""Option chains, the expiry calendar and the FII position ratio (design §5.2).

`options_eod`: every stored bhavcopy parsed into one table, NIFTY from NSE and SENSEX from BSE (R11). A
file published on the evening of d is knowledge on the morning of the next session, so `available_at` is
that session at 09:00 IST. `traded` separates rows that actually dealt from rows carrying only a close.

`expiries`: for each session day, the two nearest expiries and their lots, read from the latest chain
strictly before that day. NSE has no file for 2021-03-30, a real trading day, so the lookup must fall back.

`fii_ratio`: FIIs' share of index-futures longs, from the participant-wise OI file, same 09:00 rule.
"""

from bisect import bisect_left, bisect_right
from datetime import date, datetime, time, timedelta

import duckdb
import pandas as pd

from quantdesk.clock import IST
from quantdesk.derived.store import DerivedStore
from quantdesk.eod.bhavcopy import _existing, parse_fo_contracts
from quantdesk.eod.flows import fii_index_futures_long_ratio, parse_participant_oi
from quantdesk.pricing.surface import future_sessions
from quantdesk.storage import Store

EXCHANGES = {"NIFTY": "NSE", "SENSEX": "BSE"}
MORNING = time(9, 0)
EXPIRY_COLUMNS = ["symbol", "day", "expiry_1", "expiry_2", "lot_1", "lot_2", "is_expiry_day", "available_at"]


def _frame_from_contracts(rows: pd.DataFrame) -> pd.DataFrame:
    """Untraded rows keep a close but no real price, so every fit filters on this flag (design §5.2)."""
    rows = rows.copy()
    rows["traded"] = rows["volume"] > 0
    return rows


def _session_days(derived: DerivedStore) -> list[date]:
    return sorted(derived.read("sessions", columns="day")["day"])


def actual_expiry(listed: date, sessions) -> date:
    """The last session on or before the listed expiry: a contract whose expiry day becomes a holiday expires the
    session before (NSE and BSE rule). The old bhavcopy layout carries only the listed date, so 2023-06-29
    (Bakri Id, moved at short notice) shows there although the contracts expired on 2023-06-28. A date past the
    end of `sessions` is left alone."""
    sessions = list(sessions)
    if not sessions or listed > sessions[-1]:
        return listed
    at = bisect_right(sessions, listed)
    return sessions[at - 1] if at else listed


def _next_morning(day: date, sessions: list[date]) -> datetime:
    """09:00 IST on the session after `day`, or on the next calendar day once the calendar ends.

    `sessions` only covers days already traded, so the newest file has no next session. Nothing reads a
    table on a day that is not a session, so the calendar-day fallback is never read early.
    """
    at = bisect_right(sessions, day)
    following = sessions[at] if at < len(sessions) else day + timedelta(days=1)
    return datetime.combine(following, MORNING, tzinfo=IST)


def _modal_lot(lots: pd.Series) -> int | None:
    counts = lots.dropna().value_counts()
    return int(counts.index[0]) if len(counts) else None


def build_options_eod(store: Store, derived: DerivedStore, urls: dict, nifty_from: date,
                      sensex_from: date, holidays=frozenset()) -> dict:
    """Parse every stored bhavcopy, a year at a time: the whole table does not fit in one frame.

    `expiry` is the actual expiry (`actual_expiry`): recorded sessions, then the published holiday calendar for
    expiries not yet reached. `expiry_listed` keeps the date the file printed."""
    sessions = _session_days(derived)
    calendar = future_sessions(sessions, set(holidays), sessions[-1] + timedelta(days=400)) if sessions else ()
    rolled: dict[date, date] = {}
    first_day = {"NIFTY": nifty_from, "SENSEX": sensex_from}
    by_year: dict[int, list[pd.DataFrame]] = {}
    for day in sessions:
        for symbol, exchange in EXCHANGES.items():
            if day < first_day[symbol]:
                continue
            path = _existing(store, day, urls, exchange)
            if path is None:  # not published: the chain for that day is simply missing
                continue
            rows = _frame_from_contracts(parse_fo_contracts(path, symbols=(symbol,)))
            rows["expiry_listed"] = rows["expiry"]
            rows["expiry"] = rows["expiry"].map(
                lambda e: rolled.setdefault(e, actual_expiry(e, calendar)) if pd.notna(e) else e)
            rows["day"] = day
            rows["available_at"] = _next_morning(day, sessions)
            by_year.setdefault(day.year, []).append(rows)
    con = duckdb.connect()
    queries = {}
    for year, frames in sorted(by_year.items()):
        con.register(f"y{year}", pd.concat(frames, ignore_index=True))
        queries[f"year={year}"] = f"select * from y{year}"
    return derived.write_parts("options_eod", con, queries)


def build_expiries(derived: DerivedStore) -> dict:
    """One row per session day and symbol, from the chain published the evening before."""
    eod = derived.read("options_eod", columns="day, symbol, expiry, lot")
    chains: dict[date, dict[str, list[tuple[date, int | None]]]] = {}
    for (day, symbol), group in eod.groupby(["day", "symbol"], sort=True):
        lots = group.groupby("expiry")["lot"].agg(_modal_lot)
        chains.setdefault(day, {})[symbol] = sorted(lots.items())
    published = sorted(chains)
    rows = []
    for day in _session_days(derived):
        at = bisect_left(published, day)
        if at == 0:  # no chain was published before the first session
            continue
        for symbol, chain in chains[published[at - 1]].items():
            ahead = [entry for entry in chain if entry[0] >= day]
            if not ahead:
                continue
            second = ahead[1] if len(ahead) > 1 else (None, None)
            rows.append({"symbol": symbol, "day": day, "expiry_1": ahead[0][0], "lot_1": ahead[0][1],
                         "expiry_2": second[0], "lot_2": second[1],
                         "is_expiry_day": any(expiry == day for expiry, _ in chain),
                         "available_at": datetime.combine(day, MORNING, tzinfo=IST)})
    frame = pd.DataFrame(rows, columns=EXPIRY_COLUMNS)
    for column in ("lot_1", "lot_2"):
        frame[column] = frame[column].astype("Int64")
    return derived.write_frame("expiries", frame)


def build_fii_ratio(store: Store, derived: DerivedStore) -> dict:
    sessions = _session_days(derived)
    rows = []
    for day in sessions:
        name = f"fao_participant_oi_{day:%d%m%Y}.csv"
        if not store.raw_exists("participant_oi", day, name):
            continue
        ratio = fii_index_futures_long_ratio(parse_participant_oi(store.raw_path("participant_oi", day, name)))
        rows.append({"day": day, "ratio": ratio, "available_at": _next_morning(day, sessions)})
    return derived.write_frame("fii_ratio", pd.DataFrame(rows, columns=["day", "ratio", "available_at"]))
