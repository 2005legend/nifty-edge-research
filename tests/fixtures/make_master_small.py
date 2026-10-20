"""Regenerates tests/fixtures/master_small.json: a synthetic Angel One instrument master.

Run: .venv/Scripts/python tests/fixtures/make_master_small.py
Strikes are stored x100 and tick sizes in paise, as in the real master.
NIFTY has a holiday-shifted Monday expiry (23NOV2026) for the Review Focus test.
"""

import json
from pathlib import Path

rows = []
token = 40000


def add(symbol, name, expiry, strike, lotsize, itype, exch, tick="5.000000"):
    global token
    token += 1
    rows.append({"token": str(token), "symbol": symbol, "name": name, "expiry": expiry,
                 "strike": f"{strike * 100:.6f}" if strike >= 0 else "-1.000000",
                 "lotsize": str(lotsize), "instrumenttype": itype, "exch_seg": exch,
                 "tick_size": tick})


rows += [
    {"token": "99926000", "symbol": "Nifty 50", "name": "NIFTY", "expiry": "", "strike": "-1.000000",
     "lotsize": "1", "instrumenttype": "AMXIDX", "exch_seg": "NSE", "tick_size": "-1.000000"},
    {"token": "99919000", "symbol": "SENSEX", "name": "SENSEX", "expiry": "", "strike": "-1.000000",
     "lotsize": "1", "instrumenttype": "AMXIDX", "exch_seg": "BSE", "tick_size": "-1.000000"},
    {"token": "99926017", "symbol": "India VIX", "name": "INDIA VIX", "expiry": "", "strike": "-1.000000",
     "lotsize": "1", "instrumenttype": "AMXIDX", "exch_seg": "NSE", "tick_size": "-1.000000"},
]

for expiry in ["20OCT2026", "27OCT2026"]:
    for strike in range(21550, 23551, 50):
        for side in ("CE", "PE"):
            add(f"NIFTY{expiry[:5]}{expiry[-2:]}{strike}{side}", "NIFTY", expiry, strike, 65, "OPTIDX", "NFO")
for expiry in ["23NOV2026", "01DEC2026"]:
    for strike in (22500, 22550, 22600):
        for side in ("CE", "PE"):
            add(f"NIFTY{expiry[:5]}{expiry[-2:]}{strike}{side}", "NIFTY", expiry, strike, 65, "OPTIDX", "NFO")
for expiry in ["22OCT2026", "29OCT2026"]:
    for strike in range(71400, 75401, 100):
        for side in ("CE", "PE"):
            add(f"SENSEX{expiry[:5]}{expiry[-2:]}{strike}{side}", "SENSEX", expiry, strike, 20, "OPTIDX", "BFO")

add("NIFTY27OCT26FUT", "NIFTY", "27OCT2026", -1, 65, "FUTIDX", "NFO", tick="10.000000")
add("NIFTY24NOV26FUT", "NIFTY", "24NOV2026", -1, 65, "FUTIDX", "NFO", tick="10.000000")
add("SENSEX29OCT26FUT", "SENSEX", "29OCT2026", -1, 20, "FUTIDX", "BFO", tick="5.000000")

for symbol, tok in [("RELIANCE-EQ", "2885"), ("HDFCBANK-EQ", "1333"), ("INFY-EQ", "1594")]:
    rows.append({"token": tok, "symbol": symbol, "name": symbol.split("-")[0], "expiry": "",
                 "strike": "-1.000000", "lotsize": "1", "instrumenttype": "", "exch_seg": "NSE",
                 "tick_size": "10.000000"})

Path(__file__).with_name("master_small.json").write_text(json.dumps(rows), encoding="utf-8")
print(len(rows), "rows")
