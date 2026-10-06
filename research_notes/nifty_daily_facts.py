"""Basic statistics on Nifty 50 daily data, 2015 to today.

Checks a few research claims on Indian data:
  1. Where Nifty's return comes from: overnight (close to open) or intraday (open to close)
  2. Base rates and persistence of daily direction
  3. India VIX implied move vs the move that actually happened (volatility risk premium)
  4. Whether gaps continue or fade during the day
  5. Whether the US session predicts the Nifty gap and the Nifty intraday move
  6. A trend filter (50-day moving average) and the 5-day forward return

Run: .venv/Scripts/python research_notes/nifty_daily_facts.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"
START = "2015-01-01"


def load(name):
    df = pd.read_csv(DATA / f"{name}_daily.csv", index_col=0, parse_dates=True)
    df = df[["Open", "High", "Low", "Close"]].dropna()
    # Yahoo sometimes repeats the close as the open on index data; drop those rows
    return df[df.index >= START]


nifty = load("NSEI")
vix = load("INDIAVIX")
spx = load("GSPC")

n = nifty.copy()
n["prev_close"] = n["Close"].shift(1)
n["overnight"] = n["Open"] / n["prev_close"] - 1
n["intraday"] = n["Close"] / n["Open"] - 1
n["daily"] = n["Close"] / n["prev_close"] - 1
n = n.dropna()
bad_open = (n["Open"] == n["prev_close"]).mean()

print("=" * 72)
print(f"Nifty 50 daily data {n.index.min().date()} to {n.index.max().date()}, {len(n)} days")
print(f"(share of days where open == previous close, a data artefact: {bad_open:.1%})")

# 1. Overnight vs intraday decomposition
print("\n1. Return decomposition (log-sum, % per year)")
g = n.groupby(n.index.year)
dec = pd.DataFrame({
    "overnight_%": g["overnight"].apply(lambda s: np.log1p(s).sum() * 100),
    "intraday_%": g["intraday"].apply(lambda s: np.log1p(s).sum() * 100),
    "total_%": g["daily"].apply(lambda s: np.log1p(s).sum() * 100),
    "intraday_up_days_%": g["intraday"].apply(lambda s: (s > 0).mean() * 100),
})
print(dec.round(1).to_string())
print(f"ALL: overnight {np.log1p(n['overnight']).sum()*100:.1f}%  "
      f"intraday {np.log1p(n['intraday']).sum()*100:.1f}%  "
      f"mean overnight {n['overnight'].mean()*100:.3f}%/day  mean intraday {n['intraday'].mean()*100:.3f}%/day")

# 2. Direction base rates and persistence
print("\n2. Direction base rates")
up = n["daily"] > 0
print(f"P(up day) = {up.mean():.1%}   -> 'always predict up' accuracy")
print(f"P(up | yesterday up) = {up[up.shift(1) == True].mean():.1%}   "
      f"P(up | yesterday down) = {up[up.shift(1) == False].mean():.1%}")
upi = n["intraday"] > 0
print(f"P(intraday close>open) = {upi.mean():.1%}")

# 3. VIX implied move vs realised move
print("\n3. India VIX implied move vs realised (volatility risk premium)")
v = vix["Close"].reindex(n.index).ffill().shift(1)  # VIX known at previous close
implied_1d = v / 100 / np.sqrt(252)
real_1d = n["daily"].abs()
ok = implied_1d.notna()
print(f"Mean implied 1-day sd {implied_1d[ok].mean()*100:.3f}%  vs mean |actual move| {real_1d[ok].mean()*100:.3f}% "
      f"(normal dist: E|x| = 0.798*sd -> {0.798*implied_1d[ok].mean()*100:.3f}%)")
print(f"Days with |move| > implied 1-sd: {(real_1d[ok] > implied_1d[ok]).mean():.1%} (normal ~31.7%)")
print(f"Days with |move| > implied 2-sd: {(real_1d[ok] > 2*implied_1d[ok]).mean():.1%} (normal ~4.6%)")
# weekly (5-day) realised vs VIX
rv20 = n["daily"].rolling(21).std().shift(-21) * np.sqrt(252) * 100  # next-month realised vol
vrp = (v - rv20).dropna()
print(f"VIX minus next-21d realised vol: mean {vrp.mean():.2f} vol pts, median {vrp.median():.2f}, "
      f"positive {(vrp > 0).mean():.1%} of days")
by_year = vrp.groupby(vrp.index.year).agg(["mean", lambda s: (s > 0).mean()])
by_year.columns = ["VRP_mean_volpts", "share_positive"]
print(by_year.round(2).to_string())

# 4. Gap continuation vs fade
print("\n4. Gap behaviour (does the open-to-close move follow the gap?)")
for lo, hi, label in [(0.005, 1, "gap up > +0.5%"), (-1, -0.005, "gap down < -0.5%"),
                      (-0.002, 0.002, "flat open |gap| < 0.2%")]:
    m = (n["overnight"] > lo) & (n["overnight"] < hi)
    s = n.loc[m, "intraday"]
    print(f"{label:24s} N={m.sum():4d}  P(close>open)={(s > 0).mean():.1%}  mean intraday {s.mean()*100:+.3f}%")

# 5. US session -> Nifty gap and intraday
print("\n5. US S&P 500 previous session -> Nifty")
spx_ret = spx["Close"].pct_change()
# for each Nifty day, take the most recent completed US session before the Indian open
us_prev = spx_ret.reindex(n.index - pd.Timedelta(days=1), method="ffill")
us_prev.index = n.index
both = pd.DataFrame({"us": us_prev, "gap": n["overnight"], "intra": n["intraday"]}).dropna()
print(f"corr(US prev day, Nifty gap)      = {both['us'].corr(both['gap']):.2f}")
print(f"corr(US prev day, Nifty intraday) = {both['us'].corr(both['intra']):.2f}")
print(f"P(gap sign == US sign) = {(np.sign(both['us']) == np.sign(both['gap'])).mean():.1%}")
print(f"P(intraday sign == US sign) = {(np.sign(both['us']) == np.sign(both['intra'])).mean():.1%}")

# 6. Trend filter: 50-DMA and forward 5-day return
print("\n6. Trend filter: close vs 50-day MA -> next 5-day return")
n["ma50"] = n["Close"].rolling(50).mean()
n["fwd5"] = n["Close"].shift(-5) / n["Close"] - 1
t = n.dropna(subset=["ma50", "fwd5"])
for label, m in [("above 50DMA", t["Close"] > t["ma50"]), ("below 50DMA", t["Close"] <= t["ma50"])]:
    s = t.loc[m, "fwd5"]
    print(f"{label}: N={m.sum()}  P(fwd5>0)={(s > 0).mean():.1%}  mean {s.mean()*100:+.2f}%  sd {s.std()*100:.2f}%")

# 7. VIX regime -> next 5-day absolute move
print("\n7. VIX regime -> size of the next 5-day move")
t = t.join(vix["Close"].rename("vix"), how="left")
t["vix_bucket"] = pd.cut(t["vix"], [0, 12, 15, 18, 22, 100], labels=["<12", "12-15", "15-18", "18-22", ">22"])
print(t.groupby("vix_bucket", observed=True)["fwd5"].agg(
    N="count", mean_abs_pct=lambda s: s.abs().mean() * 100, p_up=lambda s: (s > 0).mean() * 100).round(2).to_string())

# 8. Weekly expiry window: VIX-implied weekly range vs actual (5 trading days ahead)
print("\n8. Weekly window: does Nifty stay inside the VIX-implied 1-sd weekly range?")
w = n[["Close"]].join(vix["Close"].rename("vix"), how="left").dropna()
w["implied_wk"] = w["vix"] / 100 / np.sqrt(52)
w["fwd5"] = w["Close"].shift(-5) / w["Close"] - 1
w = w.dropna()
inside = w["fwd5"].abs() < w["implied_wk"]
print(f"All days since 2015: inside 1-sd weekly range {inside.mean():.1%} (normal ~68.3%), "
      f"inside 0.5-sd {(w['fwd5'].abs() < 0.5*w['implied_wk']).mean():.1%} (normal ~38.3%)")
recent = w[w.index >= "2025-09-01"]
print(f"Since Tuesday expiry (Sep 2025): N={len(recent)}  inside 1-sd {(recent['fwd5'].abs() < recent['implied_wk']).mean():.1%}  "
      f"mean |5d move| {recent['fwd5'].abs().mean()*100:.2f}% vs mean implied {recent['implied_wk'].mean()*100:.2f}%")
