from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient

from quantdesk.clock import IST
from quantdesk.live.dashboard import create_app
from quantdesk.live.journal import Journal
from quantdesk.validation.hypotheses import load_hypotheses
from tests.test_journal import alert

H = load_hypotheses()
DAY = date(2026, 10, 22)
AT = datetime(2026, 10, 22, 10, 0, tzinfo=IST)


@pytest.fixture
def client(tmp_path):
    j = Journal(tmp_path / "j.sqlite")
    research = tmp_path / "research"
    (research / "pilots").mkdir(parents=True)
    (research / "pilots" / "P1.md").write_text("# P1\n| eligible | 40 |\n")
    (research / "VERDICT.md").write_text("# SP2 verdict: **alert-off**\n")
    app = create_app(j, research, H, today=lambda: DAY, sessions=[DAY],
                     snapshot=lambda: {"day_card": {"NIFTY": "Trend: up"}, "frames": {}})
    return TestClient(app), j


def test_the_page_and_today_view(client):
    c, j = client
    assert c.get("/").status_code == 200 and "quantdesk" in c.get("/").text.lower()
    a = j.add_alert(alert(at=AT))
    today = c.get("/api/today").json()
    assert today["alerts"][0]["id"] == a and today["locks"] == [] and today["day_card"]["NIFTY"] == "Trend: up"


def test_took_skipped_and_fill_are_journalled(client):
    c, j = client
    a = j.add_alert(alert(at=AT))
    assert c.post(f"/api/alerts/{a}/status", json={"status": "took"}).status_code == 200
    assert c.post(f"/api/alerts/{a}/fill", json={"premium": 61.0}).status_code == 200
    assert j.alerts().loc[0, "status"] == "took" and j.real_trades().loc[0, "fill_premium"] == 61.0
    assert c.post(f"/api/alerts/{a}/status", json={"status": "maybe"}).status_code == 422


def test_unlock_needs_a_real_reason(client):
    c, j = client
    assert c.post("/api/unlock", json={"lock": "day_loss", "period": "2026-10-22", "reason": "ok"}).status_code == 422
    r = c.post("/api/unlock", json={"lock": "day_loss", "period": "2026-10-22", "reason": "bad tick, loss not real"})
    assert r.status_code == 200 and j.events().iloc[-1]["detail"].startswith("day_loss|2026-10-22|")


def test_journal_statistics(client):
    c, j = client
    for i, pnl in enumerate((400.0, -200.0, 600.0)):
        a = j.add_alert(alert(at=AT.replace(minute=i)))
        p = j.open_paper(a, AT.replace(minute=i), 60.0)
        j.close_paper(p, AT.replace(hour=11, minute=i), 66.0, "stop", pnl)
    stats = c.get("/api/journal").json()
    assert stats["paper"]["n"] == 3 and stats["paper"]["mean_r"] == pytest.approx(800 / 3 / 400)
    assert stats["paper"]["win_rate"] == pytest.approx(2 / 3) and len(stats["paper"]["equity"]) == 3


def test_research_lists_pilots_and_the_verdict(client):
    c, _ = client
    res = c.get("/api/research").json()
    assert "P1" in res["pilots"] and "alert-off" in res["verdict"]


def test_mode_shows_the_kill_switch_and_unlock_lifts_it(client):
    c, j = client
    j.set_state("verdict_mode", "live")
    assert c.get("/api/today").json()["mode"] == "live"
    j.set_state("kill_switch", "sprt")
    assert c.get("/api/today").json()["mode"] == "shadow"
    r = c.post("/api/unlock", json={"lock": "kill_switch", "period": "2026-10-22", "reason": "reviewed the trades"})
    assert r.status_code == 200 and j.get_state("kill_switch") == "" and c.get("/api/today").json()["mode"] == "live"
