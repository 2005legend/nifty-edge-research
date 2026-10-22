"""Running one registry trial end to end (spec §6.3, design §14), behind a ticket.

1. **CPCV on 2019-2023:** for each of the 45 splits, train on the training days and trade the test days at the
   primary delay. The 9 paths come from the split results, and the median path is the one with the median t.
2. **Walk-forward:** train on 2019-2023 and trade 2024-2025.
3. **Delay test:** the same splits at a 3-minute delay; the median path must stay positive.
4. **Permutation:** each traded signal against its mirror (opposite side, same moment and moneyness),
   flipped at random within weekday x expiry-day x VIX-tercile buckets.
5. **Deflated Sharpe on per-available-day R:** N = 46 earlier looks + trials run. **PBO** over every trial
   run so far.
6. **Record:** the ticket's run goes into research/experiments.csv and research/trials/<id>/.
"""

import json
import math
from datetime import date, timedelta

import numpy as np
import pandas as pd

from quantdesk.backtest.engine import _trade, run_trial_split, signal_from
from quantdesk.backtest.training import train
from quantdesk.strategy.configs import config_for
from quantdesk.strategy.meta import Consensus, MetaModel
from quantdesk.strategy.types import Signal, StrikeChoice
from quantdesk.validation.cv import cpcv_splits, half_year_groups, paths, walk_forward
from quantdesk.validation.hypotheses import param
from quantdesk.validation.stats import (deflated_sharpe, pbo, permutation_p, post_publication_ratio, sharpe_stats,
                                        t_stat)

STEP = {"NIFTY": 50, "SENSEX": 100}


def _days(sessions: list[date], start: str, end: str) -> list[date]:
    a, b = date.fromisoformat(start), date.fromisoformat(end)
    return [d for d in sessions if a <= d <= b]


def _filled(trades: pd.DataFrame) -> pd.DataFrame:
    return trades[trades["status"] == "filled"] if len(trades) else trades


def daily_series(trades: pd.DataFrame, days: list[date]) -> pd.Series:
    by_day = trades.groupby("day")["r"].sum() if len(trades) else pd.Series(dtype=float)
    return by_day.reindex(days, fill_value=0.0).astype(float)


def _model_json(model) -> dict:
    if isinstance(model, MetaModel):
        return {"kind": "meta", **model.to_json()}
    return {"kind": "consensus", "a": model.a, "b": model.b}


def run_cpcv(dataset, cfg, source, h, today, delay, ticket, sessions):
    days = _days(sessions, param(h, "cv.cpcv_start"), param(h, "cv.cpcv_end"))
    groups = half_year_groups(days)
    splits = cpcv_splits(groups, param(h, "cv.cpcv_test_groups"), param(h, "cv.embargo_days"))
    results, models = [], {}
    for i, split in enumerate(splits):
        model = train(dataset, set(split.train), cfg, h)
        models[f"split{i}"] = _model_json(model)
        trades = run_trial_split(dataset, set(split.test), cfg, model, source, h, today, delay, ticket, sessions)
        results.append(trades.assign(split=i) if len(trades) else trades)
    path_list = []
    for j, path in enumerate(paths(splits, len(groups))):
        parts = []
        for g, s in path:
            t = results[s]
            if len(t):
                parts.append(t[t["day"].isin(set(groups[g]))])
        path_list.append(pd.concat(parts, ignore_index=True).assign(path=j) if parts else pd.DataFrame())
    return days, splits, results, path_list, models


def path_stats(trades: pd.DataFrame) -> dict:
    f = _filled(trades)
    r = f["r"].to_numpy(dtype=float) if len(f) else np.array([])
    return {"n": int(len(r)), "mean": float(r.mean()) if len(r) else float("nan"), "t": t_stat(r) if len(r) > 1 else float("nan")}


def median_path(path_list: list[pd.DataFrame]) -> tuple[int, pd.DataFrame]:
    stats = [(path_stats(p)["t"], j) for j, p in enumerate(path_list)]
    finite = sorted((t, j) for t, j in stats if not math.isnan(t))
    if not finite:
        return 0, path_list[0] if path_list else pd.DataFrame()
    j = finite[len(finite) // 2][1]
    return j, path_list[j]


def mirror_r(row, dataset, source, cfg, h, today, delay) -> float:
    """The opposite trade at the same moment: put for call, mirrored strike, mirrored stop and target."""
    sig = signal_from(dataset.signals[dataset.signals["signal_id"] == row["signal_id"]].iloc[0])
    side = "short" if sig.side == "long" else "long"
    sign = 1.0 if side == "long" else -1.0
    mirror = Signal(sig.index, sig.at, side, sig.ref_close, sig.upper, sig.lower, sig.vwap,
                    sig.ref_close - sign * sig.b, sig.b, sig.ref_close + sign * 2.3 * sig.b)
    step = STEP.get(sig.index, 50)
    atm = round(sig.ref_close / step) * step
    strike = 2 * atm - float(row["strike"])
    kind = "PE" if row["kind"] == "CE" else "CE"
    ctx = source.context(sig.index, row["day"])
    frame = source.frame(ctx)
    quotes = source.helpers(ctx, frame).quotes
    ask = quotes.quote(sig.index, row["expiry"], strike, kind, sig.at).ask
    choice = StrikeChoice(sig.index, row["expiry"], strike, kind, int(row["lot"]), ask, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    out = _trade(mirror, choice, source, cfg, h, today, delay, row["day"])
    return float(out["r"]) if out["status"] == "filled" else 0.0


def _bucket(row, terciles) -> str:
    return f"{row['weekday']}-{bool(row['expiry_day'])}-{terciles(row['vix_prev_close'])}"


def run_trial(trial_id: str, registry, dataset, source, h: dict, today: date, accepted: dict, prerequisites: dict,
              data_hash: str, sessions: list[date]) -> dict:
    cfg = config_for(trial_id, accepted)
    ticket = registry.issue_ticket(trial_id, data_hash, prerequisites)
    delay = param(h, "backtest.primary_delay_min")
    days, splits, results, path_list, models = run_cpcv(dataset, cfg, source, h, today, delay, ticket, sessions)
    j, med = median_path(path_list)
    _, _, _, delayed_paths, _ = run_cpcv(dataset, cfg, source, h, today, param(h, "h1.delay_sign_flip_minutes"),
                                         ticket, sessions)
    wf_days = _days(sessions, *param(h, "cv.walk_forward"))
    wf_split = walk_forward(sessions, date.fromisoformat(param(h, "cv.cpcv_end")),
                            date.fromisoformat(param(h, "cv.walk_forward")[0]),
                            date.fromisoformat(param(h, "cv.walk_forward")[1]), param(h, "cv.embargo_days"))
    wf_model = train(dataset, set(wf_split.train), cfg, h)
    models["walk_forward"] = _model_json(wf_model)
    wf = run_trial_split(dataset, set(wf_split.test), cfg, wf_model, source, h, today, delay, ticket, sessions)

    per_split_trades = [len(_filled(t)) for t in results]
    med_stats, wf_stats = path_stats(med), path_stats(wf)
    delayed = path_stats(delayed_paths[j]) if j < len(delayed_paths) else {"mean": float("nan")}
    daily = pd.concat([daily_series(med, days), daily_series(wf, wf_days)])
    sr, skew, kurt = sharpe_stats(daily.to_numpy())
    earlier = _earlier_daily(registry, days + wf_days)
    srs = [sharpe_stats(col)[0] for col in earlier.values()] + [sr]
    var = max(float(np.nanvar(srs, ddof=1)) if len([s for s in srs if not math.isnan(s)]) > 1 else 0.0,
              param(h, "gate.dsr_sr_sd_floor") ** 2)
    n_trials = param(h, "gate.n_prior") + ticket.cumulative_trials
    dsr = deflated_sharpe(sr, len(daily), skew, kurt, n_trials, var) if not math.isnan(sr) else float("nan")
    matrix = np.column_stack([*earlier.values(), daily.to_numpy()]) if earlier else None
    pbo_value = pbo(matrix, param(h, "gate.pbo_splits")) if matrix is not None else None

    filled = _filled(med)
    vix = dataset.signals["vix_prev_close"].astype(float)
    cuts = np.nanquantile(vix, [1 / 3, 2 / 3]) if vix.notna().any() else [np.inf, np.inf]
    tercile = lambda v: 1 if v <= cuts[0] else 2 if v <= cuts[1] else 3
    if len(filled):
        mirrors = np.array([mirror_r(r, dataset, source, cfg, h, today, delay) for _, r in filled.iterrows()])
        buckets = np.array([_bucket(r, tercile) for _, r in filled.iterrows()])
        perm = permutation_p(filled["r"].to_numpy(dtype=float), mirrors, buckets, param(h, "gate.permutation_rounds"), 7)
    else:
        perm = float("nan")
    years = param(h, "gate.years")
    both = pd.concat([_filled(med), _filled(wf)], ignore_index=True)
    year_means = both.groupby(both["day"].map(lambda d: d.year))["r"].mean() if len(both) else pd.Series(dtype=float)
    positive_years = int(sum(1 for y in years if y in year_means.index and year_means[y] > 0))
    after = _filled(wf)[_filled(wf)["day"] >= date.fromisoformat(param(h, "gate.post_publication_date"))] if len(wf) else wf
    ratio = post_publication_ratio(med_stats["mean"], float(after["r"].mean()) if len(after) else float("nan"))

    gates = {"trades_per_fold": float(np.median(per_split_trades)) >= param(h, "gate.min_trades_per_fold"),
             "t": med_stats["t"] >= param(h, "gate.t_min"),
             "walk_forward_positive": wf_stats["mean"] > 0,
             "years": positive_years >= param(h, "gate.years_positive_min"),
             "dsr": dsr >= param(h, "gate.dsr_min"),
             "pbo": pbo_value is None or pbo_value <= param(h, "gate.pbo_max"),
             "permutation": perm < param(h, "gate.permutation_p"),
             "delay_3": delayed["mean"] > 0,
             "post_publication": not ratio < param(h, "gate.post_publication_ratio")}
    gates = {k: bool(v) for k, v in gates.items()}
    passed = all(gates.values())
    metrics = {"config": json.dumps({"exit": cfg.exit_policy, "probability": cfg.probability,
                                     "hurdles": sorted(cfg.hurdles)}),
               "n_trades": med_stats["n"], "mean_net_r": med_stats["mean"], "t_stat": med_stats["t"], "dsr": dsr,
               "pbo": pbo_value, "verdict": "pass" if passed else "fail", "permutation_p": perm,
               "walk_forward": wf_stats, "delay_3": delayed, "median_path": j, "trades_per_split_median":
               float(np.median(per_split_trades)), "years_positive": positive_years, "post_publication_ratio": ratio,
               "gates": gates, "passed": passed, "daily_sr": sr, "n_trials_for_dsr": n_trials,
               "mean_net_r_asof": float(_filled(med)["r_asof"].mean()) if len(_filled(med)) else float("nan")}
    all_trades = pd.concat([med.assign(part="cpcv_median_path") if len(med) else med,
                            wf.assign(part="walk_forward") if len(wf) else wf], ignore_index=True)
    registry.record(ticket, metrics, all_trades, daily.rename("r").reset_index().rename(columns={"index": "day"}), models)
    return metrics


def _earlier_daily(registry, days: list[date]) -> dict[str, np.ndarray]:
    out = {}
    for trial in registry.trials_run():
        path = registry.dir / "trials" / trial / "daily_r.parquet"
        if path.exists():
            frame = pd.read_parquet(path)
            series = frame.set_index(frame.columns[0])["r"] if "r" in frame else frame.iloc[:, -1]
            out[trial] = series.reindex(days, fill_value=0.0).to_numpy(dtype=float)
    return out
