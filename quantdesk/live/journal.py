"""The trade journal (SP3 design S5): SQLite at data/journal.sqlite.

Everything the live system says and everything the owner does is a row:
- alerts, and the owner's took/skipped choice
- real fills and exits, typed in by the owner
- paper trades
- stop ratchets
- events: locks, unlocks with their reasons, shadow pauses, kill-switch firings, overrides

Nothing is deleted. The monitoring statistics and the dashboard read from here.
"""

import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

RISK = 400.0
SCHEMA = """
create table if not exists alerts (
    id integer primary key, at text, idx text, side text, mode text, status text default 'new',
    expiry text, strike real, kind text, lot integer, entry_limit real, index_stop real, index_target real,
    backstop_trigger real, backstop_limit real, p real, ev real, delta real, reasons_for text,
    reasons_against text, signal_id text, updated_at text);
create table if not exists paper_trades (
    id integer primary key, alert_id integer, entry_at text, entry_premium real, exit_at text, exit_premium real,
    reason text, pnl real, r real);
create table if not exists real_trades (
    id integer primary key, alert_id integer, fill_at text, fill_premium real, exit_at text, exit_premium real,
    pnl real, r real, notes text);
create table if not exists ratchets (id integer primary key, alert_id integer, at text, index_stop real, trigger real);
create table if not exists events (id integer primary key, at text, kind text, detail text);
create table if not exists state (key text primary key, value text);
"""


def _iso(at) -> str:
    return at.isoformat() if hasattr(at, "isoformat") else str(at)


class Journal:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._db() as db:
            db.executescript(SCHEMA)

    def _db(self):
        return sqlite3.connect(self.path)

    def _query(self, sql: str, params=()) -> pd.DataFrame:
        with self._db() as db:
            return pd.read_sql_query(sql, db, params=params)

    def add_alert(self, a: dict) -> int:
        fields = ["at", "idx", "side", "mode", "expiry", "strike", "kind", "lot", "entry_limit", "index_stop",
                  "index_target", "backstop_trigger", "backstop_limit", "p", "ev", "delta", "reasons_for",
                  "reasons_against", "signal_id"]
        values = [_iso(a["at"]), a["index"]] + [a.get(f) if f != "expiry" else str(a.get(f)) for f in fields[2:]]
        with self._db() as db:
            cur = db.execute(f"insert into alerts ({', '.join(fields)}) values ({', '.join('?' * len(fields))})", values)
            return int(cur.lastrowid)

    def set_alert_status(self, alert_id: int, status: str) -> None:
        with self._db() as db:
            db.execute("update alerts set status = ?, updated_at = ? where id = ?",
                       (status, datetime.now().isoformat(timespec="seconds"), alert_id))

    def alerts(self, day: str | None = None) -> pd.DataFrame:
        if day:
            return self._query("select * from alerts where substr(at, 1, 10) = ? order by at", (day,))
        return self._query("select * from alerts order by at")

    def add_real_fill(self, alert_id: int, premium: float, at) -> int:
        with self._db() as db:
            cur = db.execute("insert into real_trades (alert_id, fill_at, fill_premium) values (?, ?, ?)",
                             (alert_id, _iso(at), premium))
            return int(cur.lastrowid)

    def close_real(self, real_id: int, exit_premium: float, at, pnl: float, notes: str = "") -> None:
        with self._db() as db:
            db.execute("update real_trades set exit_at = ?, exit_premium = ?, pnl = ?, r = ?, notes = ? where id = ?",
                       (_iso(at), exit_premium, pnl, pnl / RISK, notes, real_id))

    def real_trades(self) -> pd.DataFrame:
        return self._query("select * from real_trades order by fill_at")

    def open_paper(self, alert_id: int, entry_at, entry_premium: float) -> int:
        with self._db() as db:
            cur = db.execute("insert into paper_trades (alert_id, entry_at, entry_premium) values (?, ?, ?)",
                             (alert_id, _iso(entry_at), entry_premium))
            return int(cur.lastrowid)

    def close_paper(self, paper_id: int, exit_at, exit_premium: float, reason: str, pnl: float) -> None:
        with self._db() as db:
            db.execute("update paper_trades set exit_at = ?, exit_premium = ?, reason = ?, pnl = ?, r = ? where id = ?",
                       (_iso(exit_at), exit_premium, reason, pnl, pnl / RISK, paper_id))

    def open_papers(self) -> pd.DataFrame:
        return self._query("select p.*, a.* , p.id as paper_id from paper_trades p join alerts a on a.id = p.alert_id "
                           "where p.exit_at is null")

    def closed_trades(self, kind: str = "paper") -> pd.DataFrame:
        table = "paper_trades" if kind == "paper" else "real_trades"
        order = "exit_at"
        return self._query(f"select * from {table} where exit_at is not null order by {order}")

    def add_ratchet(self, alert_id: int, at, index_stop: float, trigger: float) -> None:
        with self._db() as db:
            db.execute("insert into ratchets (alert_id, at, index_stop, trigger) values (?, ?, ?, ?)",
                       (alert_id, _iso(at), index_stop, trigger))

    def ratchets(self, alert_id: int) -> pd.DataFrame:
        return self._query("select * from ratchets where alert_id = ? order by at", (alert_id,))

    def log_event(self, kind: str, detail: str, at=None) -> None:
        with self._db() as db:
            db.execute("insert into events (at, kind, detail) values (?, ?, ?)",
                       (_iso(at or datetime.now()), kind, detail))

    def events(self) -> pd.DataFrame:
        return self._query("select * from events order by id")

    def set_state(self, key: str, value: str) -> None:
        with self._db() as db:
            db.execute("insert into state (key, value) values (?, ?) on conflict(key) do update set value = excluded.value",
                       (key, value))

    def get_state(self, key: str, default: str | None = None) -> str | None:
        rows = self._query("select value from state where key = ?", (key,))
        return rows.loc[0, "value"] if len(rows) else default
