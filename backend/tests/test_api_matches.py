from datetime import datetime
import json
from app.models.match_snapshot import MatchSnapshot
from app.models.player import Player


def _snap(db, date=datetime(2026, 5, 20), season=82, matchround=5,
          position=2, points=10, played=4, gf=8, ga=3,
          lineup=None, ratings=None):
    s = MatchSnapshot(
        snapshot_date=date,
        season=season,
        matchround=matchround,
        league_position=position,
        league_points=points,
        league_played=played,
        league_goals_for=gf,
        league_goals_against=ga,
        lineup_json=json.dumps(lineup or {}),
        ratings_json=json.dumps(ratings or {}),
    )
    db.add(s)
    db.commit()
    return s


def test_match_snapshot_model(db):
    s = _snap(db)
    fetched = db.query(MatchSnapshot).first()
    assert fetched.season == 82
    assert fetched.matchround == 5
    assert fetched.league_position == 2
    assert fetched.league_points == 10


def test_get_matches_empty(client):
    r = client.get("/api/matches")
    assert r.status_code == 200
    assert r.json() == []


def test_get_matches_returns_league_data(client, db):
    _snap(db, position=2, points=10, played=4, gf=8, ga=3)
    data = client.get("/api/matches").json()
    assert len(data) == 1
    league = data[0]["league"]
    assert league["position"] == 2
    assert league["points"] == 10
    assert league["played"] == 4
    assert league["goals_for"] == 8
    assert league["goals_against"] == 3


def test_get_matches_lineup_enriched_with_player_name(client, db):
    db.add(Player(id=100001, first_name="Mario", last_name="Rossi"))
    db.commit()
    _snap(db, lineup={"keeper": 100001}, ratings={"100001": 7})
    data = client.get("/api/matches").json()
    lineup = data[0]["lineup"]
    assert len(lineup) == 1
    assert lineup[0]["name"] == "Mario Rossi"
    assert lineup[0]["rating"] == 7
    assert lineup[0]["line"] == "GK"
    assert lineup[0]["position"] == "Portiere"


def test_get_matches_unknown_player_shows_id(client, db):
    _snap(db, lineup={"keeper": 999999}, ratings={"999999": 5})
    data = client.get("/api/matches").json()
    assert data[0]["lineup"][0]["name"] == "#999999"


def test_get_matches_rating_zero_becomes_null(client, db):
    db.add(Player(id=100001, first_name="Mario", last_name="Rossi"))
    db.commit()
    _snap(db, lineup={"keeper": 100001}, ratings={"100001": 0})
    data = client.get("/api/matches").json()
    assert data[0]["lineup"][0]["rating"] is None


def test_get_matches_empty_positions_excluded(client, db):
    db.add(Player(id=100001, first_name="Mario", last_name="Rossi"))
    db.commit()
    # rightBack è 0 (posizione vuota) → non deve comparire nel lineup
    _snap(db, lineup={"keeper": 100001, "rightBack": 0}, ratings={"100001": 7})
    data = client.get("/api/matches").json()
    assert len(data[0]["lineup"]) == 1
    assert data[0]["lineup"][0]["position"] == "Portiere"


def test_get_matches_ordered_most_recent_first(client, db):
    _snap(db, date=datetime(2026, 5, 13), season=82, matchround=4, position=3, points=7,
          played=3, gf=5, ga=2)
    _snap(db, date=datetime(2026, 5, 20), season=82, matchround=5, position=2, points=10,
          played=4, gf=8, ga=3)
    data = client.get("/api/matches").json()
    assert data[0]["matchround"] == 5
    assert data[1]["matchround"] == 4


def test_get_matches_season_and_matchround(client, db):
    _snap(db, season=82, matchround=5)
    data = client.get("/api/matches").json()
    assert data[0]["season"] == 82
    assert data[0]["matchround"] == 5
    assert data[0]["snapshot_date"] == "2026-05-20"
