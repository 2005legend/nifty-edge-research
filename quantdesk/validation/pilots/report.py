"""Pilot reports: a short markdown table under research/pilots/, stamped with the data it was measured on."""

from datetime import datetime
from pathlib import Path

from quantdesk.clock import IST


def _fmt(value) -> str:
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def write_report(pilot_id: str, body: dict, path: Path, data_hash: str, notes: str = "") -> Path:
    lines = [f"# {pilot_id}", "", f"- data_hash `{data_hash}`, written {datetime.now(IST).isoformat(timespec='seconds')}",
             "", "| measure | value |", "|---|---|"]
    lines += [f"| {key} | {_fmt(value)} |" for key, value in body.items()]
    if notes:
        lines += ["", notes]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def frame_to_markdown(frame) -> str:
    """A pandas frame as a markdown table, without the optional `tabulate` dependency."""
    cols = list(frame.columns)
    rows = ["| " + " | ".join(str(c) for c in cols) + " |", "|" + "---|" * len(cols)]
    for values in frame.itertuples(index=False):
        rows.append("| " + " | ".join(_fmt(v) for v in values) + " |")
    return "\n".join(rows)
