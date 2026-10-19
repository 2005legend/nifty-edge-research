"""Run: python -I exit_rules_mc.py > exit_rules_mc_output.txt
Monte Carlo comparison of exit rules for a long Nifty weekly call (alerts-only system).
Assumptions follow option_trade_construction.md: Black-76, business-time variance clock,
IV = VIX 14.67 (daily implied s.d. 0.924%), intraday variance share 0.60 uniform over 375 min,
realised intraday sigma 0.65%/day, Nifty 22,555.75, lot 65, Rs57 fixed costs, half-spread
Rs0.10 (<Rs50 premium) / Rs0.20, stop exits pay 3 half-spreads.
Index barriers in log-return units. Paths are common across policies (paired comparison).
"""
import numpy as np
from scipy.special import ndtr
import sys

rng = np.random.default_rng(20261019)
N = 40000
S0 = 22555.75
LOT = 65
SIG_D_IMPL = 0.1467 / np.sqrt(252)      # 0.924% daily implied
SIG_RLZ = 0.0065                         # realised intraday s.d. per session
SM = SIG_RLZ / np.sqrt(375)              # per minute
FIXED = 57.0


def w_left(t, dte):
    """remaining variance (daily units) at minute t (0 = 9:15) with dte full sessions after today"""
    return 0.60 * np.maximum(375 - t, 0.5) / 375 + dte * 1.0


def call(F, K, t, dte):
    v = SIG_D_IMPL * np.sqrt(w_left(t, dte))
    d1 = (np.log(F / K) + 0.5 * v * v) / v
    return F * ndtr(d1) - K * ndtr(d1 - v)


def hs(prem):
    return np.where(prem < 50, 0.10, 0.20)


def run(entry_t, dte, hard_t, scen, b=0.0010, tgt_mult=2.5, target_delta=0.35):
    sm = SM * (0.45/0.65 if scen.startswith('lowvol') else 1.0)
    base_scen = scen.replace('lowvol-', '')
    sign = np.where(rng.random(N) < 0.6, 1.0, -1.0)
    # strike: 50-pt grid, delta closest to target_delta at entry
    Ks = np.arange(22300, 23200, 50.0)
    v0 = SIG_D_IMPL * np.sqrt(w_left(entry_t, dte))
    deltas = ndtr((np.log(S0 / Ks) + 0.5 * v0 * v0) / v0)
    K = Ks[np.argmin(np.abs(deltas - target_delta))]
    delta_K = deltas[np.argmin(np.abs(deltas - target_delta))]
    P0 = call(S0, K, entry_t, dte)
    h0 = hs(P0)
    steps = hard_t - entry_t
    # pre-entry path for VWAP (equal-weighted minutes), reflected so price > VWAP at entry
    pre = np.cumsum(rng.standard_normal((N, entry_t)) * sm, axis=1)
    pre = pre - pre[:, -1:]                      # log price relative to entry price (entry = 0)
    vw_pre = pre.mean(axis=1)                    # VWAP proxy at entry (log units)
    flip = vw_pre > 0                            # price below VWAP -> reflect path
    pre[flip] *= -1
    vw_sum = pre.sum(axis=1)
    eps = rng.standard_normal((N, steps)) * sm
    X = np.zeros((N, steps + 1))
    vwap = np.zeros((N, steps + 1))
    vwap[:, 0] = vw_sum / entry_t
    total = 0.004 / 375 * 90
    vw_level = vwap[:, 0].copy()
    for k in range(steps):
        if base_scen == 'nodrift':
            mu = 0.0
        elif base_scen == 'const':
            mu = 0.004 / 375
        elif base_scen == 'trendpm':
            mu = sign * 0.008 / 375
        elif base_scen.startswith('decay'):
            hl = float(base_scen[5:])
            mu = total * np.log(2) / hl * 2 ** (-k / hl)
        elif base_scen == 'revert':
            kap = np.log(2) / 60
            mu = -kap * (X[:, k] - vw_level)
        X[:, k + 1] = X[:, k] + mu + eps[:, k]
        n = entry_t + k + 1
        vw_sum = vw_sum + X[:, k + 1]
        vwap[:, k + 1] = vw_sum / n
    tgrid = entry_t + np.arange(steps + 1)
    prem = call(S0 * np.exp(X), K, tgrid[None, :], dte)   # option mid along path

    a = tgt_mult * b
    res = {}

    def evaluate(name, stop_rule='index', tgt=a, stall=(45, 0.0005), deadline=90,
                 be_trigger=None, trail=None, vwap_exit=False, prem_stop=None, laggard_only=False, vwap_trail=False):
        exit_k = np.full(N, steps)
        reason = np.full(N, 'hard', dtype=object)
        exitX = X[:, steps].copy()
        alive = np.ones(N, bool)
        stop_lvl = np.full(N, -b)
        runmax = np.zeros(N)
        for k in range(1, steps + 1):
            x = X[:, k]
            runmax = np.maximum(runmax, x)
            if be_trigger is not None:
                stop_lvl = np.where(runmax >= be_trigger, np.maximum(stop_lvl, 0.0), stop_lvl)
            if trail is not None:
                act, dist = trail
                stop_lvl = np.where(runmax >= act, np.maximum(stop_lvl, runmax - dist), stop_lvl)
            if vwap_trail:
                stop_lvl = np.maximum(stop_lvl, vwap[:, k])
            hit_stop = np.zeros(N, bool)
            if stop_rule in ('index', 'both'):
                hit_stop |= x <= stop_lvl
            if prem_stop is not None:
                hit_stop |= (prem[:, k] - P0) * LOT <= -prem_stop
            if vwap_exit:
                hit_stop |= x < vwap[:, k]
            hit_tgt = (x >= tgt) if tgt is not None else np.zeros(N, bool)
            hit_stall = np.zeros(N, bool)
            lag = (runmax < (trail[0] if trail is not None else 9)) if laggard_only else np.ones(N, bool)
            if stall is not None and k == stall[0]:
                hit_stall = (np.abs(x) < stall[1]) & lag
            hit_dead = (deadline is not None) and (k >= deadline)
            # order: stop/target first (target fills at limit level), then time rules
            m = alive & hit_tgt
            exit_k[m] = k; reason[m] = 'target'; exitX[m] = tgt; alive &= ~m
            m = alive & hit_stop
            exit_k[m] = k
            reason[m] = np.where(x[m] >= 0, 'stop>=BE', 'stop')
            exitX[m] = x[m]; alive &= ~m
            m = alive & hit_stall
            exit_k[m] = k; reason[m] = 'stall'; exitX[m] = x[m]; alive &= ~m
            if hit_dead:
                m = alive & lag
                exit_k[m] = k; reason[m] = 'deadline'; exitX[m] = x[m]; alive &= ~m
            if not alive.any():
                break
        texit = entry_t + exit_k
        Pexit = call(S0 * np.exp(exitX), K, texit, dte)
        hexit = hs(Pexit)
        slip_mult = np.where(np.char.startswith(reason.astype(str), 'stop'), 3.0, 1.0)
        pnl = (Pexit - P0) * LOT - h0 * LOT - slip_mult * hexit * LOT - FIXED
        idx_pnl = exitX  # index log-return captured
        r = dict(mean=pnl.mean(), se=pnl.std() / np.sqrt(N), win=(pnl > 0).mean(),
                 hold=exit_k.mean(), idx=idx_pnl.mean() * 1e4,
                 mix={k2: (reason == k2).mean() for k2 in ['target', 'stop', 'stop>=BE', 'stall', 'deadline', 'hard']},
                 avgwin=pnl[pnl > 0].mean() if (pnl > 0).any() else 0, avgloss=pnl[pnl <= 0].mean())
        res[name] = (r, pnl)

    evaluate('P0 current (stop,2.5x tgt,stall45,dl90)')
    evaluate('P1 no stall (dl90)', stall=None)
    evaluate('P2 stall30 + dl60', stall=(30, 0.0005), deadline=60)
    evaluate('P3 no time stops (hard exit only)', stall=None, deadline=None)
    evaluate('P4 P0 + breakeven after +1b', be_trigger=b)
    evaluate('P5 trail 1.5b after +1b, no tgt, stall45, dl90', tgt=None, trail=(b, 1.5 * b))
    evaluate('P5b trail 1.5b after +1b, no tgt, no time stops', tgt=None, trail=(b, 1.5 * b), stall=None, deadline=None)
    evaluate('P5c trail 1.0b after +1b, no tgt, stall45, dl90', tgt=None, trail=(b, 1.0 * b))
    evaluate('P5d trail 2.0b after +1b, no tgt, stall45, dl90', tgt=None, trail=(b, 2.0 * b))
    evaluate('P6 tgt 2.0x', tgt=2.0 * b)
    evaluate('P7 tgt 3.5x', tgt=3.5 * b)
    L_entry = -(call(S0 * np.exp(-b), K, entry_t, dte) - P0) * LOT
    evaluate(f'P8 premium stop at same Rs as index stop ({L_entry:.0f})', stop_rule='none', prem_stop=L_entry)
    evaluate('P9 P0 + VWAP-cross exit (=VWAP ratchet)', vwap_exit=True)
    evaluate('P10 no tgt; at +2.5b trail 1.0b; stall45, dl90', tgt=None, trail=(a, 1.0 * b))
    evaluate('P11 NO index stop (prem backstop Rs1000), tgt, stall45, dl90', stop_rule='none', prem_stop=1000)
    evaluate('P12 trail 1.5b@+1b, no tgt, stall45/dl90 laggards only', tgt=None, trail=(b, 1.5 * b), laggard_only=True)
    evaluate('P13 trail 1.5b@+1b, no tgt, stall30/dl60 laggards only', tgt=None, trail=(b, 1.5 * b), stall=(30, 0.0005), deadline=60, laggard_only=True)
    evaluate('P14 tgt 2.5x, stall30/dl60 (all)', stall=(30, 0.0005), deadline=60)
    evaluate('P15 P13 + stop=max(stop,VWAP)', tgt=None, trail=(b, 1.5 * b), stall=(30, 0.0005), deadline=60, laggard_only=True, vwap_trail=True)
    evaluate('P16 stop=max(-b,VWAP) only, no tgt, stall30/dl60 laggards', tgt=None, trail=(b, 99.0), stall=(30, 0.0005), deadline=60, laggard_only=True, vwap_trail=True)
    base = res['P0 current (stop,2.5x tgt,stall45,dl90)'][1]
    print(f"\n=== entry t={entry_t} ({9*60+15+entry_t:d} min), dte={dte}, scen={scen}, K={K:.0f}, delta={delta_K:.2f}, "
          f"P0=Rs{P0:.1f}/unit (Rs{P0*LOT:.0f}/lot), b={b*100:.2f}% a={a*100:.2f}%  flipped={flip.mean():.2f}")
    print(f"{'policy':58s} {'mean':>7s} {'se':>5s} {'d_vs_P0':>8s} {'se_d':>5s} {'win':>5s} {'avgW':>6s} {'avgL':>6s} {'hold':>5s} {'idxbp':>6s}  exit mix")
    for name, (r, pnl) in res.items():
        d = pnl - base
        mix = ' '.join(f"{k2[:4]}={v:.2f}" for k2, v in r['mix'].items() if v > 0.005)
        print(f"{name:58s} {r['mean']:7.0f} {r['se']:5.0f} {d.mean():8.0f} {d.std()/np.sqrt(N):5.1f} {r['win']:5.2f} {r['avgwin']:6.0f} {r['avgloss']:6.0f} {r['hold']:5.0f} {r['idx']:6.2f}  {mix}")


if __name__ == '__main__':
    cases = [(45, 0, 345), (195, 0, 345), (45, 1, 355)]
    scens = ['nodrift', 'const', 'decay30', 'revert', 'trendpm', 'lowvol-nodrift', 'lowvol-const']
    sel = sys.argv[1] if len(sys.argv) > 1 else 'all'
    for (et, dte, ht) in cases:
        for sc in scens:
            run(et, dte, ht, sc)
