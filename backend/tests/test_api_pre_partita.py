from pathlib import Path
from app.models.player import Player

FIXTURES = Path(__file__).parent / "fixtures"


def _add_squad(db):
    """11 giocatori sani per testare gli endpoint."""
    players = [
        Player(id=1, first_name="GK", last_name="One", goalkeeper=11, stamina=7, set_pieces=8),
        Player(id=2, first_name="D", last_name="Two", defending=13, stamina=7),
        Player(id=3, first_name="D", last_name="Three", defending=12, stamina=7),
        Player(id=4, first_name="D", last_name="Four", defending=11, stamina=7),
        Player(id=5, first_name="D", last_name="Five", defending=10, stamina=7),
        Player(id=6, first_name="M", last_name="Six", playmaking=14, stamina=7),
        Player(id=7, first_name="M", last_name="Seven", playmaking=12, stamina=7),
        Player(id=8, first_name="W", last_name="Eight", winger=12, stamina=7),
        Player(id=9, first_name="W", last_name="Nine", winger=10, stamina=7),
        Player(id=10, first_name="F", last_name="Ten", scoring=11, stamina=7),
        Player(id=11, first_name="F", last_name="Eleven", scoring=9, stamina=7),
    ]
    for p in players:
        db.add(p)
    db.commit()


# ---------------------------------------------------------------------------
# Squad endpoint tests
# ---------------------------------------------------------------------------

def test_get_squad_empty(client):
    r = client.get("/api/pre-partita/squad")
    assert r.status_code == 200
    assert r.json()["players"] == []


def test_get_squad_returns_players_with_skills(client, db):
    _add_squad(db)
    r = client.get("/api/pre-partita/squad")
    assert r.status_code == 200
    data = r.json()
    assert len(data["players"]) == 11
    p = data["players"][0]
    assert "name" in p
    assert "best_role" in p
    assert "role_rating" in p
    assert "skills" in p
    assert "form" in p
    assert "stamina" in p
    assert "injury_days" in p


# ---------------------------------------------------------------------------
# Tactic XP endpoints
# ---------------------------------------------------------------------------

def test_get_tactic_xp_empty(client):
    resp = client.get("/api/pre-partita/tactic-xp")
    assert resp.status_code == 200
    assert "tactic_xp" in resp.json()
    assert isinstance(resp.json()["tactic_xp"], dict)


def test_put_tactic_xp(client):
    resp = client.put("/api/pre-partita/tactic-xp", json={
        "tactic_name": "Pressing", "xp_level": 12,
    })
    assert resp.status_code == 200
    resp2 = client.get("/api/pre-partita/tactic-xp")
    assert resp2.json()["tactic_xp"]["Pressing"] == 12


def test_put_tactic_xp_invalid_name(client):
    resp = client.put("/api/pre-partita/tactic-xp", json={
        "tactic_name": "FakeRobotTactic", "xp_level": 5,
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Formation XP endpoints
# ---------------------------------------------------------------------------

def test_get_formation_xp_empty(client):
    resp = client.get("/api/pre-partita/formation-xp")
    assert resp.status_code == 200
    data = resp.json()
    assert "formation_xp" in data
    assert isinstance(data["formation_xp"], dict)


def test_put_formation_xp(client):
    resp = client.put("/api/pre-partita/formation-xp", json={"formation_name": "4-4-2", "xp_level": 15})
    assert resp.status_code == 200
    resp2 = client.get("/api/pre-partita/formation-xp")
    assert resp2.json()["formation_xp"]["4-4-2"] == 15


def test_put_formation_xp_invalid_name(client):
    resp = client.put("/api/pre-partita/formation-xp", json={"formation_name": "3-3-3", "xp_level": 10})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Save and History endpoints
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# NEW analyze endpoint tests (matchdetails-based)
# ---------------------------------------------------------------------------

def test_new_analyze_returns_complete_structure(client, db):
    _add_squad(db)
    xml1 = (FIXTURES / "matchdetails_tarallos_1.xml").read_text()
    r = client.post("/api/pre-partita/analyze", json={
        "matchdetails_xml_1": xml1,
        "is_home": False,
        "spirit": 10,
        "confidence": 10,
    })
    assert r.status_code == 200
    data = r.json()
    opp = data["opponent"]
    assert opp["team_name"] == "i tarallos"
    assert opp["team_id"] == 237132
    assert opp["typical_formation"] == "2-5-3"
    assert "chpp_ratings" in opp
    assert set(opp["chpp_ratings"].keys()) == {
        "midfield", "mid_def", "mid_att", "right_def", "left_def", "right_att", "left_att"
    }
    assert "recent_results" in opp
    assert len(opp["recent_results"]) == 1
    assert opp["recent_results"][0]["result"] == "W"
    my = data["my_team"]
    all_formations = {"4-4-2","3-5-2","4-3-3","3-4-3","5-4-1","4-5-1","5-3-2","5-2-3","5-5-0","2-5-3"}
    assert my["best_formation"] in all_formations
    assert "tactic_ranking" in data
    assert "tactic_recommendation" in data
    assert data["tactic_recommendation"]["recommended"] in [t["name"] for t in data["tactic_ranking"]]
    assert "sub_plan" in data
    assert "attitude_orders" in data
    assert "attitude" in data
    assert isinstance(data["explanation"], str) and len(data["explanation"]) > 10


def test_new_analyze_with_two_matchdetails(client, db):
    _add_squad(db)
    xml1 = (FIXTURES / "matchdetails_tarallos_1.xml").read_text()
    xml2 = (FIXTURES / "matchdetails_tarallos_2.xml").read_text()
    r = client.post("/api/pre-partita/analyze", json={
        "matchdetails_xml_1": xml1,
        "matchdetails_xml_2": xml2,
        "is_home": True,
    })
    assert r.status_code == 200
    results = r.json()["opponent"]["recent_results"]
    assert len(results) == 2
    assert results[0]["result"] in ("W", "D", "L")


def test_new_analyze_is_home_false_inflates_opp_ratings(client, db):
    _add_squad(db)
    xml1 = (FIXTURES / "matchdetails_tarallos_1.xml").read_text()
    r_home = client.post("/api/pre-partita/analyze", json={
        "matchdetails_xml_1": xml1, "is_home": True,
    })
    r_away = client.post("/api/pre-partita/analyze", json={
        "matchdetails_xml_1": xml1, "is_home": False,
    })
    assert r_home.status_code == r_away.status_code == 200
    home_mid = r_home.json()["opponent"]["chpp_ratings"]["mid_def"]
    away_mid = r_away.json()["opponent"]["chpp_ratings"]["mid_def"]
    assert away_mid > home_mid


def test_new_analyze_missing_matchdetails_returns_422(client):
    r = client.post("/api/pre-partita/analyze", json={
        "matchdetails_xml_1": "",
        "is_home": True,
    })
    assert r.status_code == 422
    assert "matchdetails_xml_1" in r.json()["detail"].lower()


def test_new_analyze_malformed_xml_returns_422(client, db):
    _add_squad(db)
    r = client.post("/api/pre-partita/analyze", json={
        "matchdetails_xml_1": "<invalid",
        "is_home": True,
    })
    assert r.status_code == 422
    assert "matchdetails_xml_1" in r.json()["detail"].lower()


def test_new_analyze_tactic_ranking_has_seven_entries(client, db):
    _add_squad(db)
    xml1 = (FIXTURES / "matchdetails_tarallos_1.xml").read_text()
    r = client.post("/api/pre-partita/analyze", json={
        "matchdetails_xml_1": xml1, "is_home": True,
    })
    assert r.status_code == 200
    assert len(r.json()["tactic_ranking"]) == 7


def test_new_save_and_history(client, db):
    _add_squad(db)
    xml1 = (FIXTURES / "matchdetails_tarallos_1.xml").read_text()
    resp = client.post("/api/pre-partita/analyze", json={
        "matchdetails_xml_1": xml1,
        "is_home": False,
        "spirit": 10,
        "confidence": 10,
    })
    assert resp.status_code == 200
    analysis = resp.json()

    save_resp = client.post("/api/pre-partita/save", json={
        "analysis": analysis,
        "my_spirit": 10,
        "my_confidence": 10,
        "my_attitude": analysis["attitude"]["attitude"],
        "match_type": "league",
    })
    assert save_resp.status_code == 200

    hist = client.get("/api/pre-partita/history")
    assert hist.status_code == 200
    assert len(hist.json()["history"]) >= 1
