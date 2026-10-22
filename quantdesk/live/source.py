"""Today's market as the live engine sees it (SP3 design S3): history from the derived tables, today from the
recorder.

The day card is built by the same DayLoader the backtest uses. Three things for today exist only in the
recorder, and are added here:
- **the open:** the 09:15 bar's open, which also gives HAR its overnight-gap input
- **today in the session calendar**
- **today's expiries:** from the latest published chain

The minute frame uses the same `build_minute_frame` and `member_breadth`. Quotes are the recorder's real bid
and ask, with the model filling in where the planning maths needs a hypothetical market.
"""

import math
from bisect import bisect_left, insort
from dataclasses import replace
from datetime import date, datetime, time, timedelta

import numpy as np
import pandas as pd

from quantdesk.analysis.frame import build_minute_frame
from quantdesk.clock import IST
from quantdesk.derived.members import member_breadth
from quantdesk.pricing.quotes import ModelQuotes, Quote
from quantdesk.strategy.gates import Helpers
from quantdesk.validation.hypotheses import param

INDEX_TOKENS = {"NIFTY": "99926000", "SENSEX": "99919000"}
VIX_TOKEN = "99926017"


def recorder_bars(bars: pd.DataFrame, token: str) -> pd.DataFrame:
    rows = bars[bars["token"] == token].sort_values("minute")
    return rows.rename(columns={"minute": "ts"})[["ts", "open", "high", "low", "close"]].reset_index(drop=True)


class RecordedQuotes(ModelQuotes):
    """Real bid/ask from the recorder's minute snapshots; the model for planning scenarios and gaps."""

    def __init__(self, frames, surface, clock, h, snapshots: pd.DataFrame, meta: pd.DataFrame):
        super().__init__(frames, surface, clock, h)
        meta = meta.sort_values("subscribed_at").drop_duplicates("token", keep="last") if len(meta) else meta
        self._token = {(r.underlying, str(r.expiry)[:10], float(r.strike), r.side): r.token for r in meta.itertuples()}
        self._snap = snapshots.set_index(["token", "minute"]).sort_index() if len(snapshots) else None

    def quote(self, index, expiry, strike, kind, at):
        token = self._token.get((index, str(expiry)[:10], float(strike), kind))
        if token is not None and self._snap is not None:
            key = (token, at - timedelta(minutes=1))
            if key in self._snap.index:
                row = self._snap.loc[key]
                if isinstance(row, pd.DataFrame):
                    row = row.iloc[-1]
                bid, ask = float(row["bid"]), float(row["ask"])
                if bid > 0 and ask > 0:
                    return Quote(bid=bid, ask=ask, mid=(bid + ask) / 2.0)
        return super().quote(index, expiry, strike, kind, at)


class LiveDaySource:
    """A DaySource (backtest/dataset.py) for today: the derived history plus the recorder's day."""

    def __init__(self, loader, day: date, bars: pd.DataFrame, snapshots: pd.DataFrame, meta: pd.DataFrame,
                 token_symbol: dict[str, str], membership, h: dict):
        self.loader, self.day, self.h = loader, day, h
        self.bars, self.snapshots, self.meta = bars, snapshots, meta
        self.token_symbol, self.membership = token_symbol, membership
        if day not in loader.days:
            insort(loader.days, day)
        loader.kind[day] = "regular"
        for index, token in INDEX_TOKENS.items():
            today = recorder_bars(bars, token)
            if len(today) and index in loader.daily and day not in loader.daily[index].index:
                loader.daily[index].loc[day] = {"open": float(today["open"].iloc[0]), "high": np.nan, "low": np.nan,
                                                "close": np.nan}
        vix = recorder_bars(bars, VIX_TOKEN)
        if len(vix) and day not in loader.daily["INDIAVIX"].index:
            loader.daily["INDIAVIX"].loc[day] = {"open": float(vix["open"].iloc[0]), "high": np.nan, "low": np.nan,
                                                 "close": np.nan}
        for index in INDEX_TOKENS:
            loader.daily.get(index, pd.DataFrame()).sort_index(inplace=True)
        loader.daily["INDIAVIX"].sort_index(inplace=True)
        loader._har.clear()
        self._add_expiries()

    def _add_expiries(self) -> None:
        eod = self.loader.derived.read("options_eod", where=f"day < DATE '{self.day}' and instrument = 'IDO'",
                                       columns="day, symbol, expiry, lot")
        for symbol, rows in eod.groupby("symbol"):
            if (symbol, self.day) in self.loader.expiries.index:
                continue
            latest = rows[rows["day"] == rows["day"].max()]
            lots = latest.groupby("expiry")["lot"].agg(lambda s: int(s.mode().iloc[0]))
            ahead = sorted((e, l) for e, l in lots.items() if e >= self.day)
            if not ahead:
                continue
            second = ahead[1] if len(ahead) > 1 else (None, None)
            self.loader.expiries.loc[(symbol, self.day), ["expiry_1", "expiry_2", "lot_1", "lot_2", "is_expiry_day",
                                                          "available_at"]] = [
                ahead[0][0], second[0], ahead[0][1], second[1], ahead[0][0] == self.day,
                datetime.combine(self.day, time(9, 0), tzinfo=IST)]
        self.loader.expiries.sort_index(inplace=True)

    def context(self, index: str, day: date):
        ctx = self.loader.day_context(index, day)
        today = recorder_bars(self.bars, INDEX_TOKENS[index])
        return replace(ctx, open=float(today["open"].iloc[0])) if len(today) else ctx

    def _members(self) -> pd.DataFrame:
        stocks = self.bars[self.bars["token"].isin(self.token_symbol)].copy()
        if stocks.empty:
            return pd.DataFrame(columns=["ts", "tv"])
        stocks["target"] = stocks["token"].map(self.token_symbol)
        stocks = stocks.rename(columns={"minute": "ts"})
        members = {self.membership.listing(s) for s in self.membership.members_on(self.day)}
        prior = self.loader.derived.read("minutes", where=f"day = DATE '{self.loader.previous(self.day)}'",
                                         columns="target, high, low, close, volume")
        value = (((prior["high"] + prior["low"] + prior["close"]) / 3) * prior["volume"]).groupby(prior["target"]).sum()
        return member_breadth(stocks, members, value.to_dict(), param(self.h, "gate.breadth_top_n"))

    def frame(self, ctx) -> pd.DataFrame:
        vix = recorder_bars(self.bars, VIX_TOKEN)[["ts", "close"]]
        return build_minute_frame(recorder_bars(self.bars, INDEX_TOKENS[ctx.index]), self._members(), vix, ctx, self.h,
                                  self.loader.atm_premium_fn(ctx))

    def helpers(self, ctx, frame) -> Helpers:
        quotes = RecordedQuotes({ctx.index: frame}, self.loader.surface, self.loader.clock, self.h,
                                self.snapshots, self.meta)
        return Helpers(self.loader.clock, self.loader.surface, quotes)

    def record_signal(self, day, raw):
        self.loader.record_signal(day, raw)
