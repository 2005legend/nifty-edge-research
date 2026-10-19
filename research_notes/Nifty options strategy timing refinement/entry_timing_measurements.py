"""Own measurements for the entry-timing note (entry_timing.md).

Data: Yahoo Finance spot-index bars cached by fetch_intraday_yf.py in data/intraday_yf/
  * 60-minute bars, Nov 2023 - Oct 2026 (~725 sessions): seasonality, momentum by
    decision time, hourly noise-band breakout, pullback/confirmation entries, MTF filter,
    India VIX hourly path.
  * 5-minute bars, last ~60 sessions (Jul-Oct 2026, mostly after the 3 Aug 2026 closing
    auction): 5-min volatility profile, 15- vs 30-minute check cost, false breakouts,
    retest fills, ETF volume profile, VIX intraday path.
  * 1-minute bars, last ~19 sessions: alert-to-fill delay cost.
  * Daily Nifty 2014-2026 (data/NSEI_daily.csv): NR7 / NR4 / inside-day / Bollinger
    squeeze contraction-expansion tests and the daily-trend (MTF) filter.

Everything here is DESCRIPTIVE (evidence grade C). Spot index, not futures; no volume
for the index; no option prices. t-stats use simple i.i.d. standard errors across days.

Run from the project root:
    .venv/Scripts/python "research_notes/Nifty options strategy timing refinement/entry_timing_measurements.py"
Output is also written to entry_timing_measurements_output.txt next to this script.
"""
from __future__ import annotations

import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
D = ROOT / "data" / "intraday_yf"

# ---------------------------------------------------------------- calendars
# Weekly expiry weekday (Mon=0). Holiday -> previous trading day of the same week.
NIFTY_SCHED = [("2000-01-01", "2025-08-31", 3), ("2025-09-01", "2035-12-31", 1)]
SENSEX_SCHED = [("2000-01-01", "2024-12-31", 4), ("2025-01-01", "2025-08-31", 1),
                ("2025-09-01", "2035-12-31", 3)]
TUE_SWITCH = pd.Timestamp("2025-09-01")
AUCTION = pd.Timestamp("2026-08-03")


def expiry_set(days: pd.DatetimeIndex, sched) -> set:
    days = pd.DatetimeIndex(sorted(set(days.normalize())))
    out = set()
    s = pd.Series(days, index=days)
    for wk, grp in s.groupby(days.to_period("W-SUN")):
        monday = wk.start_time.normalize()
        for a, b, wd in sched:
            target = monday + pd.Timedelta(days=wd)
            if pd.Timestamp(a) <= target <= pd.Timestamp(b):
                c = grp[grp <= target]
                if len(c):
                    out.add(c.max())
    return out


def period_of(d: pd.Timestamp) -> str:
    if d < TUE_SWITCH:
        return "P1 Nov23-Aug25"
    if d < AUCTION:
        return "P2 Sep25-Jul26"
    return "P3 Aug26-Oct26 (auction)"


# ---------------------------------------------------------------- helpers
def tstat(x) -> tuple[int, float, float]:
    x = pd.Series(x).dropna()
    n = len(x)
    if n < 3:
        return n, float("nan"), float("nan")
    m = x.mean()
    return n, m, m / (x.std(ddof=1) / np.sqrt(n))


def fmt(n, m, t, scale=1e4, unit="bp"):
    return f"N={n:4d} mean={m*scale:+7.2f}{unit} t={t:+5.2f}"


def load(name: str, iv: str) -> pd.DataFrame:
    df = pd.read_csv(D / f"{name}_{iv}.csv", index_col=0, parse_dates=True)
    df = df[df.index.dayofweek < 5]
    return df


def pivots(df: pd.DataFrame, nbars: int):
    df = df.copy()
    df["date"] = df.index.normalize()
    cnt = df.groupby("date").size()
    good = cnt[cnt >= nbars].index
    df = df[df["date"].isin(good)]
    df["tod"] = df.index.strftime("%H:%M")
    P = {k: df.pivot(index="date", columns="tod", values=k) for k in ["Open", "High", "Low", "Close"]}
    return P


# ================================================================ 60-minute analyses
H_BARS = ["09:15", "10:15", "11:15", "12:15", "13:15", "14:15", "15:15"]
DEC = ["10:15", "11:15", "12:15", "13:15", "14:15"]  # decision times = bar ends


def hourly_frame(name: str, sched) -> pd.DataFrame:
    P = pivots(load(name, "60m"), 7)
    O, H, L, C = (P[k][H_BARS] for k in ["Open", "High", "Low", "Close"])
    f = pd.DataFrame(index=O.index)
    f["open"] = O["09:15"]
    # price at the END of each hourly bar
    for b, e in zip(H_BARS[:-1], DEC + ["15:15"]):
        f[f"p{e}"] = C[b]
    f["close"] = C["15:15"]  # last print ~15:29 (auction-affected after Aug 2026)
    f["pc"] = f["close"].shift(1)
    for b in H_BARS:
        f[f"r{b}"] = np.log(C[b] / O[b])
        f[f"hl{b}"] = np.log(H[b] / L[b])
        f[f"hi{b}"] = H[b]
        f[f"lo{b}"] = L[b]
    exp = expiry_set(f.index, sched)
    f["expiry"] = f.index.isin(list(exp))
    f["period"] = [period_of(d) for d in f.index]
    f["dow"] = f.index.dayofweek
    f["oc"] = np.log(f["p15:15"] / f["open"])
    f["sd20"] = f["oc"].rolling(20).std().shift(1)
    f["sma20"] = f["close"].rolling(20).mean()
    f["sma50"] = f["close"].rolling(50).mean()
    f["trend20"] = np.sign(f["close"] - f["sma20"]).shift(1)
    f["trend50"] = np.sign(f["close"] - f["sma50"]).shift(1)
    return f.dropna(subset=["pc"])


def sec_hourly_profile(f: pd.DataFrame, name: str):
    print(f"\n--- [{name}] A1. Hourly |return| and range profile, bp (bar 15:15 = 15 min only) ---")
    mins = {b: 60 for b in H_BARS}
    mins["15:15"] = 15
    for grp_name, g in [("ALL", f)] + [(p, f[f.period == p]) for p in sorted(f.period.unique())]:
        for ex in [False, True]:
            gg = g[g.expiry == ex]
            if len(gg) < 5:
                continue
            row = []
            for b in H_BARS:
                a = gg[f"r{b}"].abs().mean() * 1e4
                hl = gg[f"hl{b}"].mean() * 1e4
                row.append(f"{b}:{a:5.1f}/{hl:5.1f}({hl/np.sqrt(mins[b]):4.1f})")
            print(f"{grp_name:26s} {'EXP' if ex else 'non'} N={len(gg):3d} " + " ".join(row))
    print("  format = mean|O->C| / mean ln(H/L) (range per sqrt-minute)")

    print(f"\n--- [{name}] A2. Mean signed return per hourly bar (bp, t) ---")
    for grp_name, g in [("ALL", f)] + [(p, f[f.period == p]) for p in sorted(f.period.unique())]:
        row = []
        for b in H_BARS:
            n, m, t = tstat(g[f"r{b}"])
            row.append(f"{b}:{m*1e4:+5.1f}({t:+4.1f})")
        n, m, t = tstat(np.log(g["open"] / g["pc"]))
        print(f"{grp_name:26s} N={len(g):3d} gap:{m*1e4:+5.1f}({t:+4.1f}) " + " ".join(row))


def sec_momentum_by_time(f: pd.DataFrame, name: str):
    print(f"\n--- [{name}] A3. Does the move-so-far at time tau continue to 15:15? ---")
    print("  x = ln(P_tau/open) [open-anchored]; y = ln(P_15:15/P_tau); follow = sign(x)*y")
    for grp_name, g in [("ALL", f), ("non-expiry", f[~f.expiry]), ("expiry", f[f.expiry])] + \
            [(p, f[f.period == p]) for p in sorted(f.period.unique())]:
        out = []
        for tau in DEC:
            x = np.log(g[f"p{tau}"] / g["open"])
            y = np.log(g["p15:15"] / g[f"p{tau}"])
            fol = np.sign(x) * y
            z = (x.abs() / g["sd20"])
            big = z > z.quantile(2 / 3)
            n, m, t = tstat(fol)
            nb, mb, tb = tstat(fol[big])
            c = np.corrcoef(x, y)[0, 1]
            out.append(f"{tau}: all {m*1e4:+5.1f}bp(t{t:+4.1f}) corr{c:+.2f} | topTerc {mb*1e4:+5.1f}bp(t{tb:+4.1f}) win{(fol[big]>0).mean():.2f}")
        print(f"{grp_name} (N={len(g)})")
        for o in out:
            print("    " + o)

    print(f"\n--- [{name}] A3b. Rest-of-day (prev close -> tau) form, tau=14:15, y to 15:15 and to close ---")
    for grp_name, g in [("ALL", f), ("non-expiry", f[~f.expiry]), ("expiry", f[f.expiry])] + \
            [(p, f[f.period == p]) for p in sorted(f.period.unique())]:
        x = np.log(g["p14:15"] / g["pc"])
        for lab, end in [("->15:15", "p15:15"), ("->close", "close")]:
            y = np.log(g[end] / g["p14:15"])
            n, m, t = tstat(np.sign(x) * y)
            print(f"  {grp_name:26s} {lab}: {fmt(n, m, t)} win={(np.sign(x)*y>0).mean():.2f}")

    print(f"\n--- [{name}] A4. First hour (open->10:15) vs rest (10:15->15:15), incl. gap context ---")
    g = f
    x = np.log(g["p10:15"] / g["open"])
    gap = np.log(g["open"] / g["pc"])
    y = np.log(g["p15:15"] / g["p10:15"])
    for lab, mask in [("all", x == x), ("gap>+0.3%", gap > 0.003), ("gap<-0.3%", gap < -0.003),
                      ("|gap|<0.3%", gap.abs() <= 0.003),
                      ("FH same sign as gap", np.sign(x) == np.sign(gap)),
                      ("FH opposite to gap", np.sign(x) != np.sign(gap))]:
        n, m, t = tstat((np.sign(x) * y)[mask])
        print(f"  {lab:22s} follow-first-hour: {fmt(n, m, t)} P(same sign)={(np.sign(x)==np.sign(y))[mask].mean():.2f}")


def band_signals(f: pd.DataFrame, V: float = 1.0) -> pd.DataFrame:
    """First noise-band breakout of the day at hourly decision times (Zarattini band)."""
    rows = []
    sig = {}
    for tau in DEC:
        mv = (f[f"p{tau}"] / f["open"] - 1).abs()
        sig[tau] = mv.rolling(14).mean().shift(1)
    up_ref = np.maximum(f["open"], f["pc"])
    dn_ref = np.minimum(f["open"], f["pc"])
    for d in f.index:
        r = f.loc[d]
        for i, tau in enumerate(DEC):
            s = sig[tau].loc[d]
            if np.isnan(s):
                break
            up = up_ref.loc[d] * (1 + V * s)
            dn = dn_ref.loc[d] * (1 - V * s)
            p = r[f"p{tau}"]
            side = 1 if p > up else (-1 if p < dn else 0)
            if side:
                edge = up if side == 1 else dn
                later = H_BARS[H_BARS.index(tau):6]  # bars starting at tau .. 14:15
                lows = [r[f"lo{b}"] for b in later]
                highs = [r[f"hi{b}"] for b in later]
                adverse_px = min(lows) if side == 1 else max(highs)
                nxt = DEC[i + 1] if i + 1 < len(DEC) else None
                still = None
                if nxt:
                    pn = r[f"p{nxt}"]
                    still = (pn > up) if side == 1 else (pn < dn)
                rows.append(dict(date=d, tau=tau, side=side, p=p, edge=edge, s=s, openp=r["open"],
                                 exit=r["p15:15"], adverse=adverse_px, nxt=nxt,
                                 pn=r[f"p{nxt}"] if nxt else np.nan, still=still,
                                 expiry=r["expiry"], period=r["period"], sd20=r["sd20"],
                                 trend20=r["trend20"], trend50=r["trend50"]))
                break
    return pd.DataFrame(rows)


def sec_band(f: pd.DataFrame, name: str):
    print(f"\n--- [{name}] A5. Hourly noise-band breakout (first signal of day), follow to 15:15 ---")
    for V in [1.0, 1.25]:
        b = band_signals(f, V)
        b["ret"] = b.side * np.log(b.exit / b.p)
        b["mae"] = b.side * np.log(b.adverse / b.p)
        print(f" V={V}: signals on {len(b)} of {f['sd20'].notna().sum()} days")
        for grp_name, g in [("ALL", b), ("non-expiry", b[~b.expiry]), ("expiry", b[b.expiry])] + \
                [(p, b[b.period == p]) for p in sorted(b.period.unique())]:
            n, m, t = tstat(g.ret)
            print(f"   {grp_name:26s} {fmt(n, m, t)} win={(g.ret>0).mean():.2f} medMAE={g.mae.median()*1e4:+.1f}bp")
        for tau in DEC:
            g = b[b.tau == tau]
            n, m, t = tstat(g.ret)
            if n >= 3:
                print(f"   first signal at {tau}: {fmt(n, m, t)} win={(g.ret>0).mean():.2f} long/short={int((g.side>0).sum())}/{int((g.side<0).sum())}")
        for s_ in [1, -1]:
            g = b[b.side == s_]
            n, m, t = tstat(g.ret)
            print(f"   {'LONG ' if s_>0 else 'SHORT'} {fmt(n, m, t)} win={(g.ret>0).mean():.2f}")
        if V == 1.0:
            sec_entry_variants(b, name)
            sec_mtf(b, name)
            sec_band_conditioning(f, b, name)


def sec_band_conditioning(f: pd.DataFrame, b: pd.DataFrame, name: str):
    """Prior-day contraction (NR4/NR7/inside) and RSI(5) as filters on the hourly band signal."""
    hi = f[[f"hi{x}" for x in H_BARS]].max(axis=1)
    lo = f[[f"lo{x}" for x in H_BARS]].min(axis=1)
    rng = np.log(hi / lo)
    flags = pd.DataFrame(index=f.index)
    flags["nr4"] = (rng == rng.rolling(4).min()).shift(1)
    flags["nr7"] = (rng == rng.rolling(7).min()).shift(1)
    flags["inside"] = ((hi < hi.shift(1)) & (lo > lo.shift(1))).shift(1)
    dc = f["close"].diff()
    up = dc.clip(lower=0).rolling(5).mean()
    dn = (-dc.clip(upper=0)).rolling(5).mean()
    flags["rsi5"] = (100 - 100 / (1 + up / dn)).shift(1)
    bb = b.set_index("date").join(flags)
    print(f"\n--- [{name}] A10. Hourly band signal conditioned on PRIOR-day pattern (Zarattini/Crabel check) ---")
    for lab, m in [("all", bb.ret == bb.ret), ("prior NR4", bb.nr4 == True), ("prior NR7", bb.nr7 == True),
                   ("prior inside day", bb.inside == True), ("not NR4", bb.nr4 == False),
                   ("RSI5 < 50", bb.rsi5 < 50), ("RSI5 >= 50", bb.rsi5 >= 50)]:
        g = bb[m]
        print(f"  {lab:16s}: {fmt(*tstat(g.ret))} win={(g.ret>0).mean():.2f}")
    # room left: typical remaining move and excursion from each decision time to 15:15
    print(f"  A11. Room left after each decision time (to 15:15), median bp [non-expiry | expiry]:")
    for tau in DEC:
        later = H_BARS[H_BARS.index(tau):6]
        out = []
        for ex in [False, True]:
            g = f[f.expiry == ex]
            mv = np.log(g["p15:15"] / g[f"p{tau}"]).abs() * 1e4
            hi_ = g[[f"hi{x}" for x in later]].max(axis=1)
            lo_ = g[[f"lo{x}" for x in later]].min(axis=1)
            exc = np.maximum(np.log(hi_ / g[f"p{tau}"]), np.log(g[f"p{tau}"] / lo_)) * 1e4
            out.append(f"|move| {mv.median():5.1f} maxExc {exc.median():5.1f} P(maxExc>=20bp) {(exc>=20).mean():.2f}")
        print(f"    {tau}: " + " | ".join(out))
    # where in the day are the high and the low set?
    H = f[[f"hi{x}" for x in H_BARS]].values
    L = f[[f"lo{x}" for x in H_BARS]].values
    ih = pd.Series(np.array(H_BARS)[H.argmax(axis=1)]).value_counts(normalize=True).reindex(H_BARS)
    il = pd.Series(np.array(H_BARS)[L.argmin(axis=1)]).value_counts(normalize=True).reindex(H_BARS)
    print(f"  bar containing the day's HIGH: " + " ".join(f"{k}:{v:.2f}" for k, v in ih.items()))
    print(f"  bar containing the day's LOW : " + " ".join(f"{k}:{v:.2f}" for k, v in il.items()))


def sec_entry_variants(b: pd.DataFrame, name: str):
    print(f"\n--- [{name}] A6. Entry technique on the hourly band signal (V=1): market vs limit pullback vs confirmation ---")
    n, m, t = tstat(b.ret)
    print(f"  market at signal          : {fmt(n, m, t)} per signal (all signals traded)")
    for lab, k in [("limit 0.25 sigma back", 0.25), ("limit 0.50 sigma back", 0.5), ("limit at band edge", None)]:
        lim = np.where(b.side == 1,
                       b.p - (k * b.s * b.openp if k is not None else b.p - b.edge),
                       b.p + (k * b.s * b.openp if k is not None else b.edge - b.p))
        filled = np.where(b.side == 1, b.adverse <= lim, b.adverse >= lim)
        r_lim = b.side * np.log(b.exit / lim)
        per_signal = np.where(filled, r_lim, 0.0)
        nf, mf, tf = tstat(r_lim[filled])
        nm, mm, tm = tstat(b.ret[~filled])
        ns, ms, ts = tstat(per_signal)
        print(f"  {lab:26s}: fill={filled.mean():.2f} | filled trades {fmt(nf, mf, tf)} | missed trades (mkt outcome) {fmt(nm, mm, tm)} | per-signal {ms*1e4:+.2f}bp")
    c = b[b.still.notna()]
    conf = c[c.still.astype(bool)]
    r_conf = conf.side * np.log(conf.exit / conf.pn)
    n1, m1, t1 = tstat(c.ret)
    n2, m2, t2 = tstat(r_conf)
    print(f"  confirm: still outside band 1h later -> enter then: {fmt(n2, m2, t2)} (vs immediate on same days set {fmt(n1, m1, t1)}); kept {len(conf)}/{len(c)}")
    fail = c[~c.still.astype(bool)]
    n3, m3, t3 = tstat(fail.ret)
    print(f"  immediate entries whose breakout FAILED by next check: {fmt(n3, m3, t3)} (share {len(fail)/max(len(c),1):.2f})")


def sec_mtf(b: pd.DataFrame, name: str):
    print(f"\n--- [{name}] A7. Multi-timeframe: band signal aligned with daily trend (prev close vs SMA) ---")
    for tr in ["trend20", "trend50"]:
        for lab, mask in [("aligned", b.side == b[tr]), ("counter", b.side == -b[tr])]:
            g = b[mask]
            n, m, t = tstat(g.ret)
            print(f"  {tr} {lab:8s}: {fmt(n, m, t)} win={(g.ret>0).mean():.2f}")


def sec_mtf_firsthour(f: pd.DataFrame, name: str):
    print(f"\n--- [{name}] A8. MTF on first-hour direction: follow FH from 10:15 to 15:15 by daily trend ---")
    x = np.log(f["p10:15"] / f["open"])
    y = np.log(f["p15:15"] / f["p10:15"])
    fol = np.sign(x) * y
    for tr in ["trend20", "trend50"]:
        for lab, mask in [("aligned", np.sign(x) == f[tr]), ("counter", np.sign(x) == -f[tr])]:
            n, m, t = tstat(fol[mask])
            print(f"  {tr} {lab:8s}: {fmt(n, m, t)}")


def sec_vix_hourly():
    print("\n--- A9. India VIX hourly path (ratio to previous day's last print), median ---")
    P = pivots(load("INDIAVIX", "60m"), 7)
    O, C = P["Open"][H_BARS], P["Close"][H_BARS]
    prev = C["15:15"].shift(1)
    nexp = expiry_set(O.index, NIFTY_SCHED)
    df = pd.DataFrame({"09:15open": O["09:15"] / prev})
    for b, e in zip(H_BARS, DEC + ["15:15", "close"]):
        df[e] = C[b] / prev
    df = df.dropna()
    df["period"] = [period_of(d) for d in df.index]
    df["exp"] = df.index.isin(list(nexp))
    cols = ["09:15open"] + DEC + ["15:15", "close"]
    for grp_name, g in [("ALL", df)] + [(p, df[df.period == p]) for p in sorted(df.period.unique())] + \
            [("Nifty-expiry days", df[df.exp]), ("non-expiry", df[~df.exp])]:
        print(f"  {grp_name:26s} N={len(g):3d} " + " ".join(f"{c}:{(g[c].median()-1)*100:+5.2f}%" for c in cols))
    # change from 10:15 to close, share of days VIX falls after 10:15
    ch = df["close"] / df["10:15"] - 1
    print(f"  VIX close vs 10:15: median {ch.median()*100:+.2f}%, falls on {(ch<0).mean():.2f} of days")
    ch2 = df["10:15"] / df["09:15open"] - 1
    print(f"  VIX 10:15 vs 09:15 first print: median {ch2.median()*100:+.2f}%, falls on {(ch2<0).mean():.2f} of days")


# ================================================================ 5-minute analyses
def five_frame(name: str):
    P = pivots(load(name, "5m"), 70)
    C = P["Close"]
    O = P["Open"]
    return O, C, P["High"], P["Low"]


def tod_minutes(s: str) -> int:
    h, m = map(int, s.split(":"))
    return h * 60 + m


def sec_5m_profile(name: str, sched):
    O, C, H, L = five_frame(name)
    cols = [c for c in C.columns if "09:15" <= c <= "15:25"]
    r = np.log(C[cols] / O[cols]).abs() * 1e4
    hl = np.log(H[cols] / L[cols]) * 1e4
    exp = expiry_set(C.index, sched)
    isexp = C.index.isin(list(exp))
    print(f"\n--- [{name}] B1. 5-min bar mean range ln(H/L) bp by 30-min block (last ~60 sessions) ---")
    blocks = [("09:15", "09:44"), ("09:45", "10:14"), ("10:15", "10:44"), ("10:45", "11:14"), ("11:15", "11:44"),
              ("11:45", "12:14"), ("12:15", "12:44"), ("12:45", "13:14"), ("13:15", "13:44"), ("13:45", "14:14"),
              ("14:15", "14:44"), ("14:45", "15:14"), ("15:15", "15:29")]
    for lab, m in [("non-expiry", ~isexp), ("expiry", isexp)]:
        out = []
        for a, b_ in blocks:
            cc = [c for c in cols if a <= c <= b_]
            out.append(f"{a}:{hl.loc[m, cc].mean().mean():4.1f}")
        print(f"  {lab:10s} N={m.sum():2d} " + " ".join(out))
    first = hl[["09:15"]].mean().iloc[0]
    print(f"  first 5-min bar (09:15) mean range: {first:.1f}bp; 09:20 {hl['09:20'].mean():.1f}; 09:25 {hl['09:25'].mean():.1f}; 09:30 {hl['09:30'].mean():.1f}; 09:40 {hl['09:40'].mean():.1f}")
    # opening-window continuation / reversal (5-min data, small sample)
    openp = O["09:15"]
    for t0 in ["09:30", "09:45", "10:00"]:
        x = np.log(price_at(C, t0) / openp)
        y = np.log(price_at(C, "15:10") / price_at(C, t0))
        n, m, t = tstat(np.sign(x) * y)
        share = (x.abs() / (x.abs() + y.abs()))
        print(f"  open->{t0} move followed to 15:10: {fmt(n, m, t)} P(same sign)={(np.sign(x)==np.sign(y)).mean():.2f} corr={np.corrcoef(x, y)[0,1]:+.2f} median share of |path| done by {t0}={share.median():.2f}")
    # spot index after 15:15 (closing auction)
    late = [c for c in cols if c >= "15:15"]
    flat = (hl[late] < 0.01).mean()
    print(f"  share of 5-min bars with zero range after 15:15: " + " ".join(f"{c}:{v:.2f}" for c, v in flat.items()))
    return O, C, H, L, isexp


def checks_list(start="09:45", end="14:30", step=15):
    s, e = tod_minutes(start), tod_minutes(end)
    return [f"{m//60:02d}:{m%60:02d}" for m in range(s, e + 1, step)]


def price_at(C: pd.DataFrame, t: str) -> pd.Series:
    """Price at clock time t = close of the 5-min bar ending at t."""
    m = tod_minutes(t) - 5
    return C[f"{m//60:02d}:{m%60:02d}"]


def sec_5m_band(name: str, sched):
    O, C, H, L = five_frame(name)
    exp = expiry_set(C.index, sched)
    openp = O["09:15"]
    pc = C["15:25"].shift(1)
    times = checks_list("09:30", "15:10", 5)
    px = pd.DataFrame({t: price_at(C, t) for t in times})
    sig = {t: (px[t] / openp - 1).abs().rolling(14).mean().shift(1) for t in times}
    up_ref = np.maximum(openp, pc)
    dn_ref = np.minimum(openp, pc)
    rows = []
    for d in C.index:
        if np.isnan(sig["09:45"].loc[d]) or np.isnan(pc.loc[d]):
            continue
        rec = dict(date=d, expiry=d in exp)
        # first crossing on 5-min closes from 09:35, and first signal at 15-/30-min checks
        for sched_name, chk in [("c5", checks_list("09:35", "14:30", 5)), ("c15", checks_list("09:45", "14:30", 15)),
                                ("c30", checks_list("10:00", "14:30", 30))]:
            for t in chk:
                s = sig[t].loc[d]
                up, dn = up_ref.loc[d] * (1 + s), dn_ref.loc[d] * (1 - s)
                p = px.loc[d, t]
                side = 1 if p > up else (-1 if p < dn else 0)
                if side:
                    rec[sched_name] = t
                    rec[sched_name + "_side"] = side
                    rec[sched_name + "_p"] = p
                    rec[sched_name + "_edge"] = up if side == 1 else dn
                    rec[sched_name + "_s"] = s
                    # still outside 15 min later?
                    t2m = tod_minutes(t) + 15
                    t2 = f"{t2m//60:02d}:{t2m%60:02d}"
                    if t2 in px.columns:
                        s2 = sig[t2].loc[d]
                        up2, dn2 = up_ref.loc[d] * (1 + s2), dn_ref.loc[d] * (1 - s2)
                        p2 = px.loc[d, t2]
                        rec[sched_name + "_still"] = (p2 > up2) if side == 1 else (p2 < dn2)
                        rec[sched_name + "_p2"] = p2
                    # min/max after signal until 15:10 for limit-fill test
                    after = [c for c in C.columns if tod_minutes(t) <= tod_minutes(c) < tod_minutes("15:10")]
                    rec[sched_name + "_lo"] = L.loc[d, after].min()
                    rec[sched_name + "_hi"] = H.loc[d, after].max()
                    break
        rec["exit"] = px.loc[d, "15:10"]
        rec["openp"] = openp.loc[d]
        rows.append(rec)
    b = pd.DataFrame(rows)
    print(f"\n--- [{name}] B2. 5-min-resolution noise band (V=1, 14-day), last ~60 sessions (N days={len(b)}) ---")
    for k in ["c5", "c15", "c30"]:
        g = b.dropna(subset=[k])
        ret = g[k + "_side"] * np.log(g.exit / g[k + "_p"])
        n, m, t = tstat(ret)
        print(f"  first signal using {k:3s} checks: days with signal {len(g)}/{len(b)}; follow to 15:10 {fmt(n, m, t)} win={(ret>0).mean():.2f}")
    g = b.dropna(subset=["c15"]).copy()
    g["ret"] = g.c15_side * np.log(g.exit / g.c15_p)
    g["bucket"] = pd.cut(g.c15.map(tod_minutes), [0, tod_minutes("10:15"), tod_minutes("11:15"),
                                                  tod_minutes("13:15"), tod_minutes("14:30")],
                         labels=["09:45-10:15", "10:30-11:15", "11:30-13:15", "13:30-14:30"])
    for k, gg in g.groupby("bucket", observed=False):
        if len(gg):
            print(f"    first c15 signal in {k}: N={len(gg):2d} mean={gg.ret.mean()*1e4:+6.1f}bp win={(gg.ret>0).mean():.2f}")
    g = b.dropna(subset=["c5", "c15"])
    same = g[g.c5_side == g.c15_side]
    lag = same.c15.map(tod_minutes) - same.c5.map(tod_minutes)
    ext = same.c15_side * np.log(same.c15_p / same.c5_p) * 1e4
    print(f"  15-min checks vs continuous(5-min) first crossing: median lag {lag.median():.0f} min, mean extra entry distance {ext.mean():+.1f}bp (median {ext.median():+.1f}bp)")
    g = b.dropna(subset=["c5", "c30"])
    same = g[g.c5_side == g.c30_side]
    lag = same.c30.map(tod_minutes) - same.c5.map(tod_minutes)
    ext = same.c30_side * np.log(same.c30_p / same.c5_p) * 1e4
    print(f"  30-min checks vs continuous first crossing: median lag {lag.median():.0f} min, mean extra entry distance {ext.mean():+.1f}bp (median {ext.median():+.1f}bp)")
    # failure / confirmation and retest at 15-min checks
    g = b.dropna(subset=["c15"]).copy()
    g["ret"] = g.c15_side * np.log(g.exit / g.c15_p)
    if "c15_still" in g:
        st = g.dropna(subset=["c15_still"])
        fail = st[~st.c15_still.astype(bool)]
        ok = st[st.c15_still.astype(bool)]
        rc = ok.c15_side * np.log(ok.exit / ok.c15_p2)
        print(f"  15-min check signal back inside band 15 min later: {len(fail)}/{len(st)}; outcome of those (market entry) mean {fail.ret.mean()*1e4:+.1f}bp")
        print(f"  confirmation entry (still outside after 15 min): {fmt(*tstat(rc))} vs immediate on all {fmt(*tstat(st.ret))}")
    lim = np.where(g.c15_side == 1, g.c15_edge, g.c15_edge)
    filled = np.where(g.c15_side == 1, g.c15_lo <= lim, g.c15_hi >= lim)
    r_lim = g.c15_side * np.log(g.exit / lim)
    print(f"  retest-of-band-edge limit: fill rate {filled.mean():.2f}; filled {fmt(*tstat(r_lim[filled]))}; missed (mkt outcome) {fmt(*tstat(g.ret[~filled]))}; per-signal limit {np.where(filled, r_lim, 0).mean()*1e4:+.1f}bp vs market {g.ret.mean()*1e4:+.1f}bp")
    return b


def sec_5m_decay(name: str):
    O, C, H, L = five_frame(name)
    print(f"\n--- [{name}] B3. Short-horizon continuation after 15-min moves at the 15-min checks (5-min data) ---")
    chk = checks_list("09:45", "14:30", 15)
    rows = []
    for t in chk:
        p0 = price_at(C, t)
        tm = tod_minutes(t)
        pb = price_at(C, f"{(tm-15)//60:02d}:{(tm-15)%60:02d}")
        x = np.log(p0 / pb)
        for dmin in [5, 10, 15, 30]:
            t2 = tm + dmin
            if t2 > tod_minutes("15:10"):
                continue
            p2 = price_at(C, f"{t2//60:02d}:{t2%60:02d}")
            y = np.log(p2 / p0)
            rows.append(pd.DataFrame({"t": t, "d": dmin, "x": x, "y": y}))
    df = pd.concat(rows)
    df["z"] = df.groupby(["t", "d"])["x"].transform(lambda s: s / s.std())
    for thr in [0, 1, 1.5]:
        out = []
        for dmin in [5, 10, 15, 30]:
            g = df[(df.d == dmin) & (df.z.abs() > thr)]
            n, m, t = tstat(np.sign(g.x) * g.y)
            out.append(f"+{dmin}m: {m*1e4:+5.2f}bp(t{t:+4.1f},N{n})")
        print(f"  |z|>{thr}: " + " ".join(out))


def sec_1m_delay(name: str, sched):
    print(f"\n--- [{name}] C1. Alert-to-fill delay at 1-min resolution (last ~19 sessions) ---")
    m1 = load(name, "1m")
    m1["date"] = m1.index.normalize()
    cnt = m1.groupby("date").size()
    m1 = m1[m1.date.isin(cnt[cnt >= 360].index)]
    m1["tod"] = m1.index.strftime("%H:%M")
    C1 = m1.pivot(index="date", columns="tod", values="Close")
    O1 = m1.pivot(index="date", columns="tod", values="Open")
    # price at clock time t = close of 1-min bar labelled t-1
    def p1(t):
        m = tod_minutes(t) - 1
        return C1[f"{m//60:02d}:{m%60:02d}"]
    # sigma bands from 5-min history
    O5, C5, _, _ = five_frame(name)
    open5 = O5["09:15"]
    pc5 = C5["15:25"].shift(1)
    chk = checks_list("09:45", "14:30", 15)
    sig = {t: (price_at(C5, t) / open5 - 1).abs().rolling(14).mean().shift(1) for t in chk}
    rows = []
    for d in C1.index:
        if d not in open5.index or np.isnan(sig["09:45"].get(d, np.nan)):
            continue
        op, pc = O1.loc[d, "09:15"], pc5.loc[d]
        for t in chk:
            s = sig[t].loc[d]
            up, dn = max(op, pc) * (1 + s), min(op, pc) * (1 - s)
            p = p1(t).loc[d]
            side = 1 if p > up else (-1 if p < dn else 0)
            if side:
                rec = dict(date=d, t=t, side=side, p=p, exit=p1("15:10").loc[d])
                for dl in [1, 2, 3, 5, 10]:
                    tm = tod_minutes(t) + dl
                    rec[f"e{dl}"] = p1(f"{tm//60:02d}:{tm%60:02d}").loc[d]
                rows.append(rec)
                break
    b = pd.DataFrame(rows)
    print(f"  first 15-min-check band signals: {len(b)} of {len(C1)} days")
    if len(b):
        for dl in [1, 2, 3, 5, 10]:
            slip = b.side * np.log(b[f"e{dl}"] / b.p) * 1e4
            pts = b.side * (b[f"e{dl}"] - b.p)
            print(f"   delay {dl:2d} min: entry worse by mean {slip.mean():+5.1f}bp / {pts.mean():+6.1f} pts (median {pts.median():+5.1f} pts); share worse {(slip>0).mean():.2f}")
        r0 = b.side * np.log(b.exit / b.p) * 1e4
        print(f"   outcome to 15:10 from signal price: mean {r0.mean():+.1f}bp, win {(r0>0).mean():.2f}")
    # unconditional: all 15-min checks, 1-min-ahead continuation after a strong 15-min move
    rows = []
    for t in chk:
        tm = tod_minutes(t)
        p0 = p1(t)
        pb = p1(f"{(tm-15)//60:02d}:{(tm-15)%60:02d}")
        for dl in [1, 2, 3, 5, 10]:
            p2 = p1(f"{(tm+dl)//60:02d}:{(tm+dl)%60:02d}")
            rows.append(pd.DataFrame({"t": t, "d": dl, "x": np.log(p0 / pb), "y": np.log(p2 / p0)}))
    df = pd.concat(rows).dropna()
    df["z"] = df.groupby(["t", "d"])["x"].transform(lambda s: s / s.std())
    for thr in [0, 1]:
        out = []
        for dl in [1, 2, 3, 5, 10]:
            g = df[(df.d == dl) & (df.z.abs() > thr)]
            n, m, t = tstat(np.sign(g.x) * g.y)
            out.append(f"+{dl}m:{m*1e4:+5.2f}bp(t{t:+4.1f},N{n})")
        print(f"  all checks, |z15|>{thr}: " + " ".join(out))
    # quarter-hour marks: is the 1-min |return| larger in the minute starting at :00/:15/:30/:45?
    r1 = np.log(C1 / O1).abs() * 1e4
    cols = [c for c in r1.columns if "09:30" <= c <= "15:14"]
    qh = [c for c in cols if int(c[-2:]) % 15 == 0]
    other = [c for c in cols if int(c[-2:]) % 15 != 0]
    print(f"  mean |1-min O->C| 09:30-15:14: quarter-hour minutes {r1[qh].mean().mean():.2f}bp vs other minutes {r1[other].mean().mean():.2f}bp")
    # spot after 15:15
    late = [c for c in C1.columns if "15:16" <= c <= "15:29"]
    uniq = C1[late].nunique(axis=1)
    print(f"  distinct 1-min closes 15:16-15:29 per day (spot index, auction period): median {uniq.median():.0f}, min {uniq.min()}, max {uniq.max()}")


def sec_vix_5m():
    print("\n--- B4. India VIX intraday path, 5-min data (last ~60 sessions), median % change vs 09:45 value ---")
    O, C, H, L = five_frame("INDIAVIX")
    exp = expiry_set(C.index, NIFTY_SCHED)
    isexp = C.index.isin(list(exp))
    times = ["09:20", "09:25", "09:30", "09:45", "10:00", "10:30", "11:00", "11:30", "12:00", "12:30", "13:00",
             "13:30", "14:00", "14:30", "15:00", "15:15", "15:30"]
    px = pd.DataFrame({t: price_at(C, t) for t in times})
    px.insert(0, "09:15o", O["09:15"])
    prev = px["15:30"].shift(1)
    for lab, m in [("all", np.ones(len(px), bool)), ("non-expiry", ~isexp), ("Nifty expiry Tue", isexp)]:
        g = px[m]
        print(f"  {lab:16s} N={len(g):2d} vs 09:45: " + " ".join(f"{c}:{(g[c]/g['09:45']-1).median()*100:+5.1f}" for c in px.columns))
    g = px.dropna()
    pr = prev.loc[g.index]
    print("  vs prev close (all): " + " ".join(f"{c}:{(g[c]/pr-1).median()*100:+5.1f}" for c in px.columns))
    print(f"  share of days VIX(09:15 first print) > VIX(09:45): {(px['09:15o']>px['09:45']).mean():.2f}; VIX(15:00) < VIX(10:00): {(px['15:00']<px['10:00']).mean():.2f}")


def sec_etf_volume():
    print("\n--- B5. NIFTYBEES ETF 5-min volume share by 30-min block (proxy for the cash-market U-shape) ---")
    P = load("NIFTYBEES", "5m")
    P["date"] = P.index.normalize()
    P["tod"] = P.index.strftime("%H:%M")
    v = P.pivot(index="date", columns="tod", values="Volume")
    v = v.div(v.sum(axis=1), axis=0)
    blocks = [("09:15", "09:44"), ("09:45", "10:14"), ("10:15", "10:44"), ("10:45", "11:14"), ("11:15", "11:44"),
              ("11:45", "12:14"), ("12:15", "12:44"), ("12:45", "13:14"), ("13:15", "13:44"), ("13:45", "14:14"),
              ("14:15", "14:44"), ("14:45", "15:14"), ("15:15", "15:29")]
    print("  " + " ".join(f"{a}:{v[[c for c in v.columns if a<=c<=b]].sum(axis=1).median()*100:4.1f}%" for a, b in blocks))


# ================================================================ daily analyses
def sec_daily():
    d = pd.read_csv(ROOT / "data" / "NSEI_daily.csv", index_col=0, parse_dates=True)
    d = d[(d.High > d.Low) & (d.Open > 0)].copy()
    d["rng"] = np.log(d.High / d.Low)
    d["atr20"] = d.rng.rolling(20).mean()
    d["nr7"] = d.rng == d.rng.rolling(7).min()
    d["nr4"] = d.rng == d.rng.rolling(4).min()
    d["inside"] = (d.High < d.High.shift(1)) & (d.Low > d.Low.shift(1))
    bbw = d.Close.rolling(20).std() / d.Close.rolling(20).mean()
    d["bbsq"] = bbw <= bbw.rolling(126).quantile(0.10)
    nxt = d.shift(-1)
    d["n_rng_ratio"] = nxt.rng / d.atr20
    d["n_oc"] = np.log(nxt.Close / nxt.Open)
    d["n_trendiness"] = d.n_oc.abs() / nxt.rng
    up_brk = nxt.High > d.High
    dn_brk = nxt.Low < d.Low
    d["one_side_up"] = up_brk & ~dn_brk
    d["one_side_dn"] = dn_brk & ~up_brk
    d["hold_up"] = d.one_side_up & (nxt.Close > d.High)
    d["hold_dn"] = d.one_side_dn & (nxt.Close < d.Low)
    d["both"] = up_brk & dn_brk
    d["fwd5_rng"] = np.log(d.High.rolling(5).max().shift(-5) / d.Low.rolling(5).min().shift(-5)) / d.atr20
    d = d.dropna(subset=["atr20", "n_rng_ratio"])
    print("\n--- D1. Nifty daily 2014-2026: contraction -> expansion (Crabel NR7/NR4/inside day; BB squeeze) ---")
    print("  next-day range / prior 20-day avg range; next-day |O->C|/range; prior-day-extreme breakout behaviour")
    for lab, m in [("all days", np.ones(len(d), bool)), ("NR7", d.nr7), ("NR4", d.nr4), ("inside day", d.inside),
                   ("NR7 & inside", d.nr7 & d.inside), ("BB squeeze (<=10th pct width)", d.bbsq)]:
        g = d[m]
        one = g.one_side_up | g.one_side_dn
        hold = (g.hold_up | g.hold_dn)[one].mean()
        print(f"  {lab:30s} N={len(g):4d} nextRange/ATR={g.n_rng_ratio.mean():.2f} (med {g.n_rng_ratio.median():.2f}) "
              f"trendiness={g.n_trendiness.mean():.2f} |nextOC|={g.n_oc.abs().mean()*100:.2f}% "
              f"P(one-side break)={one.mean():.2f} P(close beyond|one-side)={hold:.2f} P(both sides)={g.both.mean():.2f} "
              f"5d range/ATR={g.fwd5_rng.mean():.2f}")
    # same day range relative to atr: the NR day itself is small, so expansion vs NR day is mechanical
    g = d[d.nr7]
    print(f"  NR7 day's own range / ATR20 = {(g.rng/g.atr20).mean():.2f}; next/own ratio = {(g.n_rng_ratio/(g.rng/g.atr20)).median():.2f} (median)")
    print("\n--- D2. Daily MTF: open->close by prior-day trend state (2014-2026) ---")
    d["oc"] = np.log(d.Close / d.Open)
    for n in [20, 50]:
        tr = np.sign(d.Close - d.Close.rolling(n).mean()).shift(1)
        for lab, m in [("above", tr > 0), ("below", tr < 0)]:
            nn, mm, tt = tstat(d.oc[m])
            print(f"  prev close {lab} SMA{n}: O->C {fmt(nn, mm, tt)} P(C>O)={(d.oc[m]>0).mean():.3f}")


def main():
    buf = io.StringIO()
    with redirect_stdout(buf):
        pd.set_option("display.width", 250)
        print("ENTRY-TIMING MEASUREMENTS (descriptive, grade C). Spot index from Yahoo Finance.")
        for name, sched in [("NSEI", NIFTY_SCHED), ("BSESN", SENSEX_SCHED)]:
            print("\n" + "=" * 100 + f"\n{name}: 60-minute bars\n" + "=" * 100)
            f = hourly_frame(name, sched)
            print(f"sessions {len(f)}  {f.index.min().date()} -> {f.index.max().date()}  expiry days {int(f.expiry.sum())}")
            print(f.groupby('period').size().to_string())
            sec_hourly_profile(f, name)
            sec_momentum_by_time(f, name)
            sec_band(f, name)
            sec_mtf_firsthour(f.dropna(subset=["trend50"]), name)
        sec_vix_hourly()
        for name, sched in [("NSEI", NIFTY_SCHED), ("BSESN", SENSEX_SCHED)]:
            print("\n" + "=" * 100 + f"\n{name}: 5-minute and 1-minute bars\n" + "=" * 100)
            sec_5m_profile(name, sched)
            sec_5m_band(name, sched)
            sec_5m_decay(name)
            sec_1m_delay(name, sched)
        sec_vix_5m()
        sec_etf_volume()
        sec_daily()
    txt = buf.getvalue()
    (HERE / "entry_timing_measurements_output.txt").write_text(txt, encoding="utf-8")
    sys.stdout.write(txt)


if __name__ == "__main__":
    main()
