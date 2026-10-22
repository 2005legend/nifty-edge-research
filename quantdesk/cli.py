"""quantdesk command line: python -m quantdesk <command>."""

import argparse
import json
from dataclasses import asdict
from datetime import date, datetime, time, timedelta
from pathlib import Path

import numpy as np
import requests
import yaml

from quantdesk.app import build_app
from quantdesk.calendar.events import trading_days
from quantdesk.config import MissingSecretError, get_secret, project_root
from quantdesk.derived.daily import build_daily
from quantdesk.derived.macro import build_macro
from quantdesk.derived.members import build_members_minute
from quantdesk.derived.minutes import build_minutes, build_sessions
from quantdesk.derived.options import build_expiries, build_fii_ratio, build_options_eod
from quantdesk.derived.store import DerivedStore
from quantdesk.eod.bhavcopy import backfill_bhavcopy
from quantdesk.eod.flows import backfill_participant_oi, run_eod
from quantdesk.history.backfill import default_targets, run_backfill
from quantdesk.instruments import equity_tokens
from quantdesk.market.membership import load_membership
from quantdesk.macro.collect import run_macro_daily, run_macro_intraday
from quantdesk.news.collect import SeenIndex, poll_gdelt_once, poll_once, run_news_loop
from quantdesk.news.labels import sample_for_labelling, write_label_sheet
from quantdesk.power import keep_awake
from quantdesk.pricing.fitting import clock_sessions, fit_clock_from, fit_surface_from
from quantdesk.quality import build_health_report, write_health_report
from quantdesk.recorder.live import AlreadyRunningError, RecordingSummary, run_lock, run_recording
from quantdesk.validation.hypotheses import load_hypotheses, param

ANGEL_SECRETS = ["ANGEL_API_KEY", "ANGEL_CLIENT_CODE", "ANGEL_PIN", "ANGEL_TOTP_SECRET"]
DERIVE_TABLES = ["minutes", "sessions", "daily", "macro", "options_eod", "expiries", "fii_ratio", "members_minute"]


def missing_secrets(names: list[str]) -> list[str]:
    missing = []
    for name in names:
        try:
            get_secret(name)
        except MissingSecretError:
            missing.append(name)
    return missing


def _require(names: list[str]) -> bool:
    missing = missing_secrets(names)
    if missing:
        print(f"Missing secret(s): {', '.join(missing)} - copy .env.example to .env and fill them in.")
        return False
    return True


def _day(value: str | None, app) -> date:
    return date.fromisoformat(value) if value else app.clock.now().date()


def _health(app, day: date) -> dict:
    report = build_health_report(day, store=app.store, events=app.events, settings=app.settings)
    write_health_report(report, app.store)
    return report


def cmd_login_check(app, args) -> int:
    if not _require(ANGEL_SECRETS):
        return 2
    client = app.client()
    client.login()
    profile = client.profile() or {}
    print(f"session ok: {profile.get('name', '?')}")
    return 0


def cmd_record(app, args) -> int:
    if not _require(ANGEL_SECRETS):
        return 2
    day = app.clock.now().date()
    if not app.is_trading_day(day):  # before any download: the master alone is 35 MB
        app.store.write_report("recording", day, asdict(RecordingSummary(status="holiday")))
        print(f"recording holiday: {day} is not a trading day")
        return 0
    warnings = []
    try:
        constituents = app.constituents(day)
    except Exception as exc:  # noqa: BLE001 - options and indices are still recorded
        constituents = {}
        warnings.append(f"Nifty 50 list unavailable, recording without stocks: {type(exc).__name__}: {exc}"[:300])
    try:
        with keep_awake():
            summary = run_recording(day, client=app.client(), stream_factory=app.stream_factory,
                                    master=app.master(day), constituents=constituents, store=app.store,
                                    clock=app.clock, sleep=app.sleep, is_trading_day=app.is_trading_day,
                                    settings=app.settings)
    except AlreadyRunningError as exc:
        print(f"{exc} - nothing to do; leave that one running.")
        return 0
    fallback = app.master_fallback(day)
    summary.warnings = warnings + ([fallback] if fallback else []) + summary.warnings
    app.store.write_report("recording", day, asdict(summary))
    report = _health(app, day)
    print(f"recording {summary.status}: {summary.minutes_written} minutes; problems: {report['problems']}")
    for warning in summary.warnings:
        print(f"  warning: {warning}")
    for error in summary.errors:
        print(f"  error: {error}")
    return 1 if summary.status == "no_session" else 0


def cmd_backfill(app, args) -> int:
    """One copy per kind: the nightly job must not overlap a long manual run (they would store chunks twice)."""
    try:
        with run_lock(app.store, f"backfill-{args.what}"):
            return _backfill(app, args)
    except AlreadyRunningError as exc:
        print(f"{exc} - nothing to do; leave that one running.")
        return 0


def _backfill(app, args) -> int:
    today = app.clock.now().date()
    if args.what == "history":
        if not _require(ANGEL_SECRETS):
            return 2
        master = app.master(today)
        # Former members too (R7), so breadth and the VWAP proxy see the index as it was on each day.
        former = equity_tokens(master, load_membership().backfill_symbols())
        targets = default_targets(master, {**former, **app.constituents(today)}, app.settings, today)
        report = run_backfill(targets, app.client(), app.store, app.clock, app.settings)
        app.store.write_report("backfill", today, asdict(report))
        print(f"history backfill: {asdict(report)}")
    elif args.what == "bhavcopy":
        start = date.fromisoformat(args.start or app.settings["backfill"]["minute_start"])
        days = trading_days(start, today - timedelta(days=1), app.events)
        session = app.session()
        try:
            session.bootstrap(app.settings["urls"]["nse_home"])  # NSE serves files only with its cookies
        except Exception:  # noqa: BLE001 - best effort, like run_eod
            pass
        results = {}
        for exchange in ("NSE", "BSE"):
            status = backfill_bhavcopy(session, app.store, days, app.settings["urls"], exchange=exchange) or {}
            results[exchange] = {str(k): v for k, v in status.items()}
        app.store.write_report("bhavcopy_backfill", today, results)
        print(f"bhavcopy backfill: {sum(len(v) for v in results.values())} day-files checked")
    elif args.what == "participant_oi":
        start = date.fromisoformat(args.start or app.settings["backfill"]["minute_start"])
        days = trading_days(start, today - timedelta(days=1), app.events)
        session = app.session()
        try:
            session.bootstrap(app.settings["urls"]["nse_home"])
        except Exception:  # noqa: BLE001 - best effort, like run_eod
            pass
        status = backfill_participant_oi(session, app.store, days, app.settings["urls"]) or {}
        app.store.write_report("participant_oi_backfill", today, {str(k): v for k, v in status.items()})
        print(f"participant OI backfill: {len(status)} days checked")
    elif args.what == "macro":
        # Every daily series from 2015, for HAR, shock and stress (R13, R25). The economic calendar is too
        # large to page back through, and the NSE index file has its own backfill (--what fundamentals).
        start = date.fromisoformat(args.start or app.settings["backfill"]["daily_start"])
        skip = {"econ_calendar", "nifty_fundamentals", "india_gsec10y_price"}
        settings = dict(app.settings)
        settings["macro"] = {**app.settings["macro"],
                             "series": [s for s in app.settings["macro"]["series"] if s["id"] not in skip]}
        report = run_macro_daily(today, store=app.store, settings=settings, sleep=app.sleep, start=start)
        print(f"macro backfill: {report.status}")
    else:  # fundamentals
        start = date.fromisoformat(args.start or app.settings["backfill"]["daily_start"])
        settings = dict(app.settings)
        settings["macro"] = {**app.settings["macro"],
                             "series": [s for s in app.settings["macro"]["series"]
                                        if s["id"] in ("nifty_fundamentals", "india_gsec10y_price")]}
        end = date.fromisoformat(args.end) if args.end else today
        report = run_macro_daily(end, store=app.store, settings=settings, sleep=app.sleep, start=start)
        print(f"fundamentals backfill: {report.status}")
    return 0


def cmd_derive(app, args) -> int:
    try:
        with run_lock(app.store, "derive"):  # two rebuilds would race over the same table and manifest entry
            return _derive(app, args)
    except AlreadyRunningError as exc:
        print(f"{exc} - nothing to do; leave that one running.")
        return 0


def _derive(app, args) -> int:
    """Rebuild every derived table from data/raw. The order is the dependency order: sessions reads
    minutes, expiries reads options_eod, members_minute reads minutes and sessions."""
    derived = DerivedStore(app.store.root / "derived")
    h = load_hypotheses()
    holidays = {e.date for e in _all_events(app) if e.type == "holiday_nse"}
    builders = {
        "minutes": lambda: build_minutes(app.store, derived),
        "sessions": lambda: build_sessions(derived, app.settings["session"]),
        "daily": lambda: build_daily(app.store, derived),
        "macro": lambda: build_macro(app.store, derived),
        "options_eod": lambda: build_options_eod(app.store, derived, app.settings["urls"],
                                                 date.fromisoformat(param(h, "backtest.nifty_from")),
                                                 date.fromisoformat(param(h, "backtest.sensex_from")),
                                                 holidays),
        "expiries": lambda: build_expiries(derived),
        "fii_ratio": lambda: build_fii_ratio(app.store, derived),
        "members_minute": lambda: build_members_minute(derived, load_membership(), param(h, "gate.breadth_top_n")),
    }
    for name in [args.only] if args.only else DERIVE_TABLES:
        print(f"{name}: {builders[name]()}")
    print(f"data_hash {derived.data_hash()}")
    return 0


def frozen_dir() -> Path:
    return project_root() / "config" / "frozen"


def pilots_dir() -> Path:
    return project_root() / "research" / "pilots"


def cmd_fit(app, args) -> int:
    """Fit a frozen file once, on 2019-2022 (R15). A refit needs --force and an entry in docs/decisions.md."""
    from quantdesk.pricing.clock import load_clock, save_clock
    from quantdesk.pricing.surface import save_surface

    names = {"clock": "clock_v1.yaml", "surface": "surface_v1.yaml", "shock": "shock_v1.yaml"}
    target = frozen_dir() / names[args.what]
    if target.exists() and not args.force:
        print(f"{target} is already frozen. Refitting changes every later trial: pass --force and log why in docs/decisions.md.")
        return 1
    derived = DerivedStore(app.store.root / "derived")
    h = load_hypotheses()
    holidays = {e.date for e in app.events if e.type == "holiday_nse"}
    report = pilots_dir() / "CLOCK.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    if args.what == "clock":
        clock, meta, text = fit_clock_from(derived, h, holidays)
        save_clock(target, clock, meta)
        report.write_text(text, encoding="utf-8")
    elif args.what == "surface":
        clock = load_clock(frozen_dir() / names["clock"], clock_sessions(derived, holidays))
        surface, meta, text = fit_surface_from(derived, h, clock)
        save_surface(target, surface, meta)
        with open(report, "a", encoding="utf-8") as f:
            f.write(text)
    else:
        from quantdesk.analysis.hurdles import calibrate_cusum_h

        start, end = param(h, "clock.fit_start"), param(h, "clock.fit_end")
        daily = derived.read("daily", where=f"target = 'NIFTY' and day >= DATE '{start}' and day <= DATE '{end}'")
        returns = np.log(daily.sort_values("day")["close"]).diff().dropna()
        seed = 20261021
        threshold = calibrate_cusum_h(returns, param(h, "shock.cusum_sigma_window"), param(h, "shock.cusum_block"),
                                      param(h, "shock.cusum_resamples"),
                                      param(h, "hurdle.shock_cusum_false_alarms_per_year") / 250.0, seed)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(yaml.safe_dump({"h": float(threshold), "seed": seed, "fit_window": f"{start}..{end}",
                                          "data_hash": derived.data_hash(), "n_returns": int(len(returns))},
                                         sort_keys=False), encoding="utf-8")
        with open(report, "a", encoding="utf-8") as f:
            f.write(f"\n## Shock CUSUM\n\n- h = {threshold:.4f} (seed {seed}, {len(returns)} daily returns, "
                    f"target 1 alarm per 250 sessions)\n")
    print(f"wrote {target}; report {report}. If this is a refit, log it in docs/decisions.md.")
    return 0


def _all_events(app) -> list:
    """The live calendar plus the 2019-2026 history the backtest and pilots need (R9)."""
    from quantdesk.calendar.events import load_events

    history = project_root() / "config" / "events_history.yaml"
    return list(app.events) + (load_events(history) if history.exists() else [])


def cmd_pilot(app, args) -> int:
    """Zero-trial pilots (spec §6.3): they count, measure or simulate, and never rank profit."""
    import pandas as pd

    from quantdesk.validation.pilots import run
    from quantdesk.validation.pilots.p1_pass_rates import pass_rates
    from quantdesk.validation.pilots.p10_power import d2_report
    from quantdesk.validation.pilots.report import frame_to_markdown, write_report

    derived = DerivedStore(app.store.root / "derived")
    h = load_hypotheses()
    out = pilots_dir()
    out.mkdir(parents=True, exist_ok=True)
    data_hash = derived.data_hash()
    today = app.clock.now().date()
    pid = args.id
    if pid in ("P2", "P10", "D2"):
        records = pd.read_parquet(out / "p1_records.parquet")
        moves = pd.read_parquet(out / "p2_excursions.parquet")
        if pid == "P2":
            write_report("P2", run.p2_summary(moves), out / "P2.md", data_hash)
        elif pid == "P10":
            write_report("P10", run.run_p10(records, h), out / "P10.md", data_hash)
        else:
            text = d2_report(pass_rates(records), run.p2_summary(moves), run.run_p10(records, h), h)
            text += f"\nEligible days a year (one trade a day, both indices): {run.eligible_days_per_year(records):.0f}\n"
            (out / "D2.md").write_text(text, encoding="utf-8")
        print(f"wrote {out / (pid + '.md')}")
        return 0
    loader = run.make_loader(derived, h, _all_events(app), frozen_dir())
    if pid == "P4":
        write_report("P4", run.run_p4(loader), out / "P4.md", data_hash)
    elif pid == "P9":
        write_report("P9", run.run_p9(loader, h), out / "P9.md", data_hash,
                     notes="If `passed` is False, every VWAP rule switches to the open-anchored average price (spec §6.0).")
    else:
        records, moves = run.run_p1(loader, h, today, progress=lambda d: print(d) if d.day == 1 else None)
        records.to_parquet(out / "p1_records.parquet")
        moves.to_parquet(out / "p2_excursions.parquet")
        table = pass_rates(records)
        summary = {"signals": int(len(records)), "eligible_signals": int(records["failed"].isna().sum()),
                   "eligible_days_per_year": run.eligible_days_per_year(records)}
        for reason, count in records["failed"].fillna("eligible").value_counts().items():
            summary[f"outcome {reason}"] = int(count)
        write_report("P1", summary, out / "P1.md", data_hash, notes="## Pass rates\n\n" + frame_to_markdown(table))
    print(f"wrote {out / (pid + '.md')}")
    return 0


def _sp2(app):
    """What the SP2 commands share: the derived store, the pre-registration, the registry, the day loader."""
    from quantdesk.validation.pilots import run
    from quantdesk.validation.registry import Registry

    derived = DerivedStore(app.store.root / "derived")
    h = load_hypotheses()
    registry = Registry(project_root() / "research", project_root())
    return derived, h, registry, run


def cmd_dataset(app, args) -> int:
    """Stage A: every H1 signal with its gates, scores, label and candidates. No P&L is computed or shown."""
    from quantdesk.backtest.dataset import LoaderSource, build_dataset, save_dataset

    derived, h, _, run = _sp2(app)
    loader = run.make_loader(derived, h, _all_events(app), frozen_dir())
    today = app.clock.now().date()
    days = [d for d in loader.days if loader.kind.get(d) == "regular" and d < today]
    starts = {"NIFTY": date.fromisoformat(param(h, "backtest.nifty_from")),
              "SENSEX": date.fromisoformat(param(h, "backtest.sensex_from"))}
    dataset = build_dataset(LoaderSource(loader, h), days, starts, h, today,
                            progress=lambda d: print(d) if d.day == 1 else None)
    save_dataset(dataset, derived)
    counts = dataset.signals["failed"].fillna("passed every gate").value_counts().to_dict()
    print(f"signals: {len(dataset.signals)}; outcomes: {counts}; data_hash {derived.data_hash()}")
    return 0


def cmd_pricecheck(app, args) -> int:
    import json as _json

    from quantdesk.pricing.clock import load_clock
    from quantdesk.pricing.fitting import clock_sessions
    from quantdesk.pricing.pricecheck_run import run_pricecheck
    from quantdesk.pricing.surface import load_surface

    derived, h, _, _ = _sp2(app)
    holidays = {e.date for e in app.events if e.type == "holiday_nse"}
    clock = load_clock(frozen_dir() / "clock_v1.yaml", clock_sessions(derived, holidays))
    errors, result = run_pricecheck(app.store, clock, load_surface(frozen_dir() / "surface_v1.yaml"), h)
    path = project_root() / "research" / "pricecheck.json"
    path.write_text(_json.dumps({**result, "rows": int(len(errors))}, indent=2, default=str), encoding="utf-8")
    print(f"pricing check: median error {result['median_error']:.3f}, enough data {result['enough_data']}, "
          f"passed {result['passed']} ({result['sessions']} full sessions, {result['expiry_days']} expiry days)")
    return 0


def cmd_freeze(app, args) -> int:
    """Mark the pre-registration frozen and record its hash (prereg-v1). Commit and tag afterwards."""
    _, h, registry, _ = _sp2(app)
    path = registry.dir / "hypotheses.yaml"
    text = path.read_text(encoding="utf-8")
    if "frozen: false" in text:
        path.write_text(text.replace("frozen: false", "frozen: true", 1), encoding="utf-8")
    record = registry.freeze()
    print(f"frozen: hypotheses hash {record['hypotheses_hash']}. Now commit research/ and run: git tag prereg-v1")
    return 0


def cmd_preflight(app, args) -> int:
    import subprocess

    from quantdesk.validation.preflight import preflight

    _, h, registry, _ = _sp2(app)
    def run_tests(files):
        return subprocess.run([str(project_root() / ".venv" / "Scripts" / "python.exe"), "-m", "pytest", "-q", *files],
                              cwd=project_root(), capture_output=True).returncode
    checks = preflight(project_root(), registry, h, run_tests)
    lines = ["# Pre-flight (R36)", ""] + [f"- [{'x' if ok else ' '}] {name}" for name, ok in checks.items()]
    (project_root() / "research" / "PREFLIGHT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0 if checks["ready_for_B0"] else 1


def cmd_trial(app, args) -> int:
    from quantdesk.backtest.dataset import LoaderSource, load_dataset
    from quantdesk.validation.preflight import prerequisites
    from quantdesk.validation.registry import RegistryRefusal
    from quantdesk.validation.trial import run_trial
    from quantdesk.validation.verdict import evaluate

    derived, h, registry, run = _sp2(app)
    accepted = evaluate(registry, h, pricing_passed=True)["accepted"]
    pre = prerequisites(args.id, accepted, registry.trials_run(), registry.dir, h)
    loader = run.make_loader(derived, h, _all_events(app), frozen_dir())
    try:
        metrics = run_trial(args.id, registry, load_dataset(derived), LoaderSource(loader, h), h,
                            app.clock.now().date(), accepted, pre, derived.data_hash(), loader.days)
    except RegistryRefusal as exc:
        print(f"refused: {exc}")
        return 1
    print(f"{args.id}: {metrics['verdict']}; gates {metrics['gates']}")
    return 0


def cmd_verdict(app, args) -> int:
    from quantdesk.validation.preflight import pricing_passed
    from quantdesk.validation.verdict import evaluate, write_verdict

    _, h, registry, _ = _sp2(app)
    result = evaluate(registry, h, pricing_passed(registry.dir))
    path = write_verdict(result, registry.dir / "VERDICT.md")
    print(f"verdict: {result['status']} ({result.get('config')}); {path}")
    return 0


def _journal(app):
    from quantdesk.live.journal import Journal

    return Journal(app.store.root / "journal.sqlite")


def _serve(app_, port: int):
    import uvicorn

    return uvicorn.Server(uvicorn.Config(app_, host="127.0.0.1", port=port, log_level="warning"))


def cmd_live(app, args) -> int:
    """S1: the decision loop, paper trades, Telegram and the dashboard, 09:10 to 15:35."""
    import threading

    from quantdesk.live.dashboard import create_app
    from quantdesk.live.notify import format_summary, notifier_from_env
    from quantdesk.live.run import build_engine, run_loop

    now = app.clock.now()
    today = now.date()
    if not app.is_trading_day(today):
        print(f"{today} is not a trading day")
        return 0
    journal, notifier, research = _journal(app), notifier_from_env(), project_root() / "research"
    try:
        engine, mode, trial = build_engine(app, today, journal, notifier, _all_events(app), frozen_dir(), research)
    except RuntimeError as exc:
        journal.log_event("not_started", str(exc), at=now)
        print(f"not started: {exc}")
        return 1
    journal.set_state("verdict_mode", mode)
    journal.log_event("start", f"mode {mode}, configuration {trial}", at=now)
    server = _serve(create_app(journal, research, engine.h, today=lambda: today, sessions=engine.sessions,
                               snapshot=engine.snapshot), args.port)
    threading.Thread(target=server.run, daemon=True).start()
    print(f"live: mode {mode}, configuration {trial}; dashboard http://127.0.0.1:{args.port}")
    start = datetime.combine(today, time(9, 10), tzinfo=now.tzinfo)
    end = datetime.combine(today, time(15, 35), tzinfo=now.tzinfo)

    def on_error(at, exc):
        journal.log_event("error", f"{type(exc).__name__}: {exc}"[:300], at=at)

    with keep_awake():
        steps = run_loop(engine.step, app.clock.now, app.sleep, start, end, every=5, on_error=on_error)
    alerts = journal.alerts(today.isoformat())
    closed = journal.closed_trades("paper")
    day_r = float(closed.loc[closed["entry_at"].str[:10] == today.isoformat(), "r"].sum()) if len(closed) else 0.0
    notifier.send(format_summary(today, len(alerts), day_r, mode))
    server.should_exit = True
    print(f"live done: {steps} steps, {len(alerts)} alert(s), paper {day_r:+.2f}R")
    return 0


def cmd_dashboard(app, args) -> int:
    """The journal and research views outside market hours (the live process serves them during the day)."""
    from quantdesk.live.dashboard import create_app
    from quantdesk.live.run import year_sessions

    today = app.clock.now().date()
    server = _serve(create_app(_journal(app), project_root() / "research", load_hypotheses(),
                               today=lambda: app.clock.now().date(), sessions=year_sessions(today, app.events)),
                    args.port)
    print(f"dashboard: http://127.0.0.1:{args.port} (Ctrl+C to stop)")
    server.run()
    return 0


def cmd_replay(app, args) -> int:
    """S12: a recorded day through the live engine on a simulated clock, checked against decide()."""
    from quantdesk.live.journal import Journal
    from quantdesk.live.replay import backtest_day, replay_day, summary
    from quantdesk.live.run import strategy_for
    from quantdesk.live.source import LiveDaySource
    from quantdesk.market.membership import load_membership
    from quantdesk.validation.pilots.run import make_loader

    day = date.fromisoformat(args.day)
    derived, h = DerivedStore(app.store.root / "derived"), load_hypotheses()
    bars = app.store.read("bars", day)
    if bars.empty:
        print(f"no recorded bars for {day}")
        return 1
    try:
        trial, cfg, model, _, _ = strategy_for(derived, project_root() / "research", h, day)
    except RuntimeError as exc:
        print(f"not run: {exc}")
        return 1
    loader = make_loader(derived, h, _all_events(app), frozen_dir())
    token_symbol = {token: symbol for symbol, token in app.constituents(day).items()}
    source = LiveDaySource(loader, day, bars, app.store.read("option_snapshots", day),
                           app.store.read("option_meta", day), token_symbol, load_membership(), h)
    path = app.store.root / "replay" / f"journal-{day.isoformat()}.sqlite"
    path.unlink(missing_ok=True)                   # this command's own scratch journal, rebuilt each run
    live = replay_day(source, day, cfg, model, h, Journal(path))
    back = backtest_day(source, day, cfg, model, h)
    seen = {(d.index, d.at) for d in live}
    same = summary(live) == summary([d for d in back if (d.index, d.at) in seen])
    alerts = [d for d in live if d.alert is not None]
    print(f"replay {day} ({trial}): {len(live)} checks, {len(alerts)} alert(s); parity with decide(): {same}")
    for d in alerts:
        print(f"  {d.at:%H:%M} {d.index} {d.alert.side} {d.alert.choice.strike:.0f} {d.alert.choice.kind} "
              f"p {d.alert.p:.2f}")
    print(f"journal: {path}")
    return 0 if same else 1


def cmd_telegram_setup(app, args) -> int:
    """Find the owner's chat with the bot, save TELEGRAM_CHAT_ID in .env and send a test message.
    Neither the token nor the chat id is printed."""
    from quantdesk.live.notify import Telegram, find_chat_id
    from quantdesk.live.run import set_env_value

    try:
        token = get_secret("TELEGRAM_BOT_TOKEN")
    except MissingSecretError as exc:
        print(exc)
        return 2
    try:
        chat = find_chat_id(token)
    except Exception as exc:  # noqa: BLE001 - the message may carry the URL, so the token is masked
        print(f"could not reach Telegram: {type(exc).__name__}: {str(exc).replace(token, '<token>')}"[:300])
        return 1
    if chat is None:
        print('No message found. Open your bot in Telegram, send it any message (say "hi"), then run this again.')
        return 1
    set_env_value(project_root() / ".env", "TELEGRAM_CHAT_ID", chat)
    ok = Telegram(token, chat).send("quantdesk is connected. Alerts, stop moves and exits will arrive here.")
    print(f"chat id saved to .env; test message {'sent' if ok else 'NOT sent - check the bot'}")
    return 0 if ok else 1


def cmd_eod(app, args) -> int:
    day = _day(args.day, app)
    if not app.is_trading_day(day):
        print(f"eod {day}: holiday, nothing to download")
        return 0
    client = None
    if missing_secrets(ANGEL_SECRETS):
        print("Angel One secrets missing: the India VIX daily candle is skipped; NSE/BSE files still download.")
    else:
        client = app.client()
    until = time.fromisoformat(args.until or app.settings["eod"]["retry_until"])
    report = run_eod(day, session=app.session(), store=app.store, client=client, clock=app.clock,
                     sleep=app.sleep, settings=app.settings, until=until)
    app.store.write_report("eod", day, asdict(report))
    print(f"eod {day}: {report.status}")
    return 0


def cmd_macro(app, args) -> int:
    if not args.intraday:
        day = app.clock.now().date()
        report = run_macro_daily(day, store=app.store, settings=app.settings, sleep=app.sleep)
        app.store.write_report("macro", day, asdict(report))
        print(f"macro {day}: {report.status}")
        return 0
    macro = app.settings["macro"]
    start, end = (time.fromisoformat(t) for t in macro["intraday_window"])
    while True:
        now = app.clock.now()
        if now.time() >= end or not app.is_trading_day(now.date()):
            return 0
        if now.time() >= start:
            report = run_macro_intraday(now, store=app.store, settings=app.settings)
            app.store.write_report("macro_intraday", now.date(), asdict(report))
        app.sleep(macro["intraday_every_minutes"] * 60)


def cmd_news(app, args) -> int:
    config = yaml.safe_load((project_root() / "config" / "news_feeds.yaml").read_text(encoding="utf-8"))
    seen = SeenIndex(app.store.root / "state" / "news_seen.txt")
    http_get = lambda url: requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})  # noqa: E731

    def poll():
        now = app.clock.now()
        report = poll_once(config["feeds"], http_get=http_get, store=app.store, clock=app.clock, seen=seen)
        previous = app.store.read_report("news", now.date()) or {"new_items": {}, "failed": [], "stale": []}
        merged = {name: previous["new_items"].get(name, 0) + n for name, n in report.new_items.items()}
        app.store.write_report("news", now.date(), {"new_items": {**previous["new_items"], **merged},
                                                    "failed": report.failed, "stale": report.stale})
        try:
            poll_gdelt_once(http_get=http_get, store=app.store, clock=app.clock,
                            lastupdate_url=config["gdelt_lastupdate"], themes=config["gdelt_themes"])
        except Exception as exc:  # noqa: BLE001 - GDELT is optional
            print(f"gdelt skipped: {type(exc).__name__}")
        print(f"news {now:%H:%M}: new {report.new_items}; failed {report.failed}; stale {report.stale}")

    try:
        with run_lock(app.store, "news"):  # two pollers would store every headline twice
            if args.once:
                poll()
                return 0
            run_news_loop(poll=poll, clock=app.clock, sleep=app.sleep, is_trading_day=app.is_trading_day,
                          schedule=config["schedule"])
    except AlreadyRunningError as exc:
        print(f"{exc} - nothing to do; leave that one running.")
    return 0


LABEL_GUIDE = """Pilot 8 headline labels (spec section 6.3). Label every row BEFORE any model scores these headlines.
tone: negative / neutral / positive - for the Indian index market (Nifty/Sensex), not for one company.
market_moving: yes / no - could it move Nifty or Sensex by about 0.3% or more within the day?
notes: optional. Leave a row's labels empty if you cannot tell; it will be skipped.
Save as CSV (keep the file name). Then tell Claude the labels are done.
"""


def cmd_label_sample(app, args) -> int:
    path = app.store.root / "labels" / "pilot8_headlines.csv"
    sheet = sample_for_labelling(app.store.read("news"), n=args.n, seed=args.seed)
    try:
        write_label_sheet(sheet, path)
    except FileExistsError as exc:
        print(exc)
        return 1
    (path.parent / "README.txt").write_text(LABEL_GUIDE, encoding="utf-8")
    print(f"wrote {len(sheet)} headlines from {sheet['feed'].nunique()} feeds to {path}")
    return 0


def cmd_status(app, args) -> int:
    day = _day(args.day, app)
    report = app.store.read_report("health", day) or _health(app, day)
    print(json.dumps({k: report.get(k) for k in ("date", "trading_day", "minutes_expected", "minutes_recorded",
                                                "option_tokens_recorded", "problems") if k in report}, indent=2))
    backfill = app.store.read_report("backfill", day)
    if backfill:
        print(f"backfill: {backfill}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="quantdesk", description="Nifty/Sensex data foundation")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("login-check", help="verify Angel One credentials").set_defaults(func=cmd_login_check)
    sub.add_parser("record", help="record today's market session").set_defaults(func=cmd_record)
    backfill = sub.add_parser("backfill", help="download history")
    backfill.add_argument("--what", choices=["history", "bhavcopy", "fundamentals", "participant_oi", "macro"], required=True)
    backfill.add_argument("--start")
    backfill.add_argument("--end", help="last day to fetch (fundamentals only; default today)")
    backfill.set_defaults(func=cmd_backfill)
    sub.add_parser("dataset", help="stage A: the signal dataset (no P&L)").set_defaults(func=cmd_dataset)
    sub.add_parser("pricecheck", help="the recorded-chain pricing check (R17)").set_defaults(func=cmd_pricecheck)
    sub.add_parser("freeze", help="freeze the pre-registration (prereg-v1)").set_defaults(func=cmd_freeze)
    sub.add_parser("preflight", help="the checklist before trial B0 (R36)").set_defaults(func=cmd_preflight)
    trial = sub.add_parser("trial", help="run one registry trial, with a ticket")
    trial.add_argument("id")
    trial.set_defaults(func=cmd_trial)
    sub.add_parser("verdict", help="alert-on or alert-off from the trials run").set_defaults(func=cmd_verdict)
    live = sub.add_parser("live", help="the live engine, Telegram and the dashboard, 09:10-15:35")
    live.add_argument("--port", type=int, default=8000)
    live.set_defaults(func=cmd_live)
    dash = sub.add_parser("dashboard", help="the journal and research views outside market hours")
    dash.add_argument("--port", type=int, default=8000)
    dash.set_defaults(func=cmd_dashboard)
    replay = sub.add_parser("replay", help="a recorded day through the live engine, checked against decide()")
    replay.add_argument("--day", required=True)
    replay.set_defaults(func=cmd_replay)
    sub.add_parser("telegram-setup", help="save the chat id after you message the bot").set_defaults(
        func=cmd_telegram_setup)
    pilot = sub.add_parser("pilot", help="run a zero-trial pilot (P1, P2, P4, P9, P10, D2)")
    pilot.add_argument("id", choices=["P1", "P2", "P4", "P9", "P10", "D2"])
    pilot.set_defaults(func=cmd_pilot)
    fit = sub.add_parser("fit", help="fit a frozen file on 2019-2022 (clock, surface, shock)")
    fit.add_argument("what", choices=["clock", "surface", "shock"])
    fit.add_argument("--force", action="store_true", help="overwrite an existing frozen file (log it in decisions.md)")
    fit.set_defaults(func=cmd_fit)
    derive = sub.add_parser("derive", help="rebuild every derived table from data/raw")
    derive.add_argument("--only", choices=DERIVE_TABLES, help="rebuild one table instead of all of them")
    derive.set_defaults(func=cmd_derive)
    eod = sub.add_parser("eod", help="end-of-day NSE/BSE downloads")
    eod.add_argument("--day")
    eod.add_argument("--until")
    eod.set_defaults(func=cmd_eod)
    macro = sub.add_parser("macro", help="global and macro data")
    macro.add_argument("--intraday", action="store_true")
    macro.set_defaults(func=cmd_macro)
    news = sub.add_parser("news", help="India news collector")
    news.add_argument("--once", action="store_true")
    news.set_defaults(func=cmd_news)
    label = sub.add_parser("label-sample", help="headlines for the owner to label (pilot 8)")
    label.add_argument("--n", type=int, default=300)
    label.add_argument("--seed", type=int, default=8)
    label.set_defaults(func=cmd_label_sample)
    status = sub.add_parser("status", help="data health summary")
    status.add_argument("--day")
    status.set_defaults(func=cmd_status)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    app = build_app()
    return args.func(app, args)
