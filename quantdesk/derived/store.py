"""data/derived: tables rebuilt deterministically from data/raw, never edited by hand.

Each table is Parquet under data/derived/<name>/ (one file, or Hive partitions). manifest.json keeps each
table's row count and a content hash that ignores row order; `data_hash` combines them, and the trial
registry records it as the data a trial ran on (R32).
"""

import hashlib
import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path

import duckdb
import pandas as pd

from quantdesk.clock import IST


class DerivedStore:
    def __init__(self, root: Path):
        self.root = Path(root)

    def _dir(self, name: str) -> Path:
        return self.root / name

    def glob(self, name: str) -> str:
        return (self._dir(name) / "**" / "*.parquet").as_posix()

    def exists(self, name: str) -> bool:
        return self._dir(name).exists() and any(self._dir(name).rglob("*.parquet"))

    def write_frame(self, name: str, df: pd.DataFrame) -> dict:
        con = duckdb.connect()
        con.register("frame", df)
        return self.write_query(name, con, "select * from frame")

    def write_query(self, name: str, con, sql: str, partition_by: str | None = None) -> dict:
        """Run `sql` on `con` and store the result as table `name`, replacing any earlier build."""
        self.root.mkdir(parents=True, exist_ok=True)
        staging = self.root / f".{name}.{uuid.uuid4().hex[:8]}"
        staging.mkdir()
        target = staging.as_posix()
        if partition_by:
            con.execute(f"copy ({sql}) to '{target}' (format parquet, partition_by ({partition_by}))")
        else:
            con.execute(f"copy ({sql}) to '{target}/part-0.parquet' (format parquet)")
        final = self._dir(name)
        if final.exists():
            shutil.rmtree(final)
        staging.rename(final)
        return self._record(name)

    def write_parts(self, name: str, con, queries: dict) -> dict:
        """Store table `name` from one query per Hive partition, e.g. {"year=2019": sql, ...}: a large table
        is built a slice at a time instead of in one query that has to fit in memory."""
        self.root.mkdir(parents=True, exist_ok=True)
        staging = self.root / f".{name}.{uuid.uuid4().hex[:8]}"
        for part, sql in queries.items():
            folder = staging / part
            folder.mkdir(parents=True)
            con.execute(f"copy ({sql}) to '{(folder / 'part-0.parquet').as_posix()}' (format parquet)")
        final = self._dir(name)
        if final.exists():
            shutil.rmtree(final)
        staging.rename(final)
        return self._record(name)

    def read(self, name: str, where: str | None = None, columns: str = "*") -> pd.DataFrame:
        sql = f"select {columns} from read_parquet('{self.glob(name)}', hive_partitioning=true)"
        if where:
            sql += f" where {where}"
        result = duckdb.connect().execute(sql)
        dates = [d[0] for d in result.description if str(d[1]) == "DATE"]
        frame = result.df()
        for column in dates:  # DuckDB hands DATE back as timestamps; keep them dates
            frame[column] = frame[column].dt.date
        return frame

    def _record(self, name: str) -> dict:
        rel = f"read_parquet('{self.glob(name)}', hive_partitioning=true)"
        con = duckdb.connect()
        rows, total = con.execute(f"select count(*), coalesce(sum(hash(t)::hugeint), 0) from {rel} t").fetchone()
        digest = hashlib.sha256(f"{rows}:{int(total) % 2**64}".encode()).hexdigest()[:16]
        manifest = self.manifest()
        manifest[name] = {"rows": int(rows), "hash": digest, "built_at": datetime.now(IST).isoformat(timespec="seconds")}
        (self.root / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        return manifest[name]

    def manifest(self) -> dict:
        path = self.root / "manifest.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    def data_hash(self) -> str:
        """One hash over every table's content hash: the registry's 'data hash'."""
        parts = sorted(f"{name}:{entry['hash']}" for name, entry in self.manifest().items())
        return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]
