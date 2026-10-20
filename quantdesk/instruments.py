"""Angel One instrument master: download, load, expiries and option-chain tokens.

Expiry dates always come from the master (never calendar arithmetic), so holiday-shifted
expiries are handled automatically.
"""

import io
import json
from datetime import date, datetime
from pathlib import Path
from typing import Sequence

import pandas as pd

from quantdesk.storage import Store

# underlying -> (derivatives segment, cash/index segment)
UNDERLYING_SEGMENTS = {"NIFTY": ("NFO", "NSE"), "SENSEX": ("BFO", "BSE")}
MASTER_NAME = "master.json"


def download_master(store: Store, http_get, day: date, url: str) -> tuple[Path, bool]:
    """Save today's master as raw data. On failure, fall back to the newest earlier copy."""
    if store.raw_exists("instruments", day, MASTER_NAME):
        return store.raw_path("instruments", day, MASTER_NAME), False
    try:
        response = http_get(url)
        if getattr(response, "status_code", 200) != 200:
            raise ConnectionError(f"HTTP {response.status_code}")
        json.loads(response.content)  # must be valid JSON before it is stored
        return store.write_raw("instruments", day, MASTER_NAME, response.content), False
    except Exception:  # noqa: BLE001 - any failure falls back to the cache
        folder = store.root / "raw" / "instruments"
        earlier = sorted(p for p in folder.glob(f"*/{MASTER_NAME}") if p.parent.name < day.isoformat()) \
            if folder.exists() else []
        if not earlier:
            raise
        return earlier[-1], True


def _parse_expiry(value: str):
    if not value:
        return pd.NaT
    try:
        return datetime.strptime(value, "%d%b%Y").date()
    except ValueError:
        return pd.NaT


def load_master(path: Path) -> pd.DataFrame:
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    frame = pd.DataFrame(rows)
    frame["token"] = frame["token"].astype(str)
    frame["expiry"] = frame["expiry"].map(_parse_expiry)
    frame["strike"] = pd.to_numeric(frame["strike"], errors="coerce") / 100.0
    frame["tick_size"] = pd.to_numeric(frame["tick_size"], errors="coerce") / 100.0
    frame["lotsize"] = pd.to_numeric(frame["lotsize"], errors="coerce").fillna(0).astype(int)
    return frame


def _options(master: pd.DataFrame, underlying: str) -> pd.DataFrame:
    segment = UNDERLYING_SEGMENTS[underlying][0]
    mask = (master["name"] == underlying) & (master["instrumenttype"] == "OPTIDX") & (master["exch_seg"] == segment)
    return master[mask]


def option_expiries(master: pd.DataFrame, underlying: str, today: date, n: int = 2) -> list[date]:
    expiries = sorted({e for e in _options(master, underlying)["expiry"] if pd.notna(e) and e >= today})
    return expiries[:n]


def atm_strike(spot: float, strikes: Sequence[float]) -> float:
    return min(strikes, key=lambda s: (abs(s - spot), s))


def chain_tokens(master: pd.DataFrame, underlying: str, expiry: date, atm: float, width: int) -> pd.DataFrame:
    chain = _options(master, underlying)
    chain = chain[chain["expiry"] == expiry]
    strikes = sorted(chain["strike"].unique())
    if not strikes:
        return pd.DataFrame(columns=["strike", "ce_token", "pe_token", "lotsize", "tick_size"])
    centre = strikes.index(atm_strike(atm, strikes))
    chosen = strikes[max(0, centre - width): centre + width + 1]
    out = []
    for strike in chosen:
        rows = chain[chain["strike"] == strike]
        ce = rows[rows["symbol"].str.endswith("CE")]
        pe = rows[rows["symbol"].str.endswith("PE")]
        out.append({
            "strike": strike,
            "ce_token": ce["token"].iloc[0] if len(ce) else None,
            "pe_token": pe["token"].iloc[0] if len(pe) else None,
            "lotsize": int(rows["lotsize"].iloc[0]),
            "tick_size": float(rows["tick_size"].iloc[0]),
        })
    return pd.DataFrame(out)


def current_future(master: pd.DataFrame, underlying: str, today: date) -> pd.Series:
    segment = UNDERLYING_SEGMENTS[underlying][0]
    futures = master[(master["name"] == underlying) & (master["instrumenttype"] == "FUTIDX")
                     & (master["exch_seg"] == segment)]
    futures = futures[futures["expiry"].map(lambda e: pd.notna(e) and e >= today)]
    return futures.sort_values("expiry").iloc[0]


def nifty50_symbols(csv_bytes: bytes) -> list[str]:
    frame = pd.read_csv(io.BytesIO(csv_bytes))
    return [str(s).strip() for s in frame["Symbol"]]


def equity_tokens(master: pd.DataFrame, symbols: list[str]) -> dict[str, str]:
    cash = master[master["exch_seg"] == "NSE"].set_index("symbol")["token"]
    return {s: cash[f"{s}-EQ"] for s in symbols if f"{s}-EQ" in cash.index}
