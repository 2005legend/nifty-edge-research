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
    builders = {
        "minutes": lambda: build_minutes(app.store, derived),
        "sessions": lambda: build_sessions(derived, app.settings["session"]),
        "daily": lambda: build_daily(app.store, derived),
        "macro": lambda: build_macro(app.store, derived),
        "options_eod": lambda: build_options_eod(app.store, derived, app.settings["urls"],
                                                 date.fromisoformat(param(h, "backtest.nifty_from")),
                                                 date.fromisoformat(param(h, "backtest.sensex_from"))),
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
            f.write(f"
## Shock CUSUM

- h = {threshold:.4f} (seed {seed}, {len(returns)} daily returns, "
                    f"target 1 alarm per 250 sessions)
")
    print(f"wrote {target}; report {report}. If this is a refit, log it in docs/decisions.md.")
    return 0


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
