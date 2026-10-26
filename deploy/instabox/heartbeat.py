"""InstaBox pilot heartbeat: does the machine keep running when nobody is attached?

Writes the time to heartbeat.log every minute and serves "ok" on port 8080 (the URL a free web-cron service
can ping to wake or keep the machine awake). Standard library only.

    nohup python3 heartbeat.py > /dev/null 2>&1 &     # start it, then disconnect
    python3 heartbeat.py --report                     # later: every pause longer than 2 minutes
"""

import sys
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

LOG = Path(__file__).with_name("heartbeat.log")
PORT = 8080


def gaps(lines: list[str], max_gap_s: float = 120) -> list[tuple[str, str, float]]:
    """(before, after, minutes) for every pause between consecutive timestamps longer than `max_gap_s`."""
    stamps = []
    for line in lines:
        try:
            stamps.append(datetime.fromisoformat(line.strip()))
        except ValueError:
            continue
    out = []
    for a, b in zip(stamps, stamps[1:]):
        if (b - a).total_seconds() > max_gap_s:
            out.append((a.isoformat(), b.isoformat(), round((b - a).total_seconds() / 60, 1)))
    return out


class Ok(BaseHTTPRequestHandler):
    def do_GET(self):
        body = f"ok {datetime.now().isoformat(timespec='seconds')}\n".encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def beat() -> None:
    while True:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(datetime.now().isoformat(timespec="seconds") + "\n")
        time.sleep(60)


if __name__ == "__main__":
    if "--report" in sys.argv:
        lines = LOG.read_text(encoding="utf-8").splitlines() if LOG.exists() else []
        found = gaps(lines)
        print(f"{len(lines)} beats from {lines[0] if lines else '-'} to {lines[-1] if lines else '-'}")
        print("no pauses longer than 2 minutes" if not found else
              "\n".join(f"paused {m} min: {a} -> {b}" for a, b, m in found))
    else:
        threading.Thread(target=beat, daemon=True).start()
        HTTPServer(("0.0.0.0", PORT), Ok).serve_forever()
