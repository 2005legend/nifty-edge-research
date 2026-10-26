"""DayLoader: one index's day as the pipeline sees it at 09:16, plus its per-minute frame (design §4, §10 step 1).

Everything comes from `data/derived`, and nothing dated after the moment of use reaches a decision:
- the open is the first minute bar's open (known at 09:16), not the daily table's (stamped 16:00)
- the prior close, the expiries, the FII ratio and the option chain are the previous session's
- the HAR forecast uses fits on earlier rows only (`vol/har.py`)
- every z reference is built from earlier sessions only (R10)

Signal-dependent features (distance to VWAP and room to the nearest level, both in stop-distances) exist only
when a signal fires. Their z reference is therefore the previous signals pooled across check times, key
(feature, "*"). Breadth is scored against the same check time in earlier sessions, and the option inputs
against earlier days, key (feature, "day"). Ruling R40, docs/decisions.md.
"""

import math
import warnings
from bisect import bisect_left
from datetime import date, datetime, time, timedelta

import numpy as np
import pandas as pd

from quantdesk.analysis.bands import MINUTES
from quantdesk.analysis.frame import build_minute_frame
from quantdesk.analysis.hurdles import cusum_alarms, shock_days
from quantdesk.analysis.macro import event_delta, hard_exit, macro_raw, stress_delta, stress_score
from quantdesk.analysis.options_implied import options_raw
from quantdesk.clock import IST
from quantdesk.derived.store import DerivedStore
from quantdesk.pricing import black76_vec
from quantdesk.pricing.clock import Clock
from quantdesk.pricing.quotes import sessions_left
from quantdesk.pricing.surface import Surface, sigma_bt
from quantdesk.strategy.timeline import check_times
from quantdesk.strategy.types import DayContext, ZRef
from quantdesk.validation.hypotheses import param
from quantdesk.vol.har import har_series

STEP = {"NIFTY": 50, "SENSEX": 100}
ROUND = {"NIFTY": 50, "SENSEX": 100}
BREADTH_FEATURES = ("adv_share", "above_share", "top5_ret")
SIGNAL_FEATURES = ("loc_vwap", "loc_level")
OPTION_FEATURES = ("pcr", "rr25")
REFERENCE = time(9, 45)
CLOSE = time(15, 30)


class DayLoader:
    def __init__(self, derived: DerivedStore, clock: Clock, surface: Surface, h: dict, events: list,
                 shock_h: float | None = None):
        self.derived, self.clock, self.surface, self.h = derived, clock, surface, h
        self.events = events
        sessions = derived.read("sessions").sort_values("day")
        self.days = list(sessions["day"])
        self.kind = dict(zip(sessions["day"], sessions["kind"]))
        self.daily = {t: g.set_index("day").sort_index() for t, g in derived.read("daily").groupby("target")}
        self.expiries = derived.read("expiries").set_index(["symbol", "day"]).sort_index()
        self.fii = derived.read("fii_ratio").set_index("day")["ratio"].sort_index()
        self.macro = derived.read("macro")
        self.shock_h = shock_h
        self._years: dict[int, dict] = {}
        self._har: dict[str, pd.DataFrame] = {}
        self._moves: dict[str, pd.DataFrame] = {}
        self._shock: pd.Series | None = None
        self._ratio: dict[tuple, float] = {}
        self._options: dict[tuple, dict | None] = {}
        self._breadth: dict[date, dict] = {}
        self._signals: list[tuple[date, str, float]] = []
        self._atm_changes: dict[tuple, np.ndarray] = {}

    # --- raw data, cached a year at a time -------------------------------------------------------------
    def _year(self, year: int) -> dict:
        if year not in self._years:
            bars = self.derived.read("minutes", where=f"year = {year} and target in ('NIFTY', 'SENSEX', 'INDIAVIX')",
                                     columns="target, ts, open, high, low, close, day")
            members = self.derived.read("members_minute",
                                        where=f"day >= DATE '{year}-01-01' and day <= DATE '{year}-12-31'") \
                if self.derived.exists("members_minute") else pd.DataFrame(columns=["day", "ts"])
            self._years = {year: {"bars": {k: g.sort_values("ts") for k, g in bars.groupby(["target", "day"])},
                                  "members": {k: g.sort_values("ts") for k, g in members.groupby("day")}}}
        return self._years[year]

    def bars(self, target: str, day: date) -> pd.DataFrame:
        return self._year(day.year)["bars"].get((target, day), pd.DataFrame(columns=["ts", "open", "high", "low", "close"]))

    def members(self, day: date) -> pd.DataFrame:
        return self._year(day.year)["members"].get(day, pd.DataFrame(columns=["ts", "tv"]))

    def previous(self, day: date) -> date | None:
        i = bisect_left(self.days, day)
        return self.days[i - 1] if i > 0 else None

    # --- volatility ------------------------------------------------------------------------------------
    def har(self, index: str) -> pd.DataFrame:
        if index not in self._har:
            daily = self.daily[index].reset_index()[["day", "open", "high", "low", "close"]]
            vix = self.daily["INDIAVIX"].reset_index()[["day", "close"]]
            h = self.h
            self._har[index] = har_series(daily, vix, param(h, "vol.har_window_days"), param(h, "har.overnight_c"),
                                          param(h, "vol.har_percentile_window"), param(h, "har.percentile_min"))
        return self._har[index]

    def _moves_matrix(self, index: str) -> pd.DataFrame:
        if index not in self._moves:
            rows = self.derived.read("minutes", where=f"target = '{index}'", columns="day, ts, close")
            stamp = pd.to_datetime(rows["ts"]).dt.tz_convert(IST)
            rows["slot"] = (stamp.dt.hour * 60 + stamp.dt.minute - (9 * 60 + 15)).to_numpy()
            closes = rows.pivot_table(index="day", columns="slot", values="close", aggfunc="last")
            closes = closes.reindex(columns=range(MINUTES))
            opens = self.daily[index]["open"].reindex(closes.index)
            self._moves[index] = (closes.div(opens, axis=0) - 1.0).abs()
        return self._moves[index]

    def is_expiry_day(self, index: str, day: date) -> bool:
        key = (index, day)
        return bool(self.expiries.loc[key, "is_expiry_day"]) if key in self.expiries.index else False

    def band_sigma(self, index: str, day: date) -> np.ndarray:
        """Mean |close/open - 1| per slot over the previous 14 regular sessions of the same type (design §9)."""
        lookback = param(self.h, "h1.band_lookback_days")
        same = self.is_expiry_day(index, day)
        earlier = [d for d in self.days[:bisect_left(self.days, day)]
                   if self.kind[d] == "regular" and self.is_expiry_day(index, d) == same]
        moves = self._moves_matrix(index)
        rows = moves.reindex(earlier[-lookback:])
        if len(rows) < lookback:
            return np.full(MINUTES, np.nan)
        counts = rows.notna().sum(axis=0).to_numpy()
        return np.where(counts >= lookback, rows.mean(axis=0).to_numpy(), np.nan)

    def shock(self) -> pd.Series:
        if self._shock is None:
            nifty = self.daily["NIFTY"].reset_index()
            vix = self.daily["INDIAVIX"]["close"]
            har = self.har("NIFTY")
            sigma_gap = np.sqrt(self.clock.theta_night * har["rv_hat_nogap"])
            if self.shock_h is None:
                alarms = pd.Series(False, index=nifty["day"])
            else:
                returns = np.log(nifty.set_index("day")["close"]).diff()
                alarms = cusum_alarms(returns, param(self.h, "shock.cusum_sigma_window"), self.shock_h)
            self._shock = shock_days(nifty, vix, sigma_gap, alarms, param(self.h, "hurdle.shock_vix_log5"),
                                     param(self.h, "hurdle.shock_gap_sigma"))
        return self._shock

    def vix_at(self, day: date, at: time) -> float | None:
        bars = self.bars("INDIAVIX", day)
        stamp = datetime.combine(day, at, tzinfo=IST) - timedelta(minutes=1)
        hit = bars[bars["ts"] <= stamp]
        return float(hit["close"].iloc[-1]) if len(hit) else None

    def _rich_ratio(self, index: str, day: date) -> float | None:
        key = (index, day)
        if key not in self._ratio:
            vix = self.vix_at(day, REFERENCE)
            sigma = self.har(index)["sigma_day"].get(day, math.nan)
            ratio = None
            if vix is not None and sigma and not math.isnan(sigma) and self.kind.get(day) == "regular":
                try:
                    ratio = sigma_bt(vix, datetime.combine(day, REFERENCE, tzinfo=IST), self.clock) / sigma
                except ValueError:
                    ratio = None
            self._ratio[key] = ratio
        return self._ratio[key]

    def vol_rich_threshold(self, index: str, day: date) -> float | None:
        window, minimum = param(self.h, "gate.vol_rich_window_days"), param(self.h, "har.percentile_min")
        earlier = self.days[max(0, bisect_left(self.days, day) - window):bisect_left(self.days, day)]
        values = [r for d in earlier if (r := self._rich_ratio(index, d)) is not None]
        if len(values) < minimum:
            return None
        return float(np.quantile(values, param(self.h, "gate.vol_rich_percentile")))

    # --- family inputs --------------------------------------------------------------------------------
    def options_inputs(self, index: str, day: date) -> dict | None:
        key = (index, day)
        if key not in self._options:
            prev = self.previous(day)
            result = None
            if prev is not None and index in self.daily and prev in self.daily[index].index:
                eod = self.derived.read("options_eod", where=f"day = DATE '{prev}' and symbol = '{index}' "
                                                             f"and instrument = 'IDO'")
                expiries = sorted(eod["expiry"].unique()) if len(eod) else []
                result = options_raw(eod, {"prev_close": float(self.daily[index].loc[prev, "close"]),
                                           "step": STEP[index], "at": datetime.combine(prev, CLOSE, tzinfo=IST),
                                           "expiries": expiries}, self.clock,
                                     {"strike_steps": param(self.h, "options_score.strike_steps"),
                                      "rr_delta": param(self.h, "options_score.rr_delta")})
            self._options[key] = result
        return self._options[key]

    def breadth_at_checks(self, day: date) -> dict:
        """{(feature, "HH:MM"): value} at each check time's bar, for z references of later days."""
        if day not in self._breadth:
            members = self.members(day)
            out = {}
            if len(members) and "adv" in members:
                total = members["members_total"].replace(0, np.nan)
                frame = members.assign(adv_share=(members["adv"] - members["dec"]) / total,
                                       above_share=members["above_vwap"] / total).set_index("ts")
                for at in check_times(day, False, self.h):
                    seen = frame[frame.index <= at - timedelta(minutes=1)]
                    if len(seen):
                        last = seen.iloc[-1]
                        for f in BREADTH_FEATURES:
                            out[(f, at.strftime("%H:%M"))] = float(last[f])
            self._breadth[day] = out
        return self._breadth[day]

    def record_signal(self, day: date, raw: dict) -> None:
        """Signal-dependent features of a signal on `day`; usable as a z reference from the next session on."""
        for name in SIGNAL_FEATURES:
            if name in raw and raw[name] is not None and not math.isnan(raw[name]):
                self._signals.append((day, name, float(raw[name])))

    def z_refs(self, index: str, day: date) -> dict:
        window = param(self.h, "meta.zscore_window_sessions")
        earlier = [d for d in self.days[:bisect_left(self.days, day)] if self.kind[d] == "regular"][-window:]
        refs: dict = {}
        collected: dict = {}
        for d in earlier:
            for key, value in self.breadth_at_checks(d).items():
                if value is not None and not math.isnan(value):    # one gap must not make a year's mean NaN
                    collected.setdefault(key, []).append(value)
            raw = self.options_inputs(index, d)
            if raw:
                for f in OPTION_FEATURES:
                    if not math.isnan(raw.get(f, math.nan)):
                        collected.setdefault((f, "day"), []).append(raw[f])
        signals = [(d, n, v) for d, n, v in self._signals if d < day][-window * len(SIGNAL_FEATURES):]
        for name in SIGNAL_FEATURES:
            values = [v for _, n, v in signals if n == name][-window:]
            if values:
                collected[(name, "*")] = values
        for key, values in collected.items():
            arr = np.asarray(values, dtype=float)
            refs[key] = ZRef(float(arr.mean()), float(arr.std(ddof=1)) if len(arr) > 1 else 0.0, int(len(arr)))
        return refs

    # --- the day card ---------------------------------------------------------------------------------
    def day_context(self, index: str, day: date, with_refs: bool = True, z_refs: bool = True) -> DayContext:
        h = self.h
        prev = self.previous(day)
        daily = self.daily[index]
        bars = self.bars(index, day)
        open_ = float(bars["open"].iloc[0]) if len(bars) else math.nan
        prev_row = daily.loc[prev] if prev is not None and prev in daily.index else None
        prev_close = float(prev_row["close"]) if prev_row is not None else math.nan
        prev_day = tuple(float(prev_row[c]) for c in ("high", "low", "close")) if prev_row is not None else (math.nan,) * 3
        monday = day - timedelta(days=day.weekday())
        week = daily[(daily.index >= monday - timedelta(days=7)) & (daily.index < monday)]
        prev_week = ((float(week["high"].max()), float(week["low"].min()), float(week["close"].iloc[-1]))
                     if len(week) else (math.nan,) * 3)
        key = (index, day)
        exp = self.expiries.loc[key] if key in self.expiries.index else None
        expiry_1 = exp["expiry_1"] if exp is not None else None
        expiry_2 = exp["expiry_2"] if exp is not None and pd.notna(exp["expiry_2"]) else None
        is_expiry = bool(exp["is_expiry_day"]) if exp is not None else False
        dte_1 = sessions_left(self.clock, day, expiry_1) if expiry_1 is not None else -1
        har = self.har(index)
        row = har.loc[day] if day in har.index else None
        sigma_day = float(row["sigma_day"]) if row is not None else math.nan
        sigma_gap = math.sqrt(self.clock.theta_night * float(row["rv_hat_nogap"])) if row is not None else math.nan
        pct = float(row["har_pct"]) if row is not None and not math.isnan(row["har_pct"]) else None
        vix_prev = float(self.daily["INDIAVIX"].loc[prev, "close"]) \
            if prev is not None and prev in self.daily["INDIAVIX"].index else math.nan
        events = tuple(e for e in self.events if e.date == day)
        known_macro = self.macro[self.macro["available_at"] <= datetime.combine(day, time(9, 5), tzinfo=IST)]
        shock = self.shock()
        delta_parts = {"event": event_delta(events, h),
                       "shock": param(h, "hurdle.shock_delta") if self._shock_on(shock, day) else 0.0,
                       "stress": stress_delta(stress_score(known_macro, day), True, h),
                       "slow_trend": 0.0, "gamma": 0.0}
        holiday_before = prev is not None and any((prev + timedelta(days=k)).weekday() < 5
                                                  for k in range(1, (day - prev).days))
        r_on = math.log(open_ / prev_close) if prev_close and not math.isnan(open_) else 0.0
        fii = self.fii[self.fii.index < day]
        return DayContext(
            index=index, day=day, session_kind=self.kind.get(day, "irregular"), open=open_, prev_close=prev_close,
            prev_day=prev_day, prev_week=prev_week, is_expiry_day=is_expiry, expiry_1=expiry_1, expiry_2=expiry_2,
            lot_1=int(exp["lot_1"]) if exp is not None and pd.notna(exp["lot_1"]) else 0,
            lot_2=int(exp["lot_2"]) if exp is not None and pd.notna(exp["lot_2"]) else None,
            dte_1=dte_1, sigma_day=sigma_day, sigma_gap=sigma_gap, har_pct=pct, vix_prev_close=vix_prev,
            band_sigma=self.band_sigma(index, day), events=events, delta_parts=delta_parts,
            options_raw=self.options_inputs(index, day),
            macro_raw=macro_raw(holiday_before, r_on, fii, param(h, "macro.fii_flip_window")),
            vol_rich_threshold=self.vol_rich_threshold(index, day) if with_refs else None,
            z_refs=self.z_refs(index, day) if with_refs and z_refs else {},
            hard_exit=hard_exit(day, is_expiry, events, h),
            spike_ref=self.spike_ref(index, day) if with_refs else None)

    def atm_changes(self, index: str, day: date) -> np.ndarray:
        """|1-minute change| of the modelled ATM premium per slot on `day` (the spike guard's raw input)."""
        key = (index, day)
        if key not in self._atm_changes:
            frame = self.minute_frame(self.day_context(index, day, with_refs=False))
            out = np.full(MINUTES, np.nan)
            stamp = pd.to_datetime(frame["ts"]).dt.tz_convert(IST)
            slots = (stamp.dt.hour * 60 + stamp.dt.minute - (9 * 60 + 15)).to_numpy()
            changes = frame["atm_premium"].diff().abs().to_numpy()
            keep = (slots >= 0) & (slots < MINUTES)
            out[slots[keep]] = changes[keep]
            self._atm_changes[key] = out
        return self._atm_changes[key]

    def spike_ref(self, index: str, day: date) -> np.ndarray | None:
        lookback = param(self.h, "gate.spike_lookback_days")
        earlier = [d for d in self.days[:bisect_left(self.days, day)] if self.kind[d] == "regular"][-lookback:]
        if len(earlier) < lookback:
            return None
        with warnings.catch_warnings():             # slot 0 has no previous minute: an all-NaN column is expected
            warnings.simplefilter("ignore", RuntimeWarning)
            return np.nanmedian(np.vstack([self.atm_changes(index, d) for d in earlier]), axis=0)

    @staticmethod
    def _shock_on(shock: pd.Series, day: date) -> bool:
        if day not in shock.index:
            return False
        i = list(shock.index).index(day)
        return bool(shock.iloc[max(0, i - 4):i + 1].any())

    def atm_premium_fn(self, ctx: DayContext):
        """Modelled ATM premium of the nearest weekly, for the spike guard (R21)."""
        if ctx.expiry_1 is None:
            return None
        expiry_close = datetime.combine(ctx.expiry_1, CLOSE, tzinfo=IST)
        step = ROUND[ctx.index]

        def premium(ts, close, vix):
            at = ts + timedelta(minutes=1)
            if at >= expiry_close:
                return math.nan
            strike = round(close / step) * step
            sigma = self.surface.sigma(at, expiry_close, close, [strike], vix, self.clock, max(ctx.dte_1, 0))[0]
            return float(black76_vec.price(close, strike, self.clock.bt(at, expiry_close), sigma, "call"))

        return premium

    def minute_frame(self, ctx: DayContext, with_atm: bool = True) -> pd.DataFrame:
        return build_minute_frame(self.bars(ctx.index, ctx.day), self.members(ctx.day),
                                  self.bars("INDIAVIX", ctx.day)[["ts", "close"]], ctx, self.h,
                                  self.atm_premium_fn(ctx) if with_atm else None)
