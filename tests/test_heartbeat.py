import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "heartbeat", Path(__file__).parents[1] / "deploy" / "instabox" / "heartbeat.py")
heartbeat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(heartbeat)


def test_gaps_name_every_pause_longer_than_the_limit():
    lines = ["2026-10-27T09:00:00", "2026-10-27T09:01:00", "2026-10-27T09:02:00",
             "2026-10-27T09:40:00", "2026-10-27T09:41:00", "not a time", "2026-10-27T10:00:30"]
    found = heartbeat.gaps(lines, max_gap_s=120)
    assert found == [("2026-10-27T09:02:00", "2026-10-27T09:40:00", 38.0),
                     ("2026-10-27T09:41:00", "2026-10-27T10:00:30", 19.5)]
    assert heartbeat.gaps(lines[:3], max_gap_s=120) == []
