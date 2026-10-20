"""India news collector: RSS feeds and GDELT, timestamped by when *we* first saw each item.

Stored kinds: news (RSS items) and news_gdelt (India market-themed GDELT records).
Raw RSS XML is kept per poll under raw/news/<date>/.
"""

import hashlib
import io
import re
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, time, timezone
from pathlib import Path

import feedparser
import pandas as pd

from quantdesk.clock import IST
from quantdesk.storage import Store

_INDEX = re.compile(r"\b(sensex|nifty|bank\s*nifty|markets?|dalal\s+street)\b", re.I)
_NUMBER = re.compile(r"\d[\d,]*(\.\d+)?\s*(pts|points|%|per\s*cent)", re.I)
_VERB = re.compile(r"\b(tanks|jumps|surges|falls|slips|rises|gains|ends|closes|crashes|rallies|sheds|climbs|"
                   r"drops|plunges|soars|tumbles|settles)\b", re.I)
STALE_AFTER_S = 24 * 3600


def is_price_restatement(title: str) -> bool:
    """Headlines that only restate the index move (they carry no new information)."""
    return bool(_INDEX.search(title) and _NUMBER.search(title) and _VERB.search(title))


def _sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def _title_key(title: str) -> str:
    return _sha1(re.sub(r"\s+", " ", title.strip().lower()))


class SeenIndex:
    """Persistent set of item ids and title hashes already stored."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._seen = set(self.path.read_text(encoding="utf-8").split()) if self.path.exists() else set()

    def __contains__(self, key: str) -> bool:
        return key in self._seen

    def add(self, *keys: str) -> None:
        fresh = [k for k in keys if k not in self._seen]
        if not fresh:
            return
        self._seen.update(fresh)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write("\n".join(fresh) + "\n")


@dataclass
class PollReport:
    new_items: dict = field(default_factory=dict)
    failed: list = field(default_factory=list)
    stale: list = field(default_factory=list)


def _pub_date(entry):
    parsed = entry.get("published_parsed") or ("updated_parsed" in entry.keys() and entry["updated_parsed"])
    if parsed:
        return datetime(*parsed[:6], tzinfo=timezone.utc).astimezone(IST)
    raw = entry.get("published") or entry.get("updated")
    if not raw:
        return None
    try:  # Indian feeds (NSE, RBI) give local times without a timezone
        stamp = pd.to_datetime(raw, format="mixed", dayfirst=True)
    except (ValueError, TypeError):
        return None
    stamp = stamp.tz_localize(IST) if stamp.tzinfo is None else stamp.tz_convert(IST)
    return stamp.to_pydatetime()


def poll_once(feeds: list[dict], *, http_get, store: Store, clock, seen: SeenIndex) -> PollReport:
    report = PollReport()
    now = clock.now()
    rows = []
    for feed in feeds:
        name = feed["name"]
        try:
            response = http_get(feed["url"])
            if response.status_code != 200:
                raise ConnectionError(f"HTTP {response.status_code}")
            content = response.content
        except Exception:  # noqa: BLE001 - one bad feed never stops the others
            report.failed.append(name)
            continue
        store.write_raw("news", now.date(), f"{name}-{now:%H%M%S%f}.xml", content)
        parsed = feedparser.parse(content)
        count, newest = 0, None
        for entry in parsed.entries:
            link = entry.get("link", "")
            title = entry.get("title", "").strip()
            pub = _pub_date(entry)
            if pub and (newest is None or pub > newest):
                newest = pub
            item_id, title_hash = _sha1(link or title), _title_key(title)
            if item_id in seen or title_hash in seen:
                continue
            seen.add(item_id, title_hash)
            rows.append({"item_id": item_id, "title_hash": title_hash, "feed": name, "title": title,
                         "link": link, "summary": entry.get("summary", "")[:2000], "pub_date": pub,
                         "first_seen": now, "price_restatement": is_price_restatement(title)})
            count += 1
        report.new_items[name] = count
        # A feed with no entries is stale; one without parseable dates can't be judged by date.
        if not parsed.entries or (newest is not None and (now - newest).total_seconds() > STALE_AFTER_S):
            report.stale.append(name)
    if rows:
        frame = pd.DataFrame(rows)
        frame["pub_date"] = pd.to_datetime(frame["pub_date"])
        store.append_parquet("news", now.date(), frame)
    return report


def poll_gdelt_once(*, http_get, store: Store, clock, lastupdate_url: str, themes: list[str]) -> int:
    """Keep GKG records located in India whose themes match `themes`. Returns rows kept."""
    listing = http_get(lastupdate_url).content.decode("utf-8", errors="replace").split()
    gkg_url = next(token for token in listing if token.endswith(".gkg.csv.zip"))
    response = http_get(gkg_url)
    if response.status_code != 200 or response.content[:2] != b"PK":
        raise ConnectionError(f"GDELT GKG file unavailable (HTTP {response.status_code}): {gkg_url}")
    data = response.content
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        text = zf.read(zf.namelist()[0]).decode("utf-8", errors="replace")
    wanted = set(themes)
    now = clock.now()
    rows = []
    for line in text.splitlines():
        cols = line.split("\t")
        if len(cols) < 10:
            continue
        record_themes = set(cols[7].split(";")) | {t.split(",")[0] for t in cols[8].split(";") if t}
        if "#IN#" not in cols[9] or not (record_themes & wanted):
            continue
        rows.append({"record_id": cols[0], "date": datetime.strptime(cols[1], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc),
                     "source": cols[3], "url": cols[4], "themes": cols[7][:1000], "first_seen": now})
    if rows:
        store.append_parquet("news_gdelt", now.date(), pd.DataFrame(rows))
    return len(rows)


def next_interval(now: datetime, is_trading_day, schedule: dict) -> int:
    start, end = (time.fromisoformat(t) for t in schedule["active"])
    active = is_trading_day(now.date()) and start <= now.time() < end
    minutes = schedule["active_every_minutes"] if active else schedule["idle_every_minutes"]
    return int(minutes * 60)


def run_news_loop(*, poll, clock, sleep, is_trading_day, schedule: dict, max_cycles: int | None = None) -> None:
    cycles = 0
    while max_cycles is None or cycles < max_cycles:
        poll()
        cycles += 1
        sleep(next_interval(clock.now(), is_trading_day, schedule))
