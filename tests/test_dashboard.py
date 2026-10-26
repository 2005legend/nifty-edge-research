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


def test_an_exit_without_a_pnl_is_costed_by_the_server(client):
    from quantdesk.costs import round_trip

    c, j = client
    a = j.add_alert(alert(at=AT))
    real = c.post(f"/api/alerts/{a}/fill", json={"premium": 60.0}).json()["real_trade_id"]
    assert c.get("/api/today").json()["real"][0]["id"] == real
    assert c.post(f"/api/real/{real}/exit", json={"premium": 70.0, "notes": "took the exit message"}).status_code == 200
    expected = 10.0 * 65 - round_trip(60.0, 70.0, 65, exchange="NSE", day=DAY).total
    assert j.real_trades().loc[0, "pnl"] == pytest.approx(expected)


def test_each_lock_comes_with_the_period_an_unlock_needs(client):
    c, j = client
    a = j.add_alert(alert(at=AT))
    p = j.open_paper(a, AT, 60.0)
    j.close_paper(p, AT.replace(hour=11), 54.0, "stop", -420.0)
    today = c.get("/api/today").json()
    assert set(today["locks"]) == {"per_day", "day_loss"}
    assert today["lock_periods"] == {"per_day": "2026-10-22", "day_loss": "2026-10-22"}


def test_your_own_trade_is_logged_with_its_pnl_after_charges(client):
    """26 Oct 2026: the owner bought NIFTY 22600 PE (27 Oct) at 81, 2 lots, and sold at 105, on the desk's DOWN bias."""
    from quantdesk.costs import round_trip

    c, j = client
    body = {"index": "NIFTY", "strike": 22600, "kind": "PE", "expiry": "2026-10-27", "qty": 130,
            "entry_at": "2026-10-26T10:30:00+05:30", "entry_premium": 81.0,
            "exit_at": "2026-10-26T11:20:00+05:30", "exit_premium": 105.0, "source": "desk", "notes": "bias DOWN"}
    r = c.post("/api/own-trade", json=body)
    expected = 24.0 * 130 - round_trip(81.0, 105.0, 130, exchange="NSE", day=DAY).total
    assert r.status_code == 200 and r.json()["pnl"] == pytest.approx(expected)
    stats = c.get("/api/journal").json()["own"]
    assert stats["n"] == 1 and stats["net"] == pytest.approx(expected) and stats["by_source"]["desk"]["n"] == 1
    assert c.post("/api/own-trade", json={**body, "source": "hunch"}).status_code == 422


def test_mode_shows_the_kill_switch_and_unlock_lifts_it(client):
    c, j = client
    j.set_state("verdict_mode", "live")
    assert c.get("/api/today").json()["mode"] == "live"
    j.set_state("kill_switch", "sprt")
    assert c.get("/api/today").json()["mode"] == "shadow"
    r = c.post("/api/unlock", json={"lock": "kill_switch", "period": "2026-10-22", "reason": "reviewed the trades"})
    assert r.status_code == 200 and j.get_state("kill_switch") == "" and c.get("/api/today").json()["mode"] == "live"
