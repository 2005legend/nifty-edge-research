"""Late-start catch-up: the morning's missed minutes from Angel's 1-minute candles, stored as recorded bars.

On 23 Oct 2026 Windows restarted at 08:54 and the recorder never ran; on 26 Oct the laptop slept until 10:08.
Without the morning bars the live engine would take the first recorded price as the day's open, and every noise
band and gap would be wrong for the rest of the day. Indices, VIX and the Nifty 50 stocks are fetched from the
open to the last complete minute before the live feed starts, so the two never overlap. Option quotes cannot be
fetched afterwards; for those minutes the model prices options instead.
"""

from datetime import datetime, timedelta

import pandas as pd

from quantdesk.recorder.bars import BAR_COLUMNS


def catch_up(client, store, day, targets: list[tuple[str, str]], open_t: datetime, now: datetime) -> int:
    """`targets`: (exchange, token). Returns the number of bars stored."""
    end = now.replace(second=0, microsecond=0)              # bars for minutes before this one are complete
    if end <= open_t + timedelta(minutes=1):
        return 0
    frames = []
    for exchange, token in targets:
        try:
            candles = client.candles(exchange, token, "ONE_MINUTE", open_t, end)
        except Exception:  # noqa: BLE001 - one missing token must not stop the recorder
            continue
        if candles is None or candles.empty:
            continue
        c = candles[(candles["ts"] >= open_t) & (candles["ts"] < end)]
        frames.append(pd.DataFrame({"minute": c["ts"], "token": str(token), "open": c["open"], "high": c["high"],
                                    "low": c["low"], "close": c["close"], "volume": c["volume"].astype("int64"),
                                    "n_ticks": 0, "atp": 0.0, "total_buy_qty": 0, "total_sell_qty": 0}))
    if not frames:
        return 0
    bars = pd.concat(frames, ignore_index=True)[BAR_COLUMNS]
    store.append_parquet("bars", day, bars)
    return len(bars)
