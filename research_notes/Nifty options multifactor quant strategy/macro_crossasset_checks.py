"""Calendar, event-day and cross-asset checks on Nifty daily data (2015 to Oct 2026).

Uses the Yahoo daily files already in data/ (NSEI, INDIAVIX, GSPC, BZ_F, INR_X).
Descriptive statistics only; no out-of-sample test. Overlapping/serial issues not corrected.
"""
from pathlib import Path
import sys
import numpy as np
import pandas as pd

DATA = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent.parent / "data"
START = "2015-01-01"
pd.set_option("display.width", 200)


def load(name):
    df = pd.read_csv(DATA / f"{name}_daily.csv", index_col=0, parse_dates=True)
    df = df[["Open", "High", "Low", "Close"]].dropna()
    return df[df.index >= START]


n = load("NSEI")
vix = load("INDIAVIX")["Close"].rename("vix")
spx = load("GSPC")["Close"]
brent = load("BZ_F")["Close"]
inr = load("INR_X")["Close"]

n["prev_close"] = n["Close"].shift(1)
n = n.dropna()
n["artefact"] = (n["Open"] == n["prev_close"])  # Yahoo sometimes copies prev close into open
n["cc"] = n["Close"] / n["prev_close"] - 1
n["gap"] = np.where(n["artefact"], np.nan, n["Open"] / n["prev_close"] - 1)
n["oc"] = np.where(n["artefact"], np.nan, n["Close"] / n["Open"] - 1)
n["rng"] = np.where(n["artefact"], np.nan, (n["High"] - n["Low"]) / n["Open"])
n = n.join(vix.shift(1).rename("vix_prev"), how="left")
n["vix_prev"] = n["vix_prev"].ffill()
n["imp1d"] = n["vix_prev"] / 100 / np.sqrt(252)          # VIX-implied 1-day sd
n["rng_over_imp"] = n["rng"] / n["imp1d"]
n["abscc_over_imp"] = n["cc"].abs() / n["imp1d"]


def last_before(series, dates):
    """Value of a foreign series' daily return on its last session strictly before each Nifty date."""
    r = series.pct_change()
    idx = series.index
    out = []
    for d in dates:
        pos = idx.searchsorted(d) - 1
        out.append(r.iloc[pos] if pos >= 1 else np.nan)
    return pd.Series(out, index=dates)


n["spx_prev"] = last_before(spx, n.index)
n["brent_prev"] = last_before(brent, n.index)
n["inr_prev"] = last_before(inr, n.index)       # USDINR up = rupee weaker
inr_r = inr.pct_change()
n["inr_same"] = inr_r.reindex(n.index)           # Yahoo INR=X bar overlaps the Indian session: coincident
br_r = brent.pct_change()
n["brent_same"] = br_r.reindex(n.index)


def stats(df, col="cc"):
    s = df[col].dropna()
    return pd.Series({
        "N": len(s),
        "mean_%": s.mean() * 100,
        "t": s.mean() / (s.std() / np.sqrt(len(s))) if len(s) > 2 else np.nan,
        "P(up)_%": (s > 0).mean() * 100,
    })


def block(title):
    print("\n" + "=" * 90 + "\n" + title + "\n" + "=" * 90)


print(f"Nifty rows {n.index.min().date()} to {n.index.max().date()}: {len(n)}; open==prevclose artefact share {n['artefact'].mean():.1%}")

# ---------------------------------------------------------------- 1. day of week
block("1. Day-of-week (cc = close-to-close, gap, oc = open-to-close, rng = (H-L)/O, rng/imp = range vs VIX-implied 1-day sd)")
periods = {
    "2015-2019": ("2015-01-01", "2019-12-31"),
    "2020-2024": ("2020-01-01", "2024-12-31"),
    "2025-01..2025-08": ("2025-01-01", "2025-08-31"),
    "TueExpiry 2025-09..": ("2025-09-01", "2030-01-01"),
}
for name, (a, b) in periods.items():
    sub = n.loc[a:b]
    g = sub.groupby(sub.index.dayofweek)
    t = pd.DataFrame({
        "N": g["cc"].count(),
        "cc_mean%": g["cc"].mean() * 100,
        "cc_t": g["cc"].apply(lambda s: s.mean() / (s.std() / np.sqrt(len(s)))),
        "P(cc>0)%": g["cc"].apply(lambda s: (s > 0).mean() * 100),
        "gap%": g["gap"].mean() * 100,
        "oc%": g["oc"].mean() * 100,
        "P(oc>0)%": g["oc"].apply(lambda s: (s.dropna() > 0).mean() * 100),
        "rng%": g["rng"].mean() * 100,
        "rng/imp": g["rng_over_imp"].mean(),
        "|cc|/imp": g["abscc_over_imp"].mean(),
    })
    t.index = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][: len(t)] if len(t) <= 5 else t.index
    print(f"\n-- {name}")
    print(t.round(3).to_string())

# ---------------------------------------------------------------- 2. turn of month
block("2. Turn-of-month: TOM = last trading day of month + first 3 trading days")
ym = n.index.to_period("M")
rank_fwd = n.groupby(ym).cumcount()                       # 0 = first trading day
rank_bwd = n.groupby(ym).cumcount(ascending=False)        # 0 = last trading day
n["tom"] = (rank_fwd <= 2) | (rank_bwd == 0)
n["day1"] = rank_fwd == 0
n["last"] = rank_bwd == 0
for name, (a, b) in {"2015-2019": ("2015", "2019"), "2020-2026": ("2020", "2026"), "ALL": ("2015", "2026")}.items():
    sub = n.loc[a:b]
    rows = {
        "TOM": stats(sub[sub["tom"]]),
        "non-TOM": stats(sub[~sub["tom"]]),
        "first day": stats(sub[sub["day1"]]),
        "last day": stats(sub[sub["last"]]),
    }
    print(f"\n-- {name}")
    print(pd.DataFrame(rows).T.round(3).to_string())
    tom_sum = sub.loc[sub["tom"], "cc"].pipe(lambda s: np.log1p(s).sum())
    all_sum = np.log1p(sub["cc"]).sum()
    print(f"   share of total log return earned on TOM days: {tom_sum/all_sum:.0%} (TOM = {sub['tom'].mean():.0%} of days)")

# ---------------------------------------------------------------- 3. holidays
block("3. Pre-/post-holiday (weekday exchange holiday between two sessions)")
dates = n.index
nxt = pd.Series(dates[1:].append(pd.DatetimeIndex([pd.NaT])), index=dates)
prv = pd.Series(pd.DatetimeIndex([pd.NaT]).append(dates[:-1]), index=dates)
pre = []
post = []
for d in dates:
    nd = nxt[d]
    pdv = prv[d]
    pre.append(pd.notna(nd) and np.busday_count((d + pd.Timedelta(days=1)).date(), nd.date()) > 0)
    post.append(pd.notna(pdv) and np.busday_count((pdv + pd.Timedelta(days=1)).date(), d.date()) > 0)
n["pre_hol"] = pre
n["post_hol"] = post
print(pd.DataFrame({
    "pre-holiday cc": stats(n[n["pre_hol"]]),
    "post-holiday cc": stats(n[n["post_hol"]]),
    "post-holiday gap": stats(n[n["post_hol"]], "gap"),
    "post-holiday oc": stats(n[n["post_hol"]], "oc"),
    "other cc": stats(n[~n["pre_hol"] & ~n["post_hol"]]),
}).T.round(3).to_string())
print("   pre-holiday 2020+:")
print(stats(n.loc["2020":][n.loc["2020":, "pre_hol"]]).round(3).to_string())

# ---------------------------------------------------------------- 4. cross-asset
block("4. Cross-asset prior-session moves -> Nifty gap and open-to-close (Pearson corr)")


def corr_table(sub):
    rows = {}
    for x in ["spx_prev", "brent_prev", "inr_prev"]:
        rows[x] = {
            "corr_gap": sub[[x, "gap"]].dropna().corr().iloc[0, 1],
            "corr_oc": sub[[x, "oc"]].dropna().corr().iloc[0, 1],
            "corr_cc": sub[[x, "cc"]].dropna().corr().iloc[0, 1],
        }
    for x in ["inr_same", "brent_same"]:
        rows[x + " (coincident)"] = {
            "corr_gap": np.nan,
            "corr_oc": sub[[x, "oc"]].dropna().corr().iloc[0, 1],
            "corr_cc": sub[[x, "cc"]].dropna().corr().iloc[0, 1],
        }
    return pd.DataFrame(rows).T


for name, (a, b) in {"2015-2019": ("2015", "2019"), "2020-2025": ("2020", "2025"), "2026 YTD": ("2026", "2026"), "ALL": ("2015", "2026")}.items():
    print(f"\n-- {name}")
    print(corr_table(n.loc[a:b]).round(3).to_string())

# multivariate OLS for the gap and the oc move
block("4b. OLS: gap and oc on prior US, Brent, USDINR moves (+ Nifty prior cc). Coeffs in % per 1% move")


def ols(y, X):
    d = pd.concat([y, X], axis=1).dropna()
    yy = d.iloc[:, 0].values
    XX = np.column_stack([np.ones(len(d)), d.iloc[:, 1:].values])
    beta, *_ = np.linalg.lstsq(XX, yy, rcond=None)
    resid = yy - XX @ beta
    s2 = resid @ resid / (len(d) - XX.shape[1])
    cov = s2 * np.linalg.inv(XX.T @ XX)
    se = np.sqrt(np.diag(cov))
    r2 = 1 - resid.var() / yy.var()
    names = ["const"] + list(d.columns[1:])
    return pd.DataFrame({"beta": beta, "t": beta / se}, index=names), r2, len(d)


n["cc_prev"] = n["cc"].shift(1)
for name, (a, b) in {"ALL": ("2015", "2026"), "2026 YTD": ("2026", "2026")}.items():
    sub = n.loc[a:b]
    for yname in ["gap", "oc"]:
        res, r2, N = ols(sub[yname], sub[["spx_prev", "brent_prev", "inr_prev", "cc_prev"]])
        print(f"\n-- {name}  y={yname}  N={N}  R2={r2:.3f}")
        print(res.round(3).to_string())

# ---------------------------------------------------------------- 5. shock size -> range
block("5. Does the size of the overnight shock predict the Nifty intraday range beyond VIX? (rng/imp = range / VIX-implied 1d sd)")
for x, bins in [("spx_prev", [0, 0.005, 0.01, 0.015, 0.025, 1]), ("brent_prev", [0, 0.01, 0.02, 0.03, 0.05, 1]), ("gap", [0, 0.002, 0.005, 0.01, 0.02, 1])]:
    sub = n.dropna(subset=[x, "rng"])
    b = pd.cut(sub[x].abs(), bins, include_lowest=True)
    g = sub.groupby(b, observed=True)
    print(f"\n-- |{x}| buckets")
    print(pd.DataFrame({
        "N": g["rng"].count(),
        "rng%": g["rng"].mean() * 100,
        "rng/imp": g["rng_over_imp"].mean(),
        "|oc|%": g["oc"].apply(lambda s: s.abs().mean() * 100),
        "P(oc>0)%": g["oc"].apply(lambda s: (s.dropna() > 0).mean() * 100),
        "mean oc%": g["oc"].mean() * 100,
    }).round(3).to_string())

# conditional direction after big US moves
block("5b. Nifty open-to-close after big prior US moves (fade or follow?)")
for lab, mask in {
    "US <= -1.5%": n["spx_prev"] <= -0.015,
    "US -1.5..-0.5%": (n["spx_prev"] > -0.015) & (n["spx_prev"] <= -0.005),
    "US -0.5..+0.5%": n["spx_prev"].abs() < 0.005,
    "US +0.5..+1.5%": (n["spx_prev"] >= 0.005) & (n["spx_prev"] < 0.015),
    "US >= +1.5%": n["spx_prev"] >= 0.015,
    "Brent >= +3%": n["brent_prev"] >= 0.03,
    "Brent <= -3%": n["brent_prev"] <= -0.03,
}.items():
    sub = n[mask]
    print(f"{lab:18s} N={len(sub):4d}  gap {sub['gap'].mean()*100:+.2f}%  oc {sub['oc'].mean()*100:+.3f}%  P(oc>0) {(sub['oc'].dropna()>0).mean()*100:.1f}%  rng/imp {sub['rng_over_imp'].mean():.2f}")

# ---------------------------------------------------------------- 6. event days
block("6. Union Budget and election-result days (dates hard-coded; weekend sessions may be missing in Yahoo)")
events = {
    "Budget 2015-02-28 (Sat)": "2015-02-28", "Budget 2016-02-29": "2016-02-29", "Budget 2017-02-01": "2017-02-01",
    "Budget 2018-02-01": "2018-02-01", "Interim 2019-02-01": "2019-02-01", "Budget 2019-07-05": "2019-07-05",
    "Budget 2020-02-01 (Sat)": "2020-02-01", "Budget 2021-02-01": "2021-02-01", "Budget 2022-02-01": "2022-02-01",
    "Budget 2023-02-01": "2023-02-01", "Interim 2024-02-01": "2024-02-01", "Budget 2024-07-23": "2024-07-23",
    "Budget 2025-02-01 (Sat)": "2025-02-01", "Budget 2026-02-01 (Sun)": "2026-02-01",
    "Exit polls 2019-05-20": "2019-05-20", "Results 2019-05-23": "2019-05-23",
    "Exit polls 2024-06-03": "2024-06-03", "Results 2024-06-04": "2024-06-04", "Day after 2024-06-05": "2024-06-05",
}
vix_full = load("INDIAVIX")["Close"]
rows = []
for lab, d in events.items():
    d = pd.Timestamp(d)
    if d in n.index:
        r = n.loc[d]
        v_prev = vix_full[vix_full.index < d].iloc[-1]
        v_now = vix_full.get(d, np.nan)
        rows.append([lab, r["cc"] * 100, r["rng"] * 100 if pd.notna(r["rng"]) else np.nan, r["rng_over_imp"], (v_now / v_prev - 1) * 100])
    else:
        rows.append([lab, np.nan, np.nan, np.nan, np.nan])
ev = pd.DataFrame(rows, columns=["event", "cc%", "rng%", "rng/imp", "VIX chg%"]).set_index("event")
print(ev.round(2).to_string())
budget = ev.loc[[k for k in ev.index if "Budget" in k or "Interim" in k]].dropna()
print(f"\nBudget days found: {len(budget)}; mean |cc| {budget['cc%'].abs().mean():.2f}%  mean rng {budget['rng%'].mean():.2f}%  mean rng/imp {budget['rng/imp'].mean():.2f}  mean VIX chg {budget['VIX chg%'].mean():+.1f}%")
print(f"All days: mean |cc| {n['cc'].abs().mean()*100:.2f}%  mean rng {n['rng'].mean()*100:.2f}%  mean rng/imp {n['rng_over_imp'].mean():.2f}")

# ---------------------------------------------------------------- 7. rolling correlations, regime
block("7. Rolling 250-day correlation of Nifty daily (cc) with same-day USDINR and prior-day Brent; yearly")
yr = n.groupby(n.index.year)
print(pd.DataFrame({
    "corr(cc, INR same day)": yr.apply(lambda d: d[["cc", "inr_same"]].dropna().corr().iloc[0, 1]),
    "corr(cc, Brent same day)": yr.apply(lambda d: d[["cc", "brent_same"]].dropna().corr().iloc[0, 1]),
    "corr(gap, Brent prev)": yr.apply(lambda d: d[["gap", "brent_prev"]].dropna().corr().iloc[0, 1]),
    "corr(gap, US prev)": yr.apply(lambda d: d[["gap", "spx_prev"]].dropna().corr().iloc[0, 1]),
    "corr(oc, US prev)": yr.apply(lambda d: d[["oc", "spx_prev"]].dropna().corr().iloc[0, 1]),
}).round(3).to_string())

# ---------------------------------------------------------------- 8. significance of expiry-day and post-holiday effects
block("8. Expiry weekday and post-holiday open-to-close: N, mean%, t, P(up)%, binomial p vs 46.7% base")
from scipy import stats as st
def tt(s):
    s = s.dropna(); return len(s), s.mean()*100, s.mean()/(s.std()/np.sqrt(len(s))), (s>0).mean()*100, st.binomtest(int((s>0).sum()), len(s), 0.467).pvalue
print("Expiry-weekday open-to-close (N, mean%, t, P(up)%, binom p vs 46.7%)")
for lab,a,b,wd in [("Thu 2019-02..2025-08 (Nifty weekly expiry)", "2019-02-11","2025-08-31",3),
                   ("Tue 2019-02..2025-08 (non-expiry)", "2019-02-11","2025-08-31",1),
                   ("Tue 2025-09.. (Nifty expiry)", "2025-09-01","2030",1),
                   ("Thu 2025-09.. (Sensex expiry)", "2025-09-01","2030",3),
                   ("Mon/Wed/Fri 2025-09..", "2025-09-01","2030",None)]:
    sub = n.loc[a:b]
    sub = sub[sub.index.dayofweek.isin([0,2,4])] if wd is None else sub[sub.index.dayofweek==wd]
    print(f"  {lab:45s}", ["%.3f"%x for x in tt(sub['oc'])])
    print(f"  {'   cc':45s}", ["%.3f"%x for x in tt(sub['cc'])])
print("\nPost-holiday open-to-close by subperiod")
for a,b in [("2015","2019"),("2020","2026")]:
    sub=n.loc[a:b]; sub=sub[sub['post_hol']]
    print(f"  {a}-{b}: oc", ["%.3f"%x for x in tt(sub['oc'])], " gap", ["%.3f"%x for x in tt(sub['gap'])])
print("\nAll-days oc baseline", ["%.3f"%x for x in tt(n['oc'])])
# Year 2026 regime: Brent prev up >2% vs down
sub=n.loc["2026"]
for lab,m in [("2026 Brent prev >= +2%", sub['brent_prev']>=0.02),("2026 Brent prev <= -2%", sub['brent_prev']<=-0.02)]:
    s=sub[m]; print(f"{lab}: N={len(s)} gap {s['gap'].mean()*100:+.2f}% cc {s['cc'].mean()*100:+.2f}% oc {s['oc'].mean()*100:+.3f}%")
# VIX level regimes and range/implied
print("\nrng/imp by VIX-prev bucket")
b=pd.cut(n['vix_prev'],[0,12,15,18,22,100]); print(n.groupby(b,observed=True)[['rng_over_imp','abscc_over_imp']].mean().round(2).to_string())

# ---------------------------------------------------------------- 9. RBI MPC and FOMC event days
block("9. RBI MPC decision days and FOMC days (dates hard-coded: RBI 2016-2025 from memory, 2026 from rbi.org.in; FOMC from memory). VERIFY DATES.")
vix_full = load("INDIAVIX")["Close"]
n["vix_chg"] = (vix_full.reindex(n.index) / vix_full.shift(1).reindex(n.index) - 1)
# RBI scheduled MPC decision dates (recalled; 2026 from RBI site). Unscheduled 2020-03-27, 2020-05-22, 2022-05-04 excluded.
rbi = """2016-10-04 2016-12-07 2017-02-08 2017-04-06 2017-06-07 2017-08-02 2017-10-04 2017-12-06 2018-02-07 2018-04-05
2018-06-06 2018-08-01 2018-10-05 2018-12-05 2019-02-07 2019-04-04 2019-06-06 2019-08-07 2019-10-04 2019-12-05 2020-02-06
2020-08-06 2020-10-09 2020-12-04 2021-02-05 2021-04-07 2021-06-04 2021-08-06 2021-10-08 2021-12-08 2022-02-10 2022-04-08
2022-06-08 2022-08-05 2022-09-30 2022-12-07 2023-02-08 2023-04-06 2023-06-08 2023-08-10 2023-10-06 2023-12-08 2024-02-08
2024-04-05 2024-06-07 2024-08-08 2024-10-09 2024-12-06 2025-02-07 2025-04-09 2025-06-06 2025-08-06 2025-10-01 2025-12-05
2026-04-08 2026-06-05 2026-08-05""".split()
fomc = """2015-01-28 2015-03-18 2015-04-29 2015-06-17 2015-07-29 2015-09-17 2015-10-28 2015-12-16 2016-01-27 2016-03-16 2016-04-27
2016-06-15 2016-07-27 2016-09-21 2016-11-02 2016-12-14 2017-02-01 2017-03-15 2017-05-03 2017-06-14 2017-07-26 2017-09-20 2017-11-01
2017-12-13 2018-01-31 2018-03-21 2018-05-02 2018-06-13 2018-08-01 2018-09-26 2018-11-08 2018-12-19 2019-01-30 2019-03-20 2019-05-01
2019-06-19 2019-07-31 2019-09-18 2019-10-30 2019-12-11 2020-01-29 2020-04-29 2020-06-10 2020-07-29 2020-09-16 2020-11-05 2020-12-16
2021-01-27 2021-03-17 2021-04-28 2021-06-16 2021-07-28 2021-09-22 2021-11-03 2021-12-15 2022-01-26 2022-03-16 2022-05-04 2022-06-15
2022-07-27 2022-09-21 2022-11-02 2022-12-14 2023-02-01 2023-03-22 2023-05-03 2023-06-14 2023-07-26 2023-09-20 2023-11-01 2023-12-13
2024-01-31 2024-03-20 2024-05-01 2024-06-12 2024-07-31 2024-09-18 2024-11-07 2024-12-18 2025-01-29 2025-03-19 2025-05-07 2025-06-18
2025-07-30 2025-09-17 2025-10-29 2025-12-10 2026-01-28 2026-03-18 2026-04-29 2026-06-17 2026-07-29 2026-09-16""".split()
idx = n.index
def pos_on_or_after(d):
    return idx.searchsorted(pd.Timestamp(d))
def summarize(label, rows):
    df = pd.DataFrame(rows)
    base = {"cc": n["cc"], "gap": n["gap"], "oc": n["oc"], "rng_over_imp": n["rng_over_imp"], "abscc_over_imp": n["abscc_over_imp"], "vix_chg": n["vix_chg"]}
    print(f"\n{label}: N={len(df)}")
    for c in ["cc", "gap", "oc", "rng_over_imp", "abscc_over_imp", "vix_chg"]:
        s = df[c].dropna(); b = base[c].dropna()
        t = (s.mean() - b.mean()) / np.sqrt(s.var()/len(s) + b.var()/len(b))
        extra = f" P(>0) {(s>0).mean()*100:5.1f}% (all {(b>0).mean()*100:4.1f}%)" if c in ("cc","oc","gap") else ""
        mult = 100 if c in ("cc","gap","oc","vix_chg") else 1
        print(f"   {c:15s} event mean {s.mean()*mult:+.3f}  all-days {b.mean()*mult:+.3f}  diff-t {t:+.2f}{extra}")
def collect(dates, offset):
    rows = []
    for d in dates:
        p = pos_on_or_after(d)
        if p >= len(idx) or idx[p] != pd.Timestamp(d) and offset == 0:
            pass
        q = p + offset
        if 0 <= q < len(idx):
            rows.append(n.iloc[q][["cc","gap","oc","rng_over_imp","abscc_over_imp","vix_chg"]])
    return rows
rbi_in = [d for d in rbi if pd.Timestamp(d) in idx]
print("RBI dates found in Nifty data:", len(rbi_in), "of", len(rbi))
summarize("RBI day -1 (pre-announcement session)", collect(rbi_in, -1))
summarize("RBI day 0 (decision day; gap is pre-announcement)", collect(rbi_in, 0))
summarize("RBI day +1", collect(rbi_in, 1))
for a,b in [("2016","2019"),("2020","2026")]:
    sub=[d for d in rbi_in if a<=d[:4]<=b]
    summarize(f"RBI day 0 {a}-{b}", collect(sub, 0))
# FOMC: announcement after Indian close on the FOMC date (US). Indian session on FOMC date = 'pre' ; next Indian session = 'post'
pre_rows=[]; post_rows=[]
for d in fomc:
    D=pd.Timestamp(d)
    p = idx.searchsorted(D)          # first Indian session on/after D
    if p < len(idx) and idx[p]==D:
        pre_rows.append(n.iloc[p][["cc","gap","oc","rng_over_imp","abscc_over_imp","vix_chg"]]); post=p+1
    else:
        post=p                          # FOMC date was an Indian holiday
    if post < len(idx): post_rows.append(n.iloc[post][["cc","gap","oc","rng_over_imp","abscc_over_imp","vix_chg"]])
summarize("FOMC: Indian session on FOMC day (pre-announcement, 'pre-FOMC drift' test)", pre_rows)
summarize("FOMC: next Indian session (post-announcement)", post_rows)
pre15=[r for d,r in zip(fomc,pre_rows) if d>="2016"]
