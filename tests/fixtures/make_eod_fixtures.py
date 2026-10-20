"""Regenerates synthetic NSE/BSE end-of-day fixtures (UDiFF bhavcopy, participant OI, FII/DII).

Run: .venv/Scripts/python tests/fixtures/make_eod_fixtures.py
"""

import io
import json
import zipfile
from pathlib import Path

HERE = Path(__file__).parent

UDIFF_HEADER = ("TradDt,BizDt,Sgmt,Src,FinInstrmTp,FinInstrmId,ISIN,TckrSymb,SctySrs,XpryDt,"
                "FininstrmActlXpryDt,StrkPric,OptnTp,FinInstrmNm,OpnPric,HghPric,LwPric,ClsPric,LastPric,"
                "PrvsClsgPric,UndrlygPric,SttlmPric,OpnIntrst,ChngInOpnIntrst,TtlTradgVol,TtlTrfVal,"
                "TtlNbOfTxsExctd,SsnId,NewBrdLotQty,Rmks,Rsvd1,Rsvd2,Rsvd3,Rsvd4")


def udiff_row(symbol, tp, expiry, strike, opt, close, settle, oi, chg, vol, und, src="NSE"):
    return (f"2026-10-19,2026-10-19,FO,{src},{tp},123,,{symbol},,{expiry},{expiry},{strike},{opt},"
            f"{symbol}-{expiry}-{strike}-{opt},{close},{close + 5},{close - 5},{close},{close},{close},"
            f"{und},{settle},{oi},{chg},{vol},1000000,500,F1,65,,,,,")


nse_rows = [
    udiff_row("NIFTY", "IDO", "2026-10-20", "22550.00", "CE", 120.0, 120.5, 150000, 2000, 900000, 22560.1),
    udiff_row("NIFTY", "IDO", "2026-10-20", "22550.00", "PE", 110.0, 109.5, 160000, -1000, 800000, 22560.1),
    udiff_row("NIFTY", "IDF", "2026-10-27", "", "", 22600.0, 22601.0, 12000000, 50000, 70000, 22560.1),
    udiff_row("RELIANCE", "STO", "2026-10-27", "2800.00", "CE", 30.0, 30.5, 9000, 100, 500, 2790.0),
]
nse_csv = (UDIFF_HEADER + "\n" + "\n".join(nse_rows) + "\n").encode()
buffer = io.BytesIO()
with zipfile.ZipFile(buffer, "w") as zf:
    zf.writestr("BhavCopy_NSE_FO_0_0_0_20261019_F_0000.csv", nse_csv)
(HERE / "nse_fo_udiff_sample.zip").write_bytes(buffer.getvalue())

bse_rows = [
    udiff_row("SENSEX", "IDO", "2026-10-22", "73400.00", "CE", 300.0, 301.0, 50000, 500, 200000, 73420.0, "BSE"),
    udiff_row("SENSEX", "IDO", "2026-10-22", "73400.00", "PE", 280.0, 279.0, 52000, 700, 210000, 73420.0, "BSE"),
]
(HERE / "bse_fo_udiff_sample.csv").write_bytes((UDIFF_HEADER + "\n" + "\n".join(bse_rows) + "\n").encode())

(HERE / "nse_block_page.html").write_bytes(
    b"\r\n<!DOCTYPE html><html><head><title>Access Denied</title></head><body>Access Denied</body></html>")

participant = (
    '"Participant wise Open Interest (no. of contracts) in Equity Derivatives as on Oct 19, 2026"\n'
    "Client Type,Future Index Long,Future Index Short,Future Stock Long,Future Stock Short\t,"
    "Option Index Call Long,Option Index Put Long,Option Index Call Short,Option Index Put Short,"
    "Option Stock Call Long,Option Stock Put Long,Option Stock Call Short,Option Stock Put Short,"
    "Total Long Contracts\t,Total Short Contracts\t\n"
    "Client,250000,180000,1,1,1,1,1,1,1,1,1,1,1,1\n"
    "DII,60000,40000,1,1,1,1,1,1,1,1,1,1,1,1\n"
    "FII,120000,280000,1,1,1,1,1,1,1,1,1,1,1,1\n"
    "Pro,70000,100000,1,1,1,1,1,1,1,1,1,1,1,1\n"
    "TOTAL,500000,600000,4,4,4,4,4,4,4,4,4,4,4,4\n"
)
(HERE / "fao_participant_oi_sample.csv").write_bytes(participant.encode())

fiidii = [
    {"category": "DII **", "date": "19-Oct-2026", "buyValue": "20493.12", "sellValue": "15311.40", "netValue": "5181.72"},
    {"category": "FII/FPI *", "date": "19-Oct-2026", "buyValue": "15675.30", "sellValue": "20374.55", "netValue": "-4699.25"},
]
(HERE / "fiidii_sample.json").write_text(json.dumps(fiidii), encoding="utf-8")

(HERE / "ind_nifty50list_sample.csv").write_bytes(
    b"Company Name,Industry,Symbol,Series,ISIN Code\n"
    b"Reliance Industries Ltd.,Oil Gas & Consumable Fuels,RELIANCE,EQ,INE002A01018\n"
    b"HDFC Bank Ltd.,Financial Services,HDFCBANK,EQ,INE040A01034\n")
print("fixtures written")
