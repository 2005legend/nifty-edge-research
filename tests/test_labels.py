from datetime import datetime

import pandas as pd
import pytest

from quantdesk.clock import IST
from quantdesk.news.labels import LABEL_COLUMNS, sample_for_labelling, write_label_sheet

T = datetime(2026, 10, 21, 10, 0, tzinfo=IST)


def news(rows):
    return pd.DataFrame([{"item_id": f"id{i}", "feed": feed, "title": title, "summary": f"summary {i}",
                          "pub_date": T, "first_seen": T, "price_restatement": restated}
                         for i, (feed, title, restated) in enumerate(rows)])


def test_sample_spreads_across_feeds_before_filling_from_the_largest():
    rows = [("nse_announcements", f"NSE {i}", False) for i in range(50)]
    rows += [("rbi_press", "RBI policy", False), ("mint_markets", "Mint story", False)]
    sample = sample_for_labelling(news(rows), n=10, seed=1)
    assert len(sample) == 10
    assert {"rbi_press", "mint_markets"} <= set(sample["feed"])  # small feeds are never crowded out
    assert list(sample.columns) == LABEL_COLUMNS
    assert sample["tone"].eq("").all() and sample["market_moving"].eq("").all()


def test_sample_skips_price_restatements_and_repeated_titles():
    rows = [("et_markets", "Sensex tanks 800 points", True), ("et_markets", "RBI holds rate", False),
            ("mint_markets", "RBI holds rate", False), ("bs_markets", "Budget date set", False)]
    sample = sample_for_labelling(news(rows), n=10, seed=1)
    assert sorted(sample["title"]) == ["Budget date set", "RBI holds rate"]


def test_sample_is_repeatable_with_the_same_seed():
    rows = [("nse_announcements", f"NSE {i}", False) for i in range(40)]
    a = sample_for_labelling(news(rows), n=5, seed=7)
    b = sample_for_labelling(news(rows), n=5, seed=7)
    assert list(a["id"]) == list(b["id"])


def test_write_label_sheet_never_overwrites_started_labels(tmp_path):
    sheet = sample_for_labelling(news([("rbi_press", "RBI policy", False)]), n=5, seed=1)
    path = tmp_path / "labels" / "pilot8_headlines.csv"
    write_label_sheet(sheet, path)
    assert path.read_bytes().startswith(b"\xef\xbb\xbf")  # BOM so Excel opens UTF-8 correctly
    with pytest.raises(FileExistsError):
        write_label_sheet(sheet, path)
