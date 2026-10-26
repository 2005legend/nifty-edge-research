"""Implied volatility from real option prices (SP5): the ATM pair, the put-call-parity forward, and the IV of
every strike of one expiry.

Prices are bhavcopy closes (each contract's last traded price). Out-of-the-money options carry the surface, as is
standard: their prices are the liquid side and hold the most time value. Time to expiry is the business clock's,
so these IVs are directly comparable with everything else in the system.
"""

import math

import pandas as pd

from quantdesk.black76 import implied_vol


def atm_strike(rows: pd.DataFrame) -> float | None:
    """The strike whose call and put (both traded) are closest in price: the market's at-the-money."""
    traded = rows[rows["traded"].fillna(False).astype(bool)]
    calls = traded[traded["option_type"] == "CE"].set_index("strike")["close"]
    puts = traded[traded["option_type"] == "PE"].set_index("strike")["close"]
    both = calls.index.intersection(puts.index)
    if not len(both):
        return None
    return float((calls.loc[both] - puts.loc[both]).abs().idxmin())


def parity_forward(rows: pd.DataFrame, strike: float) -> float:
    c = float(rows[(rows["strike"] == strike) & (rows["option_type"] == "CE")]["close"].iloc[0])
    p = float(rows[(rows["strike"] == strike) & (rows["option_type"] == "PE")]["close"].iloc[0])
    return strike + c - p


def chain_ivs(rows: pd.DataFrame, F: float, T: float, max_log_moneyness: float = 0.1) -> pd.DataFrame:
    """IV of each traded out-of-the-money option (calls above F, puts below) within |ln K/F| <= the limit."""
    out = []
    for r in rows[rows["traded"].fillna(False).astype(bool)].itertuples():
        m = math.log(float(r.strike) / F)
        otm = (r.option_type == "CE" and r.strike >= F) or (r.option_type == "PE" and r.strike <= F)
        if not otm or abs(m) > max_log_moneyness or T <= 0:
            continue
        try:
            iv = implied_vol(float(r.close), F, float(r.strike), T, kind="call" if r.option_type == "CE" else "put")
        except ValueError:                      # below intrinsic or above the ceiling: a stale or bad print
            continue
        if iv > 1e-3:
            out.append({"strike": float(r.strike), "kind": r.option_type, "close": float(r.close),
                        "log_moneyness": m, "iv": iv})
    return pd.DataFrame(out, columns=["strike", "kind", "close", "log_moneyness", "iv"])
