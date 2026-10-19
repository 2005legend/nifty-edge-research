"""
Regime-timing measurements for the Nifty noise-band breakout system (daily-data proxy).

Run:  .venv/Scripts/python.exe "research_notes/Nifty options strategy timing refinement/regime_timing_measure.py"
Output is printed and also written to regime_timing_measure_output.txt next to this script.

What it measures (all regime variables are known before the open of day t):
  A. A daily OHLC proxy of the Zarattini noise-band breakout (hold to close, no VWAP trail,
     entry exactly at the band), and how its payoff varies by regime: India VIX level and
     percentile, VIX-of-VIX proxy, realised-vol percentile, VRP, 200-DMA, drawdown,
     daily autocorrelation, recent trendiness, prior US session, oil and rupee shocks, year.
  B. "Switch off" vs "raise the hurdle" (band multiplier 1.0 -> 1.5) vs "always on" by regime.
  C. Strategy momentum: does the proxy's own trailing P&L predict its next-period P&L?
  D. Detection lag / false alarms of regime detectors (threshold rules, a 2-state statistical
     jump model run online, a variance CUSUM) around Nifty drawdowns of >= 10%.
  E. Structural periods: COVID 2020, 2022 rate hikes, SEBI reforms (Nov 2024), Tuesday expiry
     (Sep 2025), 2026 war/oil shock.

Caveats: the proxy cannot see intraday order of highs and lows, VWAP or the 15-minute check
clock, so it is an upper-level description of when breakouts pay, not a backtest. Days where
both bands were touched are reported separately and, in the "conservative" variant, booked as
a loss of one noise unit (an assumption).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
OUT = Path(__file__).with_name("regime_timing_measure_output.txt")
_lines = []


def p(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    _lines.append(s)


def load(name):
    df = pd.read_csv(DATA / f"{name}_daily.csv", parse_dates=["Date"]).set_index("Date").sort_index()
    df = df[~df.index.duplicated()]
    return df


pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 30)

n = load("NSEI")
n = n[(n.High > n.Low) & (n.Open > 0)].copy()
vix = load("INDIAVIX")["Close"]
spx = load("GSPC")["Close"]
inr = load("INR_X")["Close"]
brent = load("BZ_F")["Close"]


def asof_before(series, idx):
    """Last value of `series` with date strictly before each date in idx (no look-ahead)."""
    s = series.dropna()
    left = pd.DataFrame({"Date": idx})
    right = pd.DataFrame({"Date": s.index, "v": s.values})
    m = pd.merge_asof(left, right, on="Date", allow_exact_matches=False)
    return pd.Series(m["v"].values, index=idx)


O, H, L, C = n.Open, n.High.copy(), n.Low.copy(), n.Close
H = np.maximum(H, np.maximum(O, C))
L = np.minimum(L, np.minimum(O, C))
Cp = C.shift(1)
r = np.log(C / Cp)

# ------------------------------------------------------------------ A. proxy outcome
move = (C / O - 1).abs()
sig = move.rolling(14).mean().shift(1)  # 14-day mean |close/open - 1|, known before day t


def proxy(vm):
    up = np.maximum(O, Cp) * (1 + vm * sig)
    dn = np.minimum(O, Cp) * (1 - vm * sig)
    hu, hd = H > up, L < dn
    single_long = hu & ~hd
    single_short = hd & ~hu
    both = hu & hd
    pnl = pd.Series(np.nan, index=n.index)
    pnl[single_long] = C[single_long] / up[single_long] - 1
    pnl[single_short] = 1 - C[single_short] / dn[single_short]
    pnl_c = pnl.copy()
    pnl_c[both] = -sig[both]  # assumption: whipsaw day costs one noise unit
    side = pd.Series(0, index=n.index)
    side[single_long] = 1
    side[single_short] = -1
    return pd.DataFrame({"pnl": pnl, "pnl_c": pnl_c, "both": both, "side": side,
                         "trig": single_long | single_short})


P1 = proxy(1.0)
P15 = proxy(1.5)

# ------------------------------------------------------------------ regime variables (known pre-open)
vix_n = vix.reindex(n.index).ffill(limit=3)
vix_prev = vix_n.shift(1)
vix_ret = np.log(vix_n / vix_n.shift(1))


def tpct(x, w=252):
    """Trailing percentile of the latest value within the last w observations (incl. itself)."""
    return x.rolling(w, min_periods=120).apply(lambda a: (a[:-1] < a[-1]).mean() if np.isfinite(a[-1]) else np.nan, raw=True)


R = pd.DataFrame(index=n.index)
R["vix"] = vix_prev
R["vix_pct"] = tpct(vix_n).shift(1)
R["vov"] = vix_ret.rolling(20).std().shift(1) * np.sqrt(252)
R["vov_pct"] = tpct(vix_ret.rolling(20).std()).shift(1)
R["vix5"] = np.log(vix_n / vix_n.shift(5)).shift(1)
rv20 = r.rolling(20).std() * np.sqrt(252) * 100
R["rv20"] = rv20.shift(1)
R["rv_pct"] = tpct(rv20).shift(1)
R["vrp"] = R.vix - R.rv20
R["above200"] = (C > C.rolling(200).mean()).shift(1)
R["dd"] = (C / C.rolling(252, min_periods=60).max() - 1).shift(1)
R["ac60"] = r.rolling(60).apply(lambda a: pd.Series(a).autocorr(1), raw=True).shift(1)
er = ((C - O).abs() / (H - L))
R["er20"] = er.rolling(20).mean().shift(1)
R["spx_prev"] = asof_before(np.log(spx / spx.shift(1)), n.index)
R["brent5"] = asof_before(np.log(brent / brent.shift(5)), n.index)
R["inr5"] = asof_before(np.log(inr / inr.shift(5)), n.index)
R["year"] = n.index.year
trail = P1.pnl_c.fillna(0) / sig  # in noise units
R["trail60"] = trail.rolling(60).sum().shift(1)
R["trail20"] = trail.rolling(20).sum().shift(1)

D = pd.concat([P1, R, sig.rename("sig"), er.rename("er")], axis=1).dropna(subset=["sig", "vix", "rv_pct", "vix_pct"])
D = D.loc["2015-01-01":]
D["pnl_s"] = D.pnl / D.sig
D["pnl_cs"] = D.pnl_c / D.sig
D15 = P15.loc[D.index]
D["pnl15_s"] = D15.pnl / D.sig
D["pnl15_cs"] = D15.pnl_c / D.sig
D["trig15"] = D15.trig
D["both15"] = D15.both

p("=" * 100)
p("Nifty noise-band breakout DAILY PROXY, regime conditioning.  Sample:", D.index.min().date(), "to", D.index.max().date(), " days:", len(D))
p("pnl = hold-to-close from band entry, in % of index (bp) and in noise units (sigma = 14-day mean |C/O-1|).")
p("'cons' books both-band days as -1 sigma.  t = t-stat of mean noise-unit pnl on single-breach days.")
p("=" * 100)


def summarize(g, label, frame=None):
    F = D if frame is None else frame
    rows = []
    for k, d in F.groupby(g, observed=True):
        t = d[d.trig]
        x = t.pnl_s
        cons = d.pnl_cs.dropna()
        tt = stats.ttest_1samp(x, 0).statistic if len(x) > 2 else np.nan
        rows.append({label: k, "days": len(d), "trig%": 100 * d.trig.mean(), "both%": 100 * d.both.mean(),
                     "n": len(t), "mean_bp": 1e4 * t.pnl.mean(), "mean_sig": x.mean(), "t": tt,
                     "hit%": 100 * (x > 0).mean(), "long_sig": t[t.side == 1].pnl_s.mean(),
                     "short_sig": t[t.side == -1].pnl_s.mean(), "cons_sig": cons.mean(),
                     "sig_bp": 1e4 * d.sig.mean(), "ER": d.er.mean()})
    out = pd.DataFrame(rows).set_index(label)
    p(out.round(3).to_string())
    p("-" * 100)
    return out


p("\n[A0] Unconditional")
summarize(pd.Series("all", index=D.index), "all")
p("[A1] By India VIX level at prior close")
summarize(pd.cut(D.vix, [0, 12, 15, 20, 25, 100], right=False), "vix")
p("[A2] By India VIX trailing-252d percentile (prior close)")
summarize(pd.cut(D.vix_pct, [-0.01, 0.33, 0.67, 0.9, 1.01]), "vix_pct")
p("[A3] By VIX-of-VIX proxy (20d stdev of daily log VIX change), trailing percentile")
summarize(pd.cut(D.vov_pct, [-0.01, 0.33, 0.67, 1.01]), "vov_pct")
p("[A4] By 5-day VIX change (log)")
summarize(pd.cut(D.vix5, [-5, -0.1, 0.1, 0.25, 5]), "vix5")
p("[A5] By realised-vol (20d) trailing percentile")
summarize(pd.cut(D.rv_pct, [-0.01, 0.33, 0.67, 0.9, 1.01]), "rv_pct")
p("[A6] By VRP = VIX - RV20 (vol points)")
summarize(pd.cut(D.vrp, [-100, 0, 3, 6, 100]), "vrp")
p("[A7] By trend state: prior close above 200-DMA")
summarize(D.above200, "above200")
p("[A8] By drawdown from 252d high (prior close)")
summarize(pd.cut(D.dd, [-1, -0.10, -0.05, -0.0001, 0.01]), "dd")
p("[A9] By 60d lag-1 autocorrelation of daily returns")
summarize(pd.cut(D.ac60, [-1, -0.1, 0, 0.1, 1]), "ac60")
p("[A10] By recent trendiness: 20d mean of |C-O|/(H-L)")
summarize(pd.qcut(D.er20, 3), "er20")
p("[A11] By prior US session |S&P 500 return|")
summarize(pd.cut(D.spx_prev.abs(), [0, 0.005, 0.01, 0.02, 1]), "abs_spx")
p("[A12] By Brent 5-day change")
summarize(pd.cut(D.brent5, [-5, -0.05, 0.05, 5]), "brent5")
p("[A13] By USD/INR 5-day change")
summarize(pd.cut(D.inr5, [-5, -0.005, 0.005, 0.01, 5]), "inr5")
p("[A14] By year")
yr = summarize(D.year, "year")

# ------------------------------------------------------------------ A15. top-vs-bottom spread tests (multiple-comparison check)
p("[A15] Top vs bottom bucket of each regime variable: difference in mean noise-unit pnl per single-breach trade")
cuts = {"vix_level(<12 vs >=20)": (D.vix < 12, D.vix >= 20),
        "vix_pct(<=.33 vs >.67)": (D.vix_pct <= 0.33, D.vix_pct > 0.67),
        "vov_pct(<=.33 vs >.67)": (D.vov_pct <= 0.33, D.vov_pct > 0.67),
        "vix5(<=-0.1 vs >0.1)": (D.vix5 <= -0.1, D.vix5 > 0.1),
        "rv_pct(<=.33 vs >.67)": (D.rv_pct <= 0.33, D.rv_pct > 0.67),
        "vrp(<=0 vs >6)": (D.vrp <= 0, D.vrp > 6),
        "above200(F vs T)": (D.above200 == False, D.above200 == True),
        "dd(<=-10% vs >-5%)": (D.dd <= -0.10, D.dd > -0.05),
        "ac60(<=0 vs >0.1)": (D.ac60 <= 0, D.ac60 > 0.1),
        "er20(low vs high tercile)": (D.er20 <= D.er20.quantile(1 / 3), D.er20 > D.er20.quantile(2 / 3)),
        "abs_spx(<=0.5% vs >1%)": (D.spx_prev.abs() <= 0.005, D.spx_prev.abs() > 0.01),
        "brent5(<=-5% vs >5%)": (D.brent5 <= -0.05, D.brent5 > 0.05),
        "inr5(<=-0.5% vs >1%)": (D.inr5 <= -0.005, D.inr5 > 0.01)}
nsig = 0
for k, (a, b) in cuts.items():
    xa, xb = D[a & D.trig].pnl_s, D[b & D.trig].pnl_s
    tt = stats.ttest_ind(xb, xa, equal_var=False).statistic
    nsig += abs(tt) > 2
    p(f"  {k:28s} bottom {xa.mean():+.3f} (n={len(xa)})  top {xb.mean():+.3f} (n={len(xb)})  diff {xb.mean()-xa.mean():+.3f}  Welch t {tt:+.2f}")
p(f"  {nsig} of {len(cuts)} spreads have |t|>2; about {0.05*len(cuts):.1f} expected by chance at 5% (cuts are correlated).")
p("-" * 100)

# ------------------------------------------------------------------ A-null. what the proxy shows with NO edge
p("[A-null] Same proxy on simulated driftless Brownian days (375 one-minute steps, empirical gap/sigma ratios)")
rng0 = np.random.default_rng(7)
gap_ratio = (np.log(O / Cp) / sig).loc[D.index].dropna().values
for label, vol_mult in [("constant vol", None), ("vol clustering (empirical sigma path)", True)]:
    Nd = 40000
    if vol_mult:
        sp = (sig / sig.loc[D.index].mean()).loc[D.index].values
        dvol = np.resize(sp, Nd)
    else:
        dvol = np.ones(Nd)
    steps = rng0.standard_normal((Nd, 375)) * (dvol[:, None] / np.sqrt(375)) * 0.01
    paths = np.cumsum(steps, axis=1)
    oc = paths[:, -1]
    hi, lo = np.maximum(paths.max(1), 0), np.minimum(paths.min(1), 0)
    s_band = pd.Series(np.abs(np.expm1(oc))).rolling(14).mean().shift(1).values
    g = np.resize(gap_ratio, Nd) * np.nan_to_num(s_band, nan=0.008)
    O_ = 1.0
    Cp_ = O_ * np.exp(-g)
    C_, H_, L_ = O_ * np.exp(oc), O_ * np.exp(hi), O_ * np.exp(lo)
    up = np.maximum(O_, Cp_) * (1 + s_band)
    dn = np.minimum(O_, Cp_) * (1 - s_band)
    ok = np.isfinite(s_band)
    hu, hd = (H_ > up) & ok, (L_ < dn) & ok
    sl, ss, bb = hu & ~hd, hd & ~hu, hu & hd
    pn = np.where(sl, C_ / up - 1, np.where(ss, 1 - C_ / dn, np.nan))
    ps = pn / s_band
    cons = np.where(bb, -1.0, ps)
    x = ps[sl | ss]
    p(f"  {label:38s}: trig% {100*(sl|ss)[ok].mean():.1f}  both% {100*bb[ok].mean():.1f}  mean_sig {np.nanmean(x):+.3f}"
      f" (se {np.nanstd(x)/np.sqrt(np.isfinite(x).sum()):.3f})  hit% {100*np.nanmean(x>0):.1f}  cons_sig {np.nanmean(cons[(sl|ss|bb)]):+.3f}"
      f"  mean |C-O|/(H-L) {np.mean(np.abs(oc)/(hi-lo)):.3f}")
p("  -> Excess edge = observed mean_sig minus this null. Regime comparisons difference the null out only if the null is regime-invariant.")
p("-" * 100)

# ------------------------------------------------------------------ B. switch-off vs raise hurdle
p("\n[B] Always-on (band x1.0) vs raised hurdle (band x1.5) vs off, by regime (noise units per DAY, cons variant)")
p("    per-day mean includes zero on no-trade days; 'per_trade' = mean over traded days.")


def compare(g, label):
    rows = []
    for k, d in D.groupby(g, observed=True):
        on = d.pnl_cs.fillna(0)
        hi = d.pnl15_cs.fillna(0)
        rows.append({label: k, "days": len(d),
                     "on_per_day": on.mean(), "on_t": stats.ttest_1samp(on, 0).statistic,
                     "on_trades": int(d.trig.sum() + d.both.sum()), "on_per_trade": d.pnl_cs.dropna().mean(),
                     "x1.5_per_day": hi.mean(), "x1.5_t": stats.ttest_1samp(hi, 0).statistic,
                     "x1.5_trades": int(d.trig15.sum() + d.both15.sum()), "x1.5_per_trade": d.pnl15_cs.dropna().mean()})
    p(pd.DataFrame(rows).set_index(label).round(3).to_string())
    p("-" * 100)


compare(pd.cut(D.vix_pct, [-0.01, 0.33, 0.67, 1.01]), "vix_pct")
compare(pd.cut(D.rv_pct, [-0.01, 0.33, 0.67, 1.01]), "rv_pct")
compare(D.above200, "above200")

# ------------------------------------------------------------------ C. strategy momentum / equity curve
p("\n[C] Strategy momentum: does the proxy's own trailing P&L predict the next period? (cons variant, noise units)")
daily = D.pnl_cs.fillna(0)
m = daily.groupby(pd.Grouper(freq="ME")).sum()
mm = pd.DataFrame({"m": m, "prev1": m.shift(1), "prev3": m.rolling(3).sum().shift(1), "prev6": m.rolling(6).sum().shift(1)}).dropna()
for c in ["prev1", "prev3", "prev6"]:
    rho, pv = stats.spearmanr(mm[c], mm.m)
    pos, neg = mm[mm[c] > 0].m, mm[mm[c] <= 0].m
    p(f"  monthly {c:5s} -> next month: Spearman {rho:+.3f} (p={pv:.3f}); next-month mean if trailing>0: {pos.mean():+.3f} (n={len(pos)}), if <=0: {neg.mean():+.3f} (n={len(neg)})")
for w in ["trail20", "trail60"]:
    on = D[D[w] > 0].pnl_cs.dropna()
    off = D[D[w] <= 0].pnl_cs.dropna()
    p(f"  equity-curve filter {w}>0: kept trades n={len(on)} mean {on.mean():+.3f} sig (t={stats.ttest_1samp(on,0).statistic:+.2f}); "
      f"skipped trades n={len(off)} mean {off.mean():+.3f} (t={stats.ttest_1samp(off,0).statistic:+.2f}); Welch diff t={stats.ttest_ind(on,off,equal_var=False).statistic:+.2f}")
# split-sample check
for a, b in [("2015", "2019"), ("2020", "2026")]:
    sub = D.loc[a:b]
    on = sub[sub.trail60 > 0].pnl_cs.dropna()
    off = sub[sub.trail60 <= 0].pnl_cs.dropna()
    p(f"  {a}-{b}: trail60>0 mean {on.mean():+.3f} (n={len(on)}) vs <=0 mean {off.mean():+.3f} (n={len(off)})")

# ------------------------------------------------------------------ D. regime detectors: lag and false alarms
p("\n[D] Regime detectors: detection lag around Nifty drawdowns >= 10% and false-alarm behaviour")
close = C.loc["2014-07-01":]
peak = close.cummax()
ddser = close / peak - 1
episodes = []
in_ep = False
for t, x in ddser.items():
    if not in_ep and x <= -0.10:
        in_ep = True
        pk_date = close.loc[:t][close.loc[:t] == peak.loc[t]].index[-1]
    if in_ep and x >= -0.0001:
        seg = close.loc[pk_date:t]
        episodes.append((pk_date, seg.idxmin(), t))
        in_ep = False
if in_ep:
    seg = close.loc[pk_date:]
    episodes.append((pk_date, seg.idxmin(), None))
p("  Drawdown episodes (peak, trough, recovery):")
for e in episodes:
    p(f"    peak {e[0].date()}  trough {e[1].date()}  depth {close[e[1]]/close[e[0]]-1:+.1%}  recovered {e[2].date() if e[2] is not None else 'not yet'}")

# --- statistical jump model (Nystrup et al. 2020; Shu, Yu & Mulvey 2024 features)
rr = r.loc["2014-01-01":].fillna(0)
neg = np.minimum(rr, 0)
def ewm_dd(hl):
    return np.sqrt((neg ** 2).ewm(halflife=hl).mean())
f = pd.DataFrame({"logdd10": np.log(ewm_dd(10) + 1e-6),
                  "sor20": rr.ewm(halflife=20).mean() / (ewm_dd(20) + 1e-6),
                  "sor60": rr.ewm(halflife=60).mean() / (ewm_dd(60) + 1e-6)}).loc["2014-07-01":]


def jm_dp(X, theta, lam):
    T, K = len(X), len(theta)
    Lc = ((X[:, None, :] - theta[None, :, :]) ** 2).sum(-1)
    V = np.zeros((T, K))
    B = np.zeros((T, K), dtype=int)
    V[0] = Lc[0]
    pen = lam * (1 - np.eye(K))
    for t in range(1, T):
        c = V[t - 1][:, None] + pen  # from j (rows) to k (cols)
        B[t] = c.argmin(0)
        V[t] = Lc[t] + c.min(0)
    s = np.zeros(T, dtype=int)
    s[-1] = V[-1].argmin()
    for t in range(T - 1, 0, -1):
        s[t - 1] = B[t, s[t]]
    online = V.argmin(1)  # filtered state: last state of the optimal path using data up to t
    return s, online, V[-1].min()


def jm_fit(X, lam, n_init=10, seed=0):
    rng = np.random.default_rng(seed)
    best = None
    for _ in range(n_init):
        theta = X[rng.choice(len(X), 2, replace=False)].copy()
        prev = None
        for _ in range(100):
            s, _, obj = jm_dp(X, theta, lam)
            if prev is not None and np.array_equal(s, prev):
                break
            prev = s
            for k in range(2):
                if (s == k).any():
                    theta[k] = X[s == k].mean(0)
        if best is None or obj < best[1]:
            best = (theta.copy(), obj)
    return best[0]


def jm_states(lam, fit_end=None):
    Ftr = f if fit_end is None else f.loc[:fit_end]
    mu, sd = Ftr.mean(), Ftr.std()
    Xtr = ((Ftr - mu) / sd).values
    theta = jm_fit(Xtr, lam)
    bad = int(np.argmin(theta[:, 1] + theta[:, 2]))  # lower Sortino = bad state
    X = ((f - mu) / sd).values
    s, online, _ = jm_dp(X, theta, lam)
    return pd.Series(s == bad, index=f.index), pd.Series(online == bad, index=f.index)


detectors = {}
for lam in [5, 20, 50, 100]:
    smooth, online = jm_states(lam)
    detectors[f"JM online lam={lam} (full-sample fit)"] = online
    if lam == 20:
        expost = smooth
    sm2, on2 = jm_states(lam, fit_end="2019-12-31")
    detectors[f"JM online lam={lam} (fit 2014-19)"] = on2
idx = f.index
detectors["VIX>20 (prior close)"] = (vix_n.reindex(idx) > 20)
detectors["VIX pct>0.80"] = (tpct(vix_n).reindex(idx) > 0.8)
detectors["RV20 pct>0.80"] = (tpct(rv20).reindex(idx) > 0.8)
detectors["Close<200DMA"] = (C < C.rolling(200).mean()).reindex(idx)

# variance CUSUM (Page 1954): H0 sigma = trailing-250d sigma, H1 sigma x1.5; alarm holds 20 days
def var_cusum(h, ratio=1.5, hold=20):
    sref = r.rolling(250, min_periods=120).std().shift(1)
    z = (r / sref).reindex(idx).fillna(0).values
    d2 = ratio ** 2
    S, flag, left = 0.0, np.zeros(len(z), bool), 0
    for i, zz in enumerate(z):
        S = max(0.0, S + 0.5 * np.log(1 / d2) + 0.5 * zz * zz * (1 - 1 / d2))
        if S >= h:
            left, S = hold, 0.0
        if left > 0:
            flag[i] = True
            left -= 1
    return pd.Series(flag, index=idx)


for h in [3, 5]:
    detectors[f"Var-CUSUM h={h} (x1.5, hold 20d)"] = var_cusum(h)

p("\n  Detector summary 2015-2026 (bad = risk-off flag).  lag = trading days from drawdown peak to first flag;"
  " dd@flag = drawdown already suffered when flagged; exit = trading days after trough until flag clears;"
  " spells/yr = entries into 'bad' per year; short% = spells lasting < 5 days; agree = share of days agreeing"
  " with the ex-post (smoothed) JM lam=20 label.")
rows = []
S0 = "2015-01-01"
for name, flag in detectors.items():
    fl = flag.loc[S0:].astype(bool)
    starts = fl & ~fl.shift(1, fill_value=False)
    spells = []
    cur = 0
    for v in fl.values:
        if v:
            cur += 1
        elif cur:
            spells.append(cur)
            cur = 0
    if cur:
        spells.append(cur)
    yrs = (fl.index[-1] - fl.index[0]).days / 365.25
    lags, dds, exits = [], [], []
    for pk, tr, rec in episodes:
        if pk < pd.Timestamp(S0):
            continue
        seg = fl.loc[pk:]
        hit = seg[seg].index
        if len(hit):
            lags.append(len(fl.loc[pk:hit[0]]) - 1)
            dds.append(close[hit[0]] / close[pk] - 1)
        after = fl.loc[tr:]
        clr = after[~after].index
        exits.append(len(fl.loc[tr:clr[0]]) - 1 if len(clr) else np.nan)
    agree = (fl == expost.loc[S0:]).mean()
    rows.append({"detector": name, "time_bad%": 100 * fl.mean(), "spells/yr": starts.sum() / yrs,
                 "mean_spell_d": np.mean(spells) if spells else np.nan,
                 "short%": 100 * np.mean(np.array(spells) < 5) if spells else np.nan,
                 "lags_d": ",".join(str(x) for x in lags), "med_dd@flag": np.median(dds) if dds else np.nan,
                 "exit_lags_d": ",".join("na" if np.isnan(x) else str(int(x)) for x in exits), "agree_expost": agree})
p(pd.DataFrame(rows).set_index("detector").round(3).to_string())

# does the online JM 'bad' state (fit 2014-19, used 2020+) condition the proxy?
p("\n  Proxy by online JM state (lam=20, fit 2014-19), 2020-2026 only (out-of-sample for the JM):")
jm = detectors["JM online lam=20 (fit 2014-19)"].shift(1).reindex(D.index)  # state known at prior close
sub = D.loc["2020-01-01":].copy()
sub["jm_bad"] = jm.loc[sub.index]
summarize(sub["jm_bad"], "jm_bad_prev", frame=sub)
xa = sub[(sub.jm_bad == False) & sub.trig].pnl_s
xb = sub[(sub.jm_bad == True) & sub.trig].pnl_s
p(f"  JM good vs bad, single-breach trades: diff {xa.mean()-xb.mean():+.3f} sigma, Welch t {stats.ttest_ind(xa, xb, equal_var=False).statistic:+.2f}")
for a, b in [("2020", "2022"), ("2023", "2026")]:
    s2 = sub.loc[a:b]
    ga, gb = s2[(s2.jm_bad == False) & s2.trig].pnl_s, s2[(s2.jm_bad == True) & s2.trig].pnl_s
    p(f"    {a}-{b}: good {ga.mean():+.3f} (n={len(ga)}) vs bad {gb.mean():+.3f} (n={len(gb)})")

# CUSUM ARL by simulation (Gaussian and Student-t(4) scaled to unit variance)
p("  Variance-CUSUM run lengths by simulation (1,000 paths x up to 20,000 days; i.i.d. returns, known baseline sigma):")
rng = np.random.default_rng(1)
NP, NT = 1000, 20000


def run_lengths(z, h):
    S = np.zeros(z.shape[0])
    rl = np.full(z.shape[0], np.nan)
    for i in range(z.shape[1]):
        S = np.maximum(0.0, S + 0.5 * np.log(1 / 2.25) + 0.5 * z[:, i] ** 2 * (1 - 1 / 2.25))
        hit = (S >= h) & np.isnan(rl)
        rl[hit] = i + 1
        if not np.isnan(rl).any():
            break
    return rl


for dist in ["normal", "t4"]:
    z = rng.standard_normal((NP, NT)) if dist == "normal" else rng.standard_t(4, (NP, NT)) / np.sqrt(2)
    for h in [3, 5]:
        rl0 = run_lengths(z, h)
        rl1 = run_lengths(z[:, :2000] * 1.5, h)
        p(f"    h={h} {dist:6s}: days to false alarm (no change) mean {np.nanmean(rl0):7.1f}, median {np.nanmedian(rl0):6.0f}"
          f" (censored {np.isnan(rl0).mean():.1%});  days to detect sigma x1.5 mean {np.nanmean(rl1):5.1f}, median {np.nanmedian(rl1):4.0f}")

p("\n  Detector states on the last 5 sessions (True = risk-off flag):")
last = pd.DataFrame({k: v.iloc[-5:] for k, v in detectors.items() if "full-sample" not in k}).T
last.columns = [c.strftime("%m-%d") for c in last.columns]
p(last.to_string())
p(f"  Latest regime inputs: VIX {vix_n.iloc[-1]:.2f} (252d pct {tpct(vix_n).iloc[-1]:.2f}); 5d VIX log chg {np.log(vix_n.iloc[-1]/vix_n.iloc[-6]):+.3f};"
  f" RV20 {rv20.iloc[-1]:.1f} (pct {tpct(rv20).iloc[-1]:.2f}); drawdown from 252d high {C.iloc[-1]/C.iloc[-252:].max()-1:+.1%}")

# regime persistence
p("\n  Regime persistence (probability the flag is the same next day; mean spell length in days):")
for name in ["VIX>20 (prior close)", "RV20 pct>0.80", "Close<200DMA", "JM online lam=20 (full-sample fit)", "JM online lam=100 (full-sample fit)"]:
    fl = detectors[name].loc[S0:].astype(bool)
    same = (fl == fl.shift(1)).iloc[1:].mean()
    p(f"    {name:40s} P(same) {same:.3f}")

# ------------------------------------------------------------------ E. structural periods
p("\n[E] Structural periods (proxy, single-breach days; noise units)")
periods = {
    "2015-2019 pre-COVID": ("2015-01-01", "2019-12-31"),
    "COVID crash 2020-02-20..2020-05-31": ("2020-02-20", "2020-05-31"),
    "2020-06..2021-12 recovery/bull": ("2020-06-01", "2021-12-31"),
    "2022 rate hikes Jan-Jun": ("2022-01-01", "2022-06-30"),
    "2022-07..2024-11-19": ("2022-07-01", "2024-11-19"),
    "SEBI reforms 2024-11-20..2025-08-31": ("2024-11-20", "2025-08-31"),
    "Tue expiry 2025-09-01..2025-12-31": ("2025-09-01", "2025-12-31"),
    "2026 YTD (war/oil/rates)": ("2026-01-01", "2026-12-31"),
}
rows = []
for k, (a, b) in periods.items():
    d = D.loc[a:b]
    t = d[d.trig]
    rows.append({"period": k, "days": len(d), "VIX": d.vix.mean(), "RV20": d.rv20.mean(), "VRP": d.vrp.mean(),
                 "sig_bp": 1e4 * d.sig.mean(), "trig%": 100 * d.trig.mean(), "both%": 100 * d.both.mean(),
                 "mean_sig": t.pnl_s.mean(), "t": stats.ttest_1samp(t.pnl_s, 0).statistic if len(t) > 2 else np.nan,
                 "cons_sig": d.pnl_cs.dropna().mean(), "ER": d.er.mean(), "ac1_daily": r.loc[a:b].autocorr(1),
                 "intraday_bp/d": 1e4 * np.log(C / O).loc[a:b].mean(), "overnight_bp/d": 1e4 * np.log(O / Cp).loc[a:b].mean()})
p(pd.DataFrame(rows).set_index("period").round(3).to_string())

p("\n  2025-09 .. 2026-10 monthly detail")
mth = D.loc["2025-09-01":].groupby(pd.Grouper(freq="ME"))
rows = []
for k, d in mth:
    if len(d) == 0:
        continue
    t = d[d.trig]
    rows.append({"month": k.strftime("%Y-%m"), "nifty_ret%": 100 * (C.loc[d.index[-1]] / Cp.loc[d.index[0]] - 1),
                 "VIX": d.vix.mean(), "RV20": d.rv20.mean(), "trig%": 100 * d.trig.mean(), "both%": 100 * d.both.mean(),
                 "mean_sig": t.pnl_s.mean(), "cons_sum": d.pnl_cs.fillna(0).sum(), "dd": d.dd.iloc[-1]})
p(pd.DataFrame(rows).set_index("month").round(3).to_string())
p(f"\n  Nifty 2026 YTD to {C.index[-1].date()}: {C.iloc[-1]/C.loc['2025-12-31']-1:+.1%};  India VIX last {vix.iloc[-1]:.2f}; "
  f"VIX max 2026 {vix.loc['2026'].max():.2f} on {vix.loc['2026'].idxmax().date()}; USD/INR last {inr.iloc[-1]:.2f}; Brent last {brent.iloc[-1]:.2f}")

p("  Share of days with India VIX close > 20, by year:", (vix > 20).groupby(vix.index.year).mean().round(3).to_dict())

OUT.write_text("\n".join(_lines), encoding="utf-8")
