"""Pilot 8 (spec §6.3): a sample of collected headlines for the owner to label blind, before any model
scores them. The owner fills `tone` (negative / neutral / positive, for the Indian index market) and
`market_moving` (yes / no)."""

from pathlib import Path

import pandas as pd

LABEL_COLUMNS = ["id", "feed", "published", "title", "summary", "tone", "market_moving", "notes"]


def sample_for_labelling(news: pd.DataFrame, n: int = 300, seed: int = 8) -> pd.DataFrame:
    """Round-robin across feeds (shuffled within each), so small feeds are never crowded out by the
    hundreds of NSE announcements. Price restatements and repeated titles are left out."""
    if news.empty:
        return pd.DataFrame(columns=LABEL_COLUMNS)
    pool = news[~news["price_restatement"].astype(bool)].copy()
    pool["_title"] = pool["title"].str.strip().str.lower()
    pool = pool.drop_duplicates("_title").sample(frac=1.0, random_state=seed)
    queues = {feed: list(group.index) for feed, group in sorted(pool.groupby("feed"))}
    picked: list = []
    while len(picked) < n and any(queues.values()):
        for feed in list(queues):
            if queues[feed] and len(picked) < n:
                picked.append(queues[feed].pop(0))
    chosen = pool.loc[picked]
    return pd.DataFrame({
        "id": chosen["item_id"].to_numpy(),
        "feed": chosen["feed"].to_numpy(),
        "published": chosen["pub_date"].astype(str).to_numpy(),
        "title": chosen["title"].str.strip().to_numpy(),
        "summary": chosen["summary"].fillna("").str.slice(0, 300).to_numpy(),
        "tone": "", "market_moving": "", "notes": "",
    })[LABEL_COLUMNS]


def write_label_sheet(sheet: pd.DataFrame, path: Path) -> Path:
    """UTF-8 with BOM so Excel shows rupee signs and Hindi correctly. Never overwrites: labels are work."""
    path = Path(path)
    if path.exists():
        raise FileExistsError(f"{path} already exists; it may hold your labels. Move it away to make a new one.")
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.to_csv(path, index=False, encoding="utf-8-sig")
    return path
