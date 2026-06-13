from pathlib import Path
from app.models.player import Player

FIXTURES = Path(__file__).parent / "fixtures"

PLAYERS_XML = """<?xml version="1.0" encoding="utf-8"?>
<HattrickData>
  <Team>
    <TeamID>999</TeamID>
    <TeamName>Avversario FC</TeamName>
    <PlayerList>
      <Player>
        <PlayerID>1</PlayerID><FirstName>A</FirstName><LastName>B</LastName>
        <PlayerForm>7</PlayerForm><StaminaSkill>8</StaminaSkill><InjuryLevel>-1</InjuryLevel>
        <KeeperSkill>5</KeeperSkill><DefenderSkill>6</DefenderSkill>
        <PlaymakerSkill>7</PlaymakerSkill><ScorerSkill>6</ScorerSkill>
        <PassingSkill>6</PassingSkill><WingerSkill>6</WingerSkill><SetPiecesSkill>5</SetPiecesSkill>
      </Player>
    </PlayerList>
  </Team>
</HattrickData>"""


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
# Analyze endpoint — new interface
# ---------------------------------------------------------------------------

def test_analyze_returns_complete_structure(client, db):
    _add_squad(db)
    players_xml = (FIXTURES / "players_sesto_san_juan.xml").read_text()
    r = client.post("/api/pre-partita/analyze", json={
        "players_xml": players_xml,
        "matches_xml": "",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["opponent"]["team_name"] == "Sesto San Juan"
    all_formations = {"4-4-2","3-5-2","4-3-3","3-4-3","5-4-1","4-5-1","5-3-2","5-2-3","5-5-0","2-5-3"}
    assert data["opponent"]["best_formation"] in all_formations
    assert set(data["opponent"]["line_ratings"]) == {"goalkeeper", "defense", "midfield", "attack"}
    assert data["opponent"]["recent_results"] == []
    assert data["my_team"]["best_formation"] in all_formations
    assert set(data["my_team"]["lineup"]) == {"goalkeeper", "defense", "midfield", "attack"}
    assert "tactic_ranking" in data
    assert "attitude" in data
    assert isinstance(data["explanation"], str) and len(data["explanation"]) > 10


def test_analyze_with_spirit_and_confidence(client, db):
    _add_squad(db)
    resp = client.post("/api/pre-partita/analyze", json={
        "players_xml": PLAYERS_XML,
        "matches_xml": "",
        "match_type": "league",
        "spirit": 12,
        "confidence": 10,
        "formation_xp": {"4-4-2": 14},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "tactic_ranking" in data
    assert len(data["tactic_ranking"]) == 7
    assert "attitude" in data
    assert data["attitude"]["attitude"] in ("normal", "mots", "cool")
    assert "my_team" in data
    assert "opponent" in data


def test_analyze_missing_players_xml(client):
    resp = client.post("/api/pre-partita/analyze", json={
        "players_xml": "",
        "match_type": "league",
        "spirit": 10,
        "confidence": 10,
        "formation_xp": {},
    })
    assert resp.status_code == 422


def test_analyze_with_matches_xml_returns_recent_results(client, db):
    _add_squad(db)
    players_xml = (FIXTURES / "players_sesto_san_juan.xml").read_text()
    matches_xml = (FIXTURES / "matches_sesto_san_juan.xml").read_text()
    r = client.post("/api/pre-partita/analyze", json={
        "players_xml": players_xml,
        "matches_xml": matches_xml,
    })
    assert r.status_code == 200
    results = r.json()["opponent"]["recent_results"]
    assert len(results) == 4
    assert results[0]["result"] in ("W", "D", "L")
    assert "goals_for" in results[0]


def test_analyze_malformed_players_xml_returns_422(client, db):
    _add_squad(db)
    r = client.post("/api/pre-partita/analyze", json={
        "players_xml": "<invalid",
        "matches_xml": "",
    })
    assert r.status_code == 422
    assert "players_xml" in r.json()["detail"].lower()


def test_analyze_malformed_matches_xml_returns_422(client, db):
    _add_squad(db)
    players_xml = (FIXTURES / "players_sesto_san_juan.xml").read_text()
    r = client.post("/api/pre-partita/analyze", json={
        "players_xml": players_xml,
        "matches_xml": "<invalid",
    })
    assert r.status_code == 422
    assert "matches_xml" in r.json()["detail"].lower()


def test_analyze_tactic_ranking_has_seven_entries(client, db):
    _add_squad(db)
    players_xml = (FIXTURES / "players_sesto_san_juan.xml").read_text()
    r = client.post("/api/pre-partita/analyze", json={"players_xml": players_xml, "matches_xml": ""})
    assert r.status_code == 200
    assert len(r.json()["tactic_ranking"]) == 7


def test_analyze_attitude_is_valid(client, db):
    _add_squad(db)
    players_xml = (FIXTURES / "players_sesto_san_juan.xml").read_text()
    r = client.post("/api/pre-partita/analyze", json={"players_xml": players_xml, "matches_xml": ""})
    assert r.json()["attitude"]["attitude"] in ("normal", "mots", "cool")


# ---------------------------------------------------------------------------
# Save and History endpoints
# ---------------------------------------------------------------------------

def test_save_and_history(client, db):
    _add_squad(db)
    resp = client.post("/api/pre-partita/analyze", json={
        "players_xml": PLAYERS_XML,
        "match_type": "league",
        "spirit": 10,
        "confidence": 10,
        "formation_xp": {},
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
