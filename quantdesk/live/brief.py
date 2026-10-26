"""The owner's daily feed (22 Oct 2026): the 09:20 morning brief, the 15:35 day summary and the Friday scorecard.

- **Morning brief:** global cues, FII positioning, a rough news tone, and for each index the open and gap, the
  expected range (the HAR forecast already used by the strategy), VIX, put/call ratio, levels, expiry, events
  and a direction lean.
- **The lean is experimental.** It sums three signs: the options score (put/call ratio and skew, z-scored), the
  flows score (FII positioning, post-holiday gaps) and the overnight move of US futures. Research puts
  direction close to a coin flip, so every lean is scored at the close and the Friday scorecard shows its hit
  rate.
- **Day summary and scorecard** count the ideas in rupees per lot, as paper trades of one lot each.
"""

import math
import re
from datetime import date, datetime, timedelta

import pandas as pd

CUES = {"spx": "S&P 500", "nq": "Nasdaq fut", "es": "S&P fut", "n225": "Nikkei", "hsi": "Hang Seng",
        "kospi": "Kospi", "brent": "Brent", "usdinr": "USD/INR", "dxy": "Dollar index", "us10y": "US 10y"}
UP_WORDS = r"surge|surges|rally|rallies|gain|gains|jump|jumps|soar|soars|record high|upgrade|beats|rate cut|" \
           r"inflow|inflows|bullish|rebound|rebounds|rises|climbs|recovers"
DOWN_WORDS = r"fall|falls|slump|slumps|plunge|plunges|crash|drop|drops|sell-off|selloff|downgrade|misses|" \
             r"rate hike|outflow|outflows|bearish|war|tension|tensions|tariff|tariffs|declines|slides|tumble|" \
             r"tumbles|record low|fears"
LEAN_AT = 1.0


def news_sentiment(titles: list[str]) -> dict:
    up = sum(bool(re.search(rf"\b({UP_WORDS})\b", t, re.I)) for t in titles)
    down = sum(bool(re.search(rf"\b({DOWN_WORDS})\b", t, re.I)) for t in titles)
    label = "no news" if not titles else "positive" if up > down else "negative" if down > up else "mixed"
    return {"positive": up, "negative": down, "headlines": len(titles), "label": label}


def global_cues(rows: pd.DataFrame) -> list[dict]:
    """The latest value of each series and its change from the value before, in percent."""
    out = []
    for sid, name in CUES.items():
        s = rows[rows["series_id"] == sid].sort_values("date").drop_duplicates("date", keep="last")
        if len(s) >= 2:
            last, prev = float(s["value"].iloc[-1]), float(s["value"].iloc[-2])
            out.append({"name": name, "value": last, "change_pct": 100.0 * (last / prev - 1.0) if prev else 0.0})
    return out


def lean(options: float, flows: float, glob: float) -> tuple[str, float, dict]:
    parts = {"options": options, "FII": flows, "global": glob}
    score = sum(parts.values())
    label = "UP" if score >= LEAN_AT else "DOWN" if score <= -LEAN_AT else "FLAT"
    return label, score, parts


def _global_sign(cues: list[dict]) -> float:
    us = [c["change_pct"] for c in cues if c["name"] in ("S&P fut", "Nasdaq fut", "S&P 500")]
    return max(-1.0, min(1.0, sum(us) / len(us))) if us else 0.0


def _options_z(ctx, h: dict) -> float:
    from quantdesk.strategy.pipeline import _options_score

    try:
        z = _options_score(ctx, 1.0, h)
    except Exception:  # noqa: BLE001 - no reference yet: the options part counts as zero
        z = None
    return 0.0 if z is None or (isinstance(z, float) and math.isnan(z)) else max(-1.0, min(1.0, z))


def morning_brief(now: datetime, ctxs: dict, frames: dict, extras: dict, h: dict) -> tuple[str, dict]:
    cues = extras.get("cues") or []
    lines = [f"MORNING BRIEF {now:%a %d %b %H:%M}"]
    if cues:
        lines.append("Global: " + ", ".join(f"{c['name']} {c['change_pct']:+.1f}%" for c in cues))
    if extras.get("fii"):
        now_r, week_r = extras["fii"]
        lines.append(f"FII index futures: {100 * now_r:.0f}% long"
                     + (f" ({100 * week_r:.0f}% a week ago)" if week_r is not None else ""))
    news = extras.get("news")
    if news:
        lines.append(f"News tone (word count, rough): {news['label']} - {news['positive']} up / "
                     f"{news['negative']} down in {news['headlines']} headlines")
    leans = {}
    for index, ctx in ctxs.items():
        frame = frames.get(index)
        gap = 100.0 * (ctx.open / ctx.prev_close - 1.0)
        move = ctx.sigma_day * ctx.open
        vix_now = float(frame["vix"].dropna().iloc[-1]) if frame is not None and "vix" in frame and \
            frame["vix"].notna().any() else None
        pcr = (ctx.options_raw or {}).get("pcr")
        label, score, parts = lean(_options_z(ctx, h), max(-1.0, min(1.0, ctx.macro_raw or 0.0)), _global_sign(cues))
        leans[index] = label
        ph, pl, pc = ctx.prev_day
        wh, wl, _ = ctx.prev_week
        events = ", ".join(getattr(e, "title", str(e)) for e in ctx.events) or "none"
        lines += ["", f"{index} open {ctx.open:,.0f} (gap {gap:+.2f}%)",
                  f"Expected range today: {ctx.open - move:,.0f} - {ctx.open + move:,.0f} (+/-{move:,.0f} pts; "
                  f"about 2 days in 3 close inside)",
                  "VIX " + (f"{vix_now:.1f} " if vix_now is not None else "") + f"(prev {ctx.vix_prev_close:.1f})"
                  + (f" | PCR {pcr:.2f}" if pcr is not None and not math.isnan(pcr) else ""),
                  f"Levels: prev day H {ph:,.0f} L {pl:,.0f} C {pc:,.0f} | prev week H {wh:,.0f} L {wl:,.0f}",
                  f"Expiry {ctx.expiry_1}{' (TODAY)' if ctx.is_expiry_day else ''} | Events: {events}",
                  f"Lean: {label} (score {score:+.1f}: " + ", ".join(f"{k} {v:+.1f}" for k, v in parts.items())
                  + ") - experimental, scored daily"]
    return "\n".join(lines), leans


STEP = {"NIFTY": 50, "SENSEX": 100}


def _premium(quotes, index, expiry, strike, kind, at, spot=None) -> float | None:
    try:
        return float(quotes.mid(index, expiry, strike, kind, at, spot=spot))
    except (KeyError, ValueError):
        return None


def _case(label, kind, index, ctx, quotes, at, last, target, stop) -> str:
    strike = round(last / STEP.get(index, 50)) * STEP.get(index, 50)
    reward, risk = abs(target - last), abs(stop - last)
    text = (f"{label} case: target {target:,.0f}, stop-loss {'above' if kind == 'PE' else 'below'} {stop:,.0f} "
            f"(reward/risk {reward / risk:.1f})" if risk else f"{label} case: target {target:,.0f}")
    now_p = _premium(quotes, index, ctx.expiry_1, strike, kind, at)
    at_t = _premium(quotes, index, ctx.expiry_1, strike, kind, at, spot=target)
    at_s = _premium(quotes, index, ctx.expiry_1, strike, kind, at, spot=stop)
    if None not in (now_p, at_t, at_s):
        text += (f"\n  {strike:.0f} {kind} (exp {ctx.expiry_1}): ~Rs {now_p:.0f} now, ~Rs {at_t:.0f} at target, "
                 f"~Rs {at_s:.0f} at stop")
    return text


def midday_update(now: datetime, ctxs: dict, frames: dict, quotes: dict, bias: dict, remaining: float) -> str:
    """12:15, the owner's old hold-or-exit moment.

    For each index: where it stands, how much of the expected range is used, and the afternoon's levels.
    - **Targets:** the expected-range edge, or one remaining move if price is already past it.
    - **Stop-losses:** today's high or low.
    - **Option prices:** the at-the-money nearest-expiry option now, at the target and at the stop.

    `bias` (desk, else the morning lean) picks the side shown; with none, both. `remaining` is the share of
    the day's variance still to come on the business clock. Levels come from the expected range, not a forecast;
    option prices are model estimates as if the index got there now."""
    lines = [f"MIDDAY {now:%H:%M} - where the day stands, and the levels for the afternoon"]
    for index, ctx in ctxs.items():
        f = frames.get(index)
        if f is None or f.empty:
            continue
        last, hi, lo = float(f["close"].iloc[-1]), float(f["high"].max()), float(f["low"].min())
        vwap = float(f["vwap"].iloc[-1]) if "vwap" in f and pd.notna(f["vwap"].iloc[-1]) else None
        exp_lo, exp_hi = ctx.open * (1 - ctx.sigma_day), ctx.open * (1 + ctx.sigma_day)
        used = (hi - lo) / (exp_hi - exp_lo) if exp_hi > exp_lo else float("nan")
        left = last * ctx.sigma_day * math.sqrt(max(remaining, 0.0))
        at = f["ts"].iloc[-1] + timedelta(minutes=1)              # priced off the latest bar
        lines += ["", f"{index} {last:,.0f} ({100 * (last / ctx.open - 1):+.2f}% from open {ctx.open:,.0f}); "
                      f"today {lo:,.0f} - {hi:,.0f}"
                  + (f"; VWAP {vwap:,.0f}, price {'above' if last > vwap else 'below'}" if vwap else ""),
                  f"Expected range {exp_lo:,.0f} - {exp_hi:,.0f}: {100 * used:.0f}% used, about +/-{left:,.0f} pts "
                  "left today"]
        side = bias.get(index)
        view = {"down": "DOWN", "up": "UP"}.get(side)
        lines.append(f"Morning view: {view}" if view else "No clear morning view: both sides")
        if side in (None, "down"):
            lines.append(_case("DOWN", "PE", index, ctx, quotes[index], at, last, min(exp_lo, last - left), hi))
        if side in (None, "up"):
            lines.append(_case("UP", "CE", index, ctx, quotes[index], at, last, max(exp_hi, last + left), lo))
    lines += ["", "Levels from today's expected range; option prices are model estimates. Your call, not advice."]
    return "\n".join(lines)


def _ideas(journal, start: date, end: date) -> pd.DataFrame:
    return journal._query(
        "select a.id, a.at, a.idx, p.entry_at, p.exit_at, p.pnl, p.reason from alerts a "
        "left join paper_trades p on p.alert_id = a.id where a.mode = 'idea' and substr(a.at, 1, 10) between ? and ?",
        (start.isoformat(), end.isoformat()))


def _money(x: float) -> str:
    return f"Rs {x:+,.0f}"


def day_summary(day: date, ctxs: dict, closes: dict, journal, leans: dict) -> str:
    """`closes`: index -> (open, last close). Each lean is scored here and kept for the Friday scorecard."""
    lines = [f"DAY SUMMARY {day:%a %d %b}"]
    for index, (opened, closed) in closes.items():
        ctx = ctxs[index]
        move = closed / opened - 1.0
        inside = "inside" if abs(move) <= ctx.sigma_day else "outside"
        text = f"{index} {opened:,.0f} -> {closed:,.0f} ({100 * move:+.2f}%), {inside} the expected " \
               f"+/-{100 * ctx.sigma_day:.2f}% range"
        call = leans.get(index) or journal.get_state(f"lean_{day}_{index}")
        if call in ("UP", "DOWN"):
            right = (call == "UP") == (move > 0)
            journal.set_state(f"lean_result_{day}_{index}", "right" if right else "wrong")
            text += f"; lean {call}: {'right' if right else 'wrong'}"
        elif call:
            text += "; lean FLAT (not scored)"
        lines.append(text)
    desk = journal.get_state(f"desk_bias_{day}")
    if desk in ("up", "down") and "NIFTY" in closes:
        opened, closed = closes["NIFTY"]
        right = (desk == "up") == (closed > opened)
        journal.set_state(f"desk_result_{day}", "right" if right else "wrong")
        lines.append(f"Desk bias {desk.upper()}: {'right' if right else 'wrong'} (Nifty open to close)")
    ideas = _ideas(journal, day, day)
    done = ideas.dropna(subset=["exit_at"])
    still = ideas[ideas["entry_at"].notna() & ideas["exit_at"].isna()]
    n = len(ideas)
    lines.append(f"Ideas today: {n} idea{'s' if n != 1 else ''}"
                 + (f", closed {_money(done['pnl'].sum())} per lot" if len(done) else "")
                 + f"; {len(still)} still open")
    return "\n".join(lines)


def score_missed(journal, daily: dict, today: date) -> int:
    """Score any desk bias or morning lean the day summary never scored (a crashed or late run), from the official
    daily open and close once the nightly rebuild has them. Returns the number of calls scored."""
    calls = journal._query("select key, value from state where key like 'desk_bias_%' or key like 'lean_%'")
    scored = 0
    for key, value in zip(calls["key"], calls["value"]):
        if key.startswith("lean_result_"):
            continue
        if key.startswith("desk_bias_"):
            day, index, result_key = key[len("desk_bias_"):], "NIFTY", "desk_result_" + key[len("desk_bias_"):]
        else:
            day, index = key[len("lean_"):].split("_", 1)
            result_key = f"lean_result_{day}_{index}"
        call = (value or "").lower()
        if call not in ("up", "down") or journal.get_state(result_key) or date.fromisoformat(day) >= today:
            continue
        rows = daily.get(index)
        if rows is None or date.fromisoformat(day) not in rows.index:
            continue
        opened, closed = float(rows.loc[date.fromisoformat(day), "open"]), float(rows.loc[date.fromisoformat(day), "close"])
        journal.set_state(result_key, "right" if (call == "up") == (closed > opened) else "wrong")
        scored += 1
    return scored


def scorecard(journal, day: date) -> str:
    start = day - timedelta(days=day.weekday())
    ideas = _ideas(journal, start, day)
    done = ideas.dropna(subset=["exit_at"])
    wins, losses = done[done["pnl"] > 0], done[done["pnl"] <= 0]
    hits = int((done["reason"] == "target").sum())
    lines = [f"WEEKLY SCORECARD {start:%d %b} - {day:%d %b}",
             f"Ideas: {len(ideas)} ideas, {int(ideas['entry_at'].notna().sum())} filled, {hits} hit target, "
             f"{len(losses)} closed at a loss; net {_money(done['pnl'].sum())} per lot"
             + (f" (avg win {_money(wins['pnl'].mean())}" if len(wins) else " (no wins")
             + (f", avg loss {_money(losses['pnl'].mean())})" if len(losses) else ", no losses)")]
    right = scored = 0
    d = start
    while d <= day:
        for index in ("NIFTY", "SENSEX"):
            result = journal.get_state(f"lean_result_{d}_{index}")
            if result:
                scored += 1
                right += result == "right"
        d += timedelta(days=1)
    lines.append(f"Morning lean right: {right} of {scored} scored days" if scored else "Morning lean: no days scored")
    desk = [journal.get_state(f"desk_result_{start + timedelta(days=k)}") for k in range((day - start).days + 1)]
    desk = [r for r in desk if r]
    if desk:
        lines.append(f"Desk bias right: {desk.count('right')} of {len(desk)}")
    lines.append("Paper only: each idea is one lot at the alert's plan, after charges.")
    return "\n".join(lines)


def brief_extras(store, derived, day: date) -> dict:
    """Global cues from the morning macro pull, FII positioning, and headlines since yesterday's 15:30."""
    raws = [store.read("macro_daily", day - timedelta(days=k)) for k in range(7)]
    raws = [r for r in raws if len(r)]
    cues = []
    if raws:
        rows = pd.concat(raws, ignore_index=True)
        rows["date"] = pd.to_datetime(rows["date"]).dt.date
        cues = global_cues(rows[rows["date"] < day])
    fii = None
    try:
        r = derived.read("fii_ratio", columns="day, ratio").sort_values("day")
        if len(r):
            fii = (float(r["ratio"].iloc[-1]), float(r["ratio"].iloc[-6]) if len(r) >= 6 else None)
    except Exception:  # noqa: BLE001 - no table yet
        pass
    titles = []
    since = pd.Timestamp(datetime.combine(day - timedelta(days=1), datetime.min.time())).tz_localize("Asia/Kolkata") \
        + pd.Timedelta(hours=15, minutes=30)                     # since the previous session's close
    for d in (day - timedelta(days=1), day):
        n = store.read("news", d)
        if len(n):
            n = n[~n["price_restatement"].fillna(False).astype(bool)] if "price_restatement" in n else n
            if "first_seen" in n:
                seen = pd.to_datetime(n["first_seen"], utc=True, errors="coerce").dt.tz_convert("Asia/Kolkata")
                n = n[seen >= since]
            titles += [str(t) for t in n["title"].dropna()]
    return {"cues": cues, "fii": fii, "news": news_sentiment(sorted(set(titles)))}
