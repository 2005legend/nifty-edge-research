"""Running the live process (SP3 design S1, S2, S9): what `python -m quantdesk live` puts together.

- **Mode:** from `research/VERDICT.md`. Alert-on means live; anything else, or no verdict yet, means shadow.
- **Configuration:** the last accepted trial, else B0, with its model fitted on every labelled signal before
  today. Without the signal dataset there is no model, and the process refuses to start rather than log
  shadow setups from an unfitted model into the forward holdout.
- **Kill-switch levels:** from the accepted trial's median-path trades. The CUSUM threshold is bootstrapped
  from those trades for about one false alarm per 250 trades.
- **Loop:** waits for 09:10 and steps every 5 seconds until 15:35. One bad step is journalled and the loop
  carries on.
"""

import os
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np

ARL = 250


def verdict_mode(research_dir: Path) -> str:
    path = Path(research_dir) / "VERDICT.md"
    return "live" if path.exists() and "**alert-on**" in path.read_text(encoding="utf-8") else "shadow"


def cusum_threshold(r, target: float, k: float, arl: int = ARL, paths: int = 400, seed: int = 0) -> float:
    """The threshold h whose mean in-control run length, resampling the validated trades, is `arl`."""
    rng = np.random.default_rng(seed)
    length = 8 * arl
    draws = rng.choice(np.asarray(r, dtype=float), size=(paths, length))
    s = np.zeros(paths)
    path = np.empty((paths, length))
    for t in range(length):
        s = np.maximum(0.0, s + (target - draws[:, t]) - k)
        path[:, t] = s
    peak = np.maximum.accumulate(path, axis=1)

    def mean_run(h):
        crossed = peak > h
        return np.where(crossed.any(axis=1), crossed.argmax(axis=1) + 1, length).mean()

    lo, hi = 0.0, float(peak[:, -1].max())
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if mean_run(mid) < arl else (lo, mid)
    return hi


def kill_params(r) -> dict:
    """mu0, breakeven, sigma and cusum_h for `monitor.kill_switches`, from the validated per-trade net R."""
    r = np.asarray(r, dtype=float)
    mu0 = float(r.mean())
    if mu0 <= 0:
        raise ValueError(f"an accepted trial has a positive mean net R; got {mu0:.3f}")
    target = mu0 - 0.5 * mu0
    return {"mu0": mu0, "breakeven": 0.0, "sigma": float(r.std(ddof=1)),
            "cusum_h": cusum_threshold(r, target, 0.5 * (mu0 - target))}


def rebuild_on_change(key, build):
    """`key(now)` is cheap (a count of the recorder's files); `build(now)` is not, so it runs only on a change."""
    state = {}

    def make(now):
        k = key(now)
        if "value" not in state or state["key"] != k:
            state["key"], state["value"] = k, build(now)
        return state["value"]

    return make


def run_loop(step, now_fn, sleep, start: datetime, end: datetime, every: float = 5.0, on_error=None) -> int:
    while (now := now_fn()) < start:
        sleep(min(every, (start - now).total_seconds()))
    steps = 0
    while (now := now_fn()) <= end:
        try:
            step(now)
        except Exception as exc:  # noqa: BLE001 - one bad step must not end the trading day
            if on_error:
                on_error(now, exc)
        steps += 1
        sleep(every)
    return steps


def set_env_value(path: Path, key: str, value: str) -> None:
    """Set KEY=value in a .env file, leaving every other line alone. The value is never printed."""
    path = Path(path)
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    out, found = [], False
    for line in lines:
        if line.split("=", 1)[0].strip() == key:
            out.append(f"{key}={value}")
            found = True
        else:
            out.append(line)
    if not found:
        out.append(f"{key}={value}")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def file_count(folder: Path) -> int:
    return sum(1 for _ in os.scandir(folder)) if folder.exists() else 0


def strategy_for(derived, research: Path, h: dict, before: date):
    """S2: the last accepted trial, else B0, with its model fitted on every labelled signal before `before`.
    Returns (trial id, config, model, verdict result, registry)."""
    from quantdesk.backtest.dataset import load_dataset
    from quantdesk.backtest.training import train
    from quantdesk.strategy.configs import config_for
    from quantdesk.validation.preflight import pricing_passed
    from quantdesk.validation.registry import Registry
    from quantdesk.validation.verdict import evaluate

    registry = Registry(research, research.parent)
    result = evaluate(registry, h, pricing_passed(research))
    trial = result["config"] or "B0"
    cfg = config_for(trial, result["accepted"])
    try:
        dataset = load_dataset(derived)
    except Exception as exc:  # noqa: BLE001 - no signals table yet
        raise RuntimeError("no signal dataset yet: run `python -m quantdesk dataset` first") from exc
    model = train(dataset, {d for d in dataset.signals["day"] if d < before}, cfg, h)
    return trial, cfg, model, result, registry


def build_engine(app, today: date, journal, notifier, events: list, frozen: Path, research: Path):
    """The live engine for `today`, wired to the recorder's files. Returns (engine, mode, config id)."""
    from quantdesk.derived.store import DerivedStore
    from quantdesk.live.engine import LiveEngine
    from quantdesk.live.source import LiveDaySource
    from quantdesk.market.membership import load_membership
    from quantdesk.validation.hypotheses import load_hypotheses
    from quantdesk.validation.pilots.run import make_loader
    from quantdesk.validation.verdict import _trades

    derived = DerivedStore(app.store.root / "derived")
    h = load_hypotheses()
    trial, cfg, model, result, registry = strategy_for(derived, research, h, today)
    mode = verdict_mode(research)
    kill = None
    if mode == "live" and result["config"]:
        kill = kill_params(_trades(registry, result["config"])["r"].to_numpy(dtype=float))
    loader = make_loader(derived, h, events, frozen)
    last = max(d for d in loader.days if d < today)
    if not derived_is_current(last, today, events):
        raise RuntimeError(f"the derived tables end on {last}: run `python -m quantdesk derive` after the evening "
                           "downloads (the nightly derive job does this)")
    membership = load_membership()
    token_symbol = {token: symbol for symbol, token in app.constituents(today).items()}
    raw = app.store.root / "raw"

    def build(now):
        return LiveDaySource(loader, today, app.store.read("bars", today), app.store.read("option_snapshots", today),
                             app.store.read("option_meta", today), token_symbol, membership, h)

    def key(now):
        return tuple(file_count(raw / kind / f"date={today.isoformat()}")
                     for kind in ("bars", "option_snapshots", "option_meta"))

    from quantdesk.live.brief import brief_extras, morning_brief
    from quantdesk.validation.pilots.run import IDEAS_SCENARIO, with_values

    def brief(now, ctxs, frames):
        return morning_brief(now, ctxs, frames, brief_extras(app.store, derived, today), h)

    idea = mode != "live"            # alert-off: the owner's idea feed, sized by the owner (22 Oct 2026)
    engine = LiveEngine(rebuild_on_change(key, build), journal, notifier, cfg, model,
                        with_values(h, IDEAS_SCENARIO) if idea else h, today, mode=mode, kill_params=kill,
                        sessions=year_sessions(today, events), idea=idea, brief=brief)
    return engine, "idea" if idea else mode, trial


def derived_is_current(last_session: date, today: date, events: list) -> bool:
    """True when the derived tables reach the session before `today`. Without it the day card would take an
    older close as yesterday's, and every band and gap would be wrong."""
    from quantdesk.calendar.events import is_trading_day

    previous = today - timedelta(days=1)
    while not is_trading_day(previous, events):
        previous -= timedelta(days=1)
    return last_session >= previous


def year_sessions(day: date, events: list) -> list[date]:
    """Every NSE session of `day`'s calendar year: the monthly cap is this month's share of the whole year."""
    from quantdesk.calendar.events import trading_days

    return trading_days(date(day.year, 1, 1), date(day.year, 12, 31), events)
