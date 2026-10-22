"""The early pricing pre-check (owner's choice B, 22 Oct 2026): the model against real option prices before the
recorder has the R17 data.

Angel One serves 1-minute candles for option contracts that are still listed. This module measures the model
on them with R17's own metric (`price_errors`): median |model move - actual move| / max(|actual move|, 2 ticks)
over 15, 30 and 60 minutes and to the exit.

It is an early warning only. It does not replace R17:
- **no expiry days:** a listed contract has not expired yet
- **trades, not quotes:** a candle's close is the minute's last trade, used as bid = ask = mid
- **stale minutes are absent:** only minutes with a trade have a candle

It costs no trial and gates nothing.
"""

from datetime import date, datetime, time, timedelta

import pandas as pd

from quantdesk.instruments import UNDERLYING_SEGMENTS, _options, atm_strike
from quantdesk.pricing.pricecheck import price_errors
from quantdesk.pricing.quotes import ModelQuotes

HORIZONS = [15, 30, 60, "exit"]


def pick_contracts(master: pd.DataFrame, underlying: str, today: date, spot: float, width: int = 5,
                   n_expiries: int = 3) -> list[dict]:
    """Calls and puts within `width` strikes of the money, for the next `n_expiries` expiries."""
    chain = _options(master, underlying)
    chain = chain[chain["expiry"].map(lambda e: pd.notna(e) and e >= today)]
    out = []
    for expiry in sorted(chain["expiry"].unique())[:n_expiries]:
        rows = chain[chain["expiry"] == expiry]
        strikes = sorted(rows["strike"].unique())
        centre = strikes.index(atm_strike(spot, strikes))
        for strike in strikes[max(0, centre - width): centre + width + 1]:
            for side in ("CE", "PE"):
                match = rows[(rows["strike"] == strike) & rows["symbol"].str.endswith(side)]
                if len(match):
                    out.append({"token": str(match["token"].iloc[0]), "symbol": match["symbol"].iloc[0],
                                "exchange": UNDERLYING_SEGMENTS[underlying][0], "underlying": underlying,
                                "expiry": expiry, "strike": float(strike), "side": side})
    return out


def candle_records(candles: pd.DataFrame, contracts: list[dict], frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Candles in the recorder's snapshot layout (`price_errors`): minute, token, bid = ask = close, contract, spot."""
    meta = pd.DataFrame(contracts)[["token", "underlying", "expiry", "strike", "side"]]
    rec = candles.rename(columns={"ts": "minute"}).merge(meta, on="token")
    rec = rec.assign(bid=rec["close"], ask=rec["close"])
    spots = pd.concat([f.set_index("ts")["close"].rename(index) for index, f in frames.items()], axis=1)
    rec["spot"] = [spots[u].get(m, float("nan")) if u in spots else float("nan")
                   for u, m in zip(rec["underlying"], rec["minute"])]
    return rec.dropna(subset=["spot"]).assign(mid=lambda f: f["close"])


def run_precheck(candles: pd.DataFrame, contracts: list[dict], frames: dict[str, pd.DataFrame], clock, surface,
                 h: dict) -> tuple[pd.DataFrame, dict]:
    quotes = ModelQuotes(frames, surface, clock, h)

    def model_mid(underlying, expiry, strike, side, at):
        try:
            return quotes.mid(underlying, expiry, strike, side, at)
        except (KeyError, ValueError):          # no index bar at that minute, or past the expiry
            return float("nan")

    rec = candle_records(candles, contracts, frames)
    days = sorted({m.date() for m in rec["minute"]})
    errors = price_errors(rec.drop(columns=["mid"]), model_mid, HORIZONS, {d: False for d in days})
    errors = errors.dropna(subset=["err"])
    by_horizon = {str(k): float(v) for k, v in errors.groupby(errors["horizon"].astype(str))["err"].median().items()}
    by_index = {k: float(v) for k, v in errors.groupby("underlying")["err"].median().items()}
    summary = {"median_error": float(errors["err"].median()) if len(errors) else float("nan"),
               "by_horizon": by_horizon, "by_index": by_index, "rows": int(len(errors)), "days": len(days),
               "contracts": int(rec["token"].nunique()) if len(rec) else 0}
    return errors, summary


def index_frames(derived, days: list[date]) -> dict[str, pd.DataFrame]:
    """Index close with VIX, minute by minute, from the derived `minutes` table."""
    if not days:
        return {}
    where = f"day >= DATE '{min(days)}' and day <= DATE '{max(days)}'"
    rows = derived.read("minutes", where=f"target in ('NIFTY', 'SENSEX', 'INDIAVIX') and {where}",
                        columns="target, ts, close")
    vix = rows[rows["target"] == "INDIAVIX"].set_index("ts")["close"].rename("vix")
    out = {}
    for index in ("NIFTY", "SENSEX"):
        close = rows[rows["target"] == index].set_index("ts")["close"]
        if len(close):
            out[index] = pd.concat([close, vix], axis=1).sort_index().ffill().dropna().reset_index()
    return out


def fetch_candles(client, contracts: list[dict], start: datetime, end: datetime) -> pd.DataFrame:
    """1-minute candles for each contract; a contract Angel returns nothing for is skipped."""
    from quantdesk.history.backfill import Target, _fetch

    frames = []
    for c in contracts:
        target = Target(c["symbol"], c["exchange"], c["token"], "ONE_MINUTE", start.date())
        try:
            frame, _ = _fetch(client, target, start, end)
        except Exception:  # noqa: BLE001 - one contract failing does not stop the check
            continue
        if frame is not None and len(frame):
            frames.append(frame.assign(token=c["token"]))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def report_text(summary: dict, start: date, end: date, data_hash: str, max_error: float) -> str:
    lines = ["# Early pricing pre-check (not R17)", "",
             f"- data_hash `{data_hash}`; option candles {start} to {end}",
             f"- {summary['contracts']} contracts, {summary['days']} sessions, {summary['rows']} measured moves", "",
             "| measure | median error |", "|---|---|",
             f"| all | {summary['median_error']:.3f} |"]
    lines += [f"| horizon {k} | {v:.3f} |" for k, v in summary["by_horizon"].items()]
    lines += [f"| {k} | {v:.3f} |" for k, v in summary["by_index"].items()]
    verdict = "within" if summary["median_error"] <= max_error else "OUTSIDE"
    lines += ["", f"R17's pass mark is {max_error:.2f}. This early read is **{verdict}** it.", "",
              "Not a substitute for R17. There are no expiry days (listed contracts have not expired), and the "
              "prices are last trades, not quotes. The trials still wait for the recorded check.", ""]
    return "\n".join(lines)
