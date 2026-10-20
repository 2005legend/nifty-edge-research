"""Storage under data/.

- raw/<source>/<YYYY-MM-DD>/<name>          original downloads, never overwritten
- raw/<kind>/date=<YYYY-MM-DD>/part-*.parquet  append-only Parquet parts
- reports/<kind>/<YYYY-MM-DD>.json         derived run reports (may be rewritten)
"""

import json
import os
import uuid
from datetime import date, datetime
from pathlib import Path

import duckdb
import pandas as pd


class RawExistsError(FileExistsError):
    """Raised when a raw file would be overwritten."""


class Store:
    def __init__(self, root: Path):
        self.root = Path(root)

    # raw original files -------------------------------------------------
    def raw_path(self, source: str, day: date, name: str) -> Path:
        return self.root / "raw" / source / day.isoformat() / name

    def raw_exists(self, source: str, day: date, name: str) -> bool:
        return self.raw_path(source, day, name).exists()

    def write_raw(self, source: str, day: date, name: str, content: bytes) -> Path:
        path = self.raw_path(source, day, name)
        if path.exists():
            raise RawExistsError(str(path))
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "xb") as f:
            f.write(content)
        return path

    # append-only parquet parts --------------------------------------------
    def _kind_dir(self, kind: str) -> Path:
        return self.root / "raw" / kind

    def append_parquet(self, kind: str, day: date, df: pd.DataFrame) -> Path:
        folder = self._kind_dir(kind) / f"date={day.isoformat()}"
        folder.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%H%M%S%f")
        path = folder / f"part-{stamp}-{uuid.uuid4().hex[:8]}.parquet"
        tmp = path.with_suffix(".tmp")  # readers glob *.parquet, so a half-written file is invisible
        try:
            df.to_parquet(tmp, index=False)
            os.replace(tmp, path)
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise
        return path

    def _parquet_glob(self, kind: str, day: date | None) -> str | None:
        folder = self._kind_dir(kind)
        if day is not None:
            folder = folder / f"date={day.isoformat()}"
        if not folder.exists() or not any(folder.rglob("*.parquet")):
            return None
        return (folder / "**" / "*.parquet").as_posix()

    def read(self, kind: str, day: date | None = None) -> pd.DataFrame:
        pattern = self._parquet_glob(kind, day)
        if pattern is None:
            return pd.DataFrame()
        query = f"select * from read_parquet('{pattern}', hive_partitioning=true, union_by_name=true)"
        return duckdb.sql(query).df()

    def connect(self) -> duckdb.DuckDBPyConnection:
        con = duckdb.connect()
        raw = self.root / "raw"
        if raw.exists():
            for folder in sorted(p for p in raw.iterdir() if p.is_dir()):
                pattern = self._parquet_glob(folder.name, None)
                if pattern is not None:
                    con.sql(
                        f"create view \"{folder.name}\" as select * from read_parquet("
                        f"'{pattern}', hive_partitioning=true, union_by_name=true)"
                    )
        return con

    # derived reports ------------------------------------------------------
    def _report_file(self, kind: str, day: date) -> Path:
        return self.root / "reports" / kind / f"{day.isoformat()}.json"

    def write_report(self, kind: str, day: date, data: dict) -> Path:
        path = self._report_file(kind, day)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        return path

    def read_report(self, kind: str, day: date) -> dict | None:
        path = self._report_file(kind, day)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
