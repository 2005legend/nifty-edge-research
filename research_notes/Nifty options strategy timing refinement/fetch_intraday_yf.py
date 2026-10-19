"""Download and cache free Yahoo Finance intraday data for entry-timing research.

Yahoo keeps 1-minute bars for ~30 days (max 7 days per request), 5/15-minute
bars for ~60 days and 60-minute bars for ~730 days. Because the history rolls
off, every run APPENDS to the cached CSVs in data/intraday_yf/ (deduplicated),
so re-running weekly builds a longer 1-minute archive over time.

Run from the project root:
    .venv/Scripts/python "research_notes/Nifty options strategy timing refinement/fetch_intraday_yf.py"
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "intraday_yf"
OUT.mkdir(parents=True, exist_ok=True)

TICKERS = {
    "NSEI": "^NSEI",        # Nifty 50 spot index (no volume on Yahoo)
    "BSESN": "^BSESN",      # Sensex spot index
    "INDIAVIX": "^INDIAVIX",  # India VIX (30-day, monthly-option based)
    "NIFTYBEES": "NIFTYBEES.NS",  # Nifty ETF, used only as a volume proxy
}


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    idx = df.index
    if idx.tz is None:
        idx = idx.tz_localize("UTC")
    df.index = idx.tz_convert("Asia/Kolkata").tz_localize(None)
    df.index.name = "ts"
    return df[[c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]]


def _merge_save(name: str, interval: str, new: pd.DataFrame) -> pd.DataFrame:
    path = OUT / f"{name}_{interval}.csv"
    if path.exists():
        old = pd.read_csv(path, index_col=0, parse_dates=True)
        new = pd.concat([old, new])
    new = new[~new.index.duplicated(keep="last")].sort_index()
    new.to_csv(path)
    return new


def fetch_1m(ticker: str) -> pd.DataFrame:
    end = dt.datetime.now()
    frames = []
    for k in range(5):  # 5 x 7-day windows ~ 30 days (Yahoo limit)
        e = end - dt.timedelta(days=7 * k)
        s = e - dt.timedelta(days=7)
        try:
            df = yf.download(ticker, start=s, end=e, interval="1m",
                             progress=False, auto_adjust=False, prepost=False)
            frames.append(_clean(df))
        except Exception as exc:  # noqa: BLE001
            print(f"  1m window {k} failed for {ticker}: {exc}")
    frames = [f for f in frames if not f.empty]
    return pd.concat(frames) if frames else pd.DataFrame()


def main() -> None:
    for name, tk in TICKERS.items():
        print(f"== {name} ({tk})")
        d1 = fetch_1m(tk)
        if not d1.empty:
            d1 = _merge_save(name, "1m", d1)
            print(f"  1m : {len(d1):6d} rows {d1.index.min()} -> {d1.index.max()}")
        for interval, period in [("5m", "60d"), ("15m", "60d"), ("60m", "730d")]:
            try:
                df = _clean(yf.download(tk, period=period, interval=interval,
                                        progress=False, auto_adjust=False))
            except Exception as exc:  # noqa: BLE001
                print(f"  {interval} failed: {exc}")
                continue
            if df.empty:
                print(f"  {interval}: empty")
                continue
            df = _merge_save(name, interval, df)
            print(f"  {interval:3s}: {len(df):6d} rows {df.index.min()} -> {df.index.max()}")


if __name__ == "__main__":
    main()
