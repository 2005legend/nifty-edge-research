"""P1: how often each step lets a signal through, by year, VIX tercile and lot size (spec §6.3 pilot 1).

It counts outcomes and never profit, so it costs no trial. Its numbers decide the D2 checkpoint: fewer than
about 60 eligible setups a year, or a high-VIX stop-fit pass rate under half the low-VIX one, and the owner
chooses between ₹15k with a ₹600 stop and alert-off.
"""

import pandas as pd

NOT_SIGNALS = {"irregular_session", "not_a_check_time", "after_last_entry", "E3", "rbi_wait", "budget_wait",
               "no_signal", "warmup"}
BEFORE_STOP_FIT = {"event_shock"}


def pass_rates(records: pd.DataFrame) -> pd.DataFrame:
    rows = records[~records["failed"].isin(NOT_SIGNALS)].copy()
    if "year" not in rows:
        rows["year"] = [d.year for d in rows["day"]]
    failed = rows["failed"]
    rows["reached_stop_fit"] = ~failed.isin(BEFORE_STOP_FIT)
    rows["passed_stop_fit"] = ~failed.isin(BEFORE_STOP_FIT | {"stop_fit"})
    rows["reached_picker"] = failed.isna() | (failed == "no_strike")
    rows["is_eligible"] = failed.isna()
    out = rows.groupby(["year", "vix_tercile", "lot"]).agg(
        signals=("failed", "size"), stop_fit_reached=("reached_stop_fit", "sum"),
        stop_fit_pass=("passed_stop_fit", "sum"), picker_reached=("reached_picker", "sum"),
        eligible=("is_eligible", "sum")).reset_index()
    out["picker_pass"] = out["eligible"]
    out["stop_fit_rate"] = out["stop_fit_pass"] / out["stop_fit_reached"].where(out["stop_fit_reached"] > 0)
    out["picker_rate"] = out["picker_pass"] / out["picker_reached"].where(out["picker_reached"] > 0)
    return out
