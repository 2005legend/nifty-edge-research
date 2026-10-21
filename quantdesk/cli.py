"""quantdesk command line: python -m quantdesk <command>."""

import argparse
import json
from dataclasses import asdict
from datetime import date, datetime, time, timedelta

import requests
import yaml

from quantdesk.app import build_app
from quantdesk.calendar.events import trading_days
from quantdesk.config import MissingSecretError, get_secret, project_root
from quantdesk.eod.bhavcopy import backfill_bhavcopy
from quantdesk.eod.flows import run_eod
from quantdesk.history.backfill import default_targets, run_backfill
from quantdesk.macro.collect import run_macro_daily, run_macro_intraday
from quantdesk.news.collect import SeenIndex, poll_gdelt_once, poll_once, run_news_loop
from quantdesk.quality import build_health_report, write_health_report
from quantdesk.recorder.live import AlreadyRunningError, run_recording

ANGEL_SECRETS = ["ANGEL_API_KEY", "ANGEL_CLIENT_CODE", "ANGEL_PIN", "ANGEL_TOTP_SECRET"]


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
    try:
        summary = run_recording(day, client=app.client(), stream_factory=app.stream_factory,
                                master=app.master(day), constituents=app.constituents(day), store=app.store,
                                clock=app.clock, sleep=app.sleep, is_trading_day=app.is_trading_day,
                                settings=app.settings)
    except AlreadyRunningError as exc:
        print(f"{exc} - nothing to do; leave that one running.")
        return 0
    app.store.write_report("recording", day, asdict(summary))
    report = _health(app, day)
    print(f"recording {summary.status}: {summary.minutes_written} minutes; problems: {report['problems']}")
    for error in summary.errors:
        print(f"  error: {error}")
    return 1 if summary.status == "no_session" else 0


def cmd_backfill(app, args) -> int:
    today = app.clock.now().date()
    if args.what == "history":
        if not _require(ANGEL_SECRETS):
            return 2
        targets = default_targets(app.master(today), app.constituents(today), app.settings, today)
        report = run_backfill(targets, app.client(), app.store, app.clock, app.settings)
        app.store.write_report("backfill", today, asdict(report))
        print(f"history backfill: {asdict(report)}")
    elif args.what == "bhavcopy":
        start = date.fromisoformat(args.start or app.settings["backfill"]["minute_start"])
        days = trading_days(start, today - timedelta(days=1), app.events)
        session = app.session()
        results = {}
        for exchange in ("NSE", "BSE"):
            status = backfill_bhavcopy(session, app.store, days, app.settings["urls"], exchange=exchange) or {}
            results[exchange] = {str(k): v for k, v in status.items()}
        app.store.write_report("bhavcopy_backfill", today, results)
        print(f"bhavcopy backfill: {sum(len(v) for v in results.values())} day-files checked")
    else:  # fundamentals
        start = date.fromisoformat(args.start or app.settings["backfill"]["daily_start"])
        settings = dict(app.settings)
        settings["macro"] = {**app.settings["macro"],
                             "series": [s for s in app.settings["macro"]["series"] if s["id"] == "nifty_fundamentals"]}
        report = run_macro_daily(today, store=app.store, settings=settings, sleep=app.sleep, start=start)
        print(f"fundamentals backfill: {report.status}")
    return 0


def cmd_eod(app, args) -> int:
    if not _require(ANGEL_SECRETS):
        return 2
    day = _day(args.day, app)
    until = time.fromisoformat(args.until or app.settings["eod"]["retry_until"])
    report = run_eod(day, session=app.session(), store=app.store, client=app.client(), clock=app.clock,
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

    if args.once:
        poll()
        return 0
    run_news_loop(poll=poll, clock=app.clock, sleep=app.sleep, is_trading_day=app.is_trading_day,
                  schedule=config["schedule"])
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
    backfill.add_argument("--what", choices=["history", "bhavcopy", "fundamentals"], required=True)
    backfill.add_argument("--start")
    backfill.set_defaults(func=cmd_backfill)
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
    status = sub.add_parser("status", help="data health summary")
    status.add_argument("--day")
    status.set_defaults(func=cmd_status)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    app = build_app()
    return args.func(app, args)
