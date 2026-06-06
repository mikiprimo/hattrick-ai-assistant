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
    assert set(data["tactics"]) == {"pressing", "attack_direction", "set_pieces_taker", "attitude"}
    assert isinstance(data["explanation"], str) and len(data["explanation"]) > 10


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


def test_analyze_tactics_direction_is_valid(client, db):
    _add_squad(db)
    players_xml = (FIXTURES / "players_sesto_san_juan.xml").read_text()
    r = client.post("/api/pre-partita/analyze", json={"players_xml": players_xml, "matches_xml": ""})
    assert r.json()["tactics"]["attack_direction"] in ("center", "wings")


def test_analyze_set_pieces_taker_present(client, db):
    _add_squad(db)
    players_xml = (FIXTURES / "players_sesto_san_juan.xml").read_text()
    r = client.post("/api/pre-partita/analyze", json={"players_xml": players_xml, "matches_xml": ""})
    sp = r.json()["tactics"]["set_pieces_taker"]
    assert sp is not None
    assert "name" in sp
    assert "set_pieces" in sp
