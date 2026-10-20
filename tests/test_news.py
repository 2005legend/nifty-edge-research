import io
import zipfile
from datetime import date, datetime
from pathlib import Path

import pytest

from quantdesk.clock import IST
from quantdesk.news.collect import SeenIndex, is_price_restatement, next_interval, poll_gdelt_once, poll_once
from quantdesk.storage import Store
from tests.fakes import FakeClock, FakeHttp

FIX = Path(__file__).parent / "fixtures"
RSS = (FIX / "rss_sample.xml").read_bytes()
NOW = datetime(2026, 10, 19, 10, 15, tzinfo=IST)
SCHEDULE = {"active": ["07:00", "19:30"], "active_every_minutes": 5, "idle_every_minutes": 60}


@pytest.mark.parametrize("title,expected", [
    ("Sensex tanks 800 points as banks drag", True),
    ("Nifty ends 1.2% higher", True),
    ("Bank Nifty slips 300 pts in late trade", True),
    ("RBI hikes repo rate by 25 bps", False),
    ("Infosys Q2 profit rises 8%", False),
])
def test_restatement_tagger(title, expected):
    assert is_price_restatement(title) is expected


def poll(store, seen, clock, routes):
    feeds = [{"name": name, "url": url} for name, url in [("a", "https://f/a"), ("b", "https://f/b")] if url in routes]
    http = FakeHttp(routes)
    return poll_once(feeds, http_get=http.get, store=store, clock=clock, seen=seen)


def test_first_seen_uses_poll_time_and_dedupes(tmp_path):
    store = Store(tmp_path)
    seen = SeenIndex(tmp_path / "state" / "news_seen.txt")
    clock = FakeClock(NOW)
    report1 = poll(store, seen, clock, {"https://f/a": (200, RSS)})
    clock.advance(300)
    report2 = poll(store, SeenIndex(tmp_path / "state" / "news_seen.txt"), clock, {"https://f/a": (200, RSS)})
    news = store.read("news")
    assert report1.new_items == {"a": 2}
    assert report2.new_items == {"a": 0}
    assert len(news) == 2
    assert set(news["first_seen"]) == {NOW}
    assert news[news["link"] == "https://example.com/news/1"].iloc[0]["pub_date"] == datetime(2026, 10, 19, 10, 0, tzinfo=IST)
    assert bool(news[news["link"] == "https://example.com/news/1"].iloc[0]["price_restatement"]) is True


def test_failing_feed_does_not_stop_others(tmp_path):
    store = Store(tmp_path)
    report = poll(store, SeenIndex(tmp_path / "s.txt"), FakeClock(NOW),
                  {"https://f/a": ConnectionError("down"), "https://f/b": (200, RSS)})
    assert report.failed == ["a"]
    assert report.new_items["b"] == 2


def test_stale_feed_flagged(tmp_path):
    later = FakeClock(datetime(2026, 10, 21, 10, 0, tzinfo=IST))
    report = poll(Store(tmp_path), SeenIndex(tmp_path / "s.txt"), later, {"https://f/a": (200, RSS)})
    assert report.stale == ["a"]


def rss(items_xml: str) -> bytes:
    return (f'<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>{items_xml}</channel></rss>').encode()


def test_naive_pubdate_parsed_as_ist(tmp_path):
    feed = rss("<item><title>NSE circular</title><link>https://n/1</link>"
               "<pubDate>20-Oct-2026 19:42:31</pubDate></item>")
    store = Store(tmp_path)
    poll(store, SeenIndex(tmp_path / "s.txt"), FakeClock(datetime(2026, 10, 20, 20, 0, tzinfo=IST)),
         {"https://f/a": (200, feed)})
    assert store.read("news").iloc[0]["pub_date"] == datetime(2026, 10, 20, 19, 42, 31, tzinfo=IST)


def test_feed_without_dates_not_marked_stale(tmp_path):
    feed = rss("<item><title>PIB release</title><link>https://p/1</link></item>")
    report = poll(Store(tmp_path), SeenIndex(tmp_path / "s.txt"), FakeClock(NOW), {"https://f/a": (200, feed)})
    assert report.stale == []
    assert report.new_items == {"a": 1}


def test_gdelt_missing_gkg_raises_clear_error(tmp_path):
    lastupdate = b"3 c http://data.gdeltproject.org/gdeltv2/20261019043000.gkg.csv.zip\n"
    http = FakeHttp({"https://g/last": (200, lastupdate)})
    with pytest.raises(ConnectionError, match="GKG"):
        poll_gdelt_once(http_get=http.get, store=Store(tmp_path), clock=FakeClock(NOW),
                        lastupdate_url="https://g/last", themes=["ECON_STOCKMARKET"])


def test_next_interval_follows_schedule():
    assert next_interval(NOW, lambda d: True, SCHEDULE) == 300
    assert next_interval(datetime(2026, 10, 19, 21, 0, tzinfo=IST), lambda d: True, SCHEDULE) == 3600
    assert next_interval(NOW, lambda d: False, SCHEDULE) == 3600


def gkg_zip():
    def row(record, url, themes, locations):
        cols = [""] * 27
        cols[0], cols[1], cols[3], cols[4], cols[7], cols[9] = record, "20261019043000", "example.com", url, themes, locations
        return "\t".join(cols)
    text = "\n".join([
        row("1", "https://in.example/rbi", "ECON_INTEREST_RATES;TAX_FNCACT", "1#India#IN#IN#20#77#IN"),
        row("2", "https://us.example/fed", "ECON_INTEREST_RATES", "1#United States#US#US#38#-97#US"),
        row("3", "https://in.example/cricket", "SPORTS", "1#India#IN#IN#20#77#IN"),
    ])
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("20261019043000.gkg.csv", text)
    return buffer.getvalue()


def test_gdelt_keeps_india_market_rows_only(tmp_path):
    lastupdate = (b"1 a http://data.gdeltproject.org/gdeltv2/20261019043000.export.CSV.zip\n"
                  b"2 b http://data.gdeltproject.org/gdeltv2/20261019043000.mentions.CSV.zip\n"
                  b"3 c http://data.gdeltproject.org/gdeltv2/20261019043000.gkg.csv.zip\n")
    http = FakeHttp({"https://data.gdeltproject.org/gdeltv2/lastupdate.txt": (200, lastupdate),
                     "http://data.gdeltproject.org/gdeltv2/20261019043000.gkg.csv.zip": (200, gkg_zip())})
    store = Store(tmp_path)
    kept = poll_gdelt_once(http_get=http.get, store=store, clock=FakeClock(NOW),
                           lastupdate_url="https://data.gdeltproject.org/gdeltv2/lastupdate.txt",
                           themes=["ECON_INTEREST_RATES", "ECON_STOCKMARKET"])
    assert kept == 1
    assert list(store.read("news_gdelt")["url"]) == ["https://in.example/rbi"]
