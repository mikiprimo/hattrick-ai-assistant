import pytest
from tests.conftest import *  # noqa


def test_get_current_no_data(client):
    resp = client.get("/api/seasonal/current")
    assert resp.status_code == 200
    assert resp.json()["objective"] is None


def test_create_objective(client):
    resp = client.post("/api/seasonal", json={
        "season": 82,
        "league_position": 3,
        "league_points": 18,
        "league_series": "VII.935",
        "budget_manual": 500000,
        "strategy": "promote",
        "notes": "Anno buono",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["season"] == 82
    assert "recommendation" in data
    assert len(data["recommendation"]) > 0


def test_create_objective_invalid_strategy(client):
    resp = client.post("/api/seasonal", json={
        "season": 82,
        "strategy": "invalid",
    })
    assert resp.status_code == 422


def test_get_current_after_create(client):
    client.post("/api/seasonal", json={
        "season": 82,
        "league_position": 1,
        "league_points": 24,
        "league_series": "VI.12",
        "budget_manual": 800000,
        "strategy": "promote",
        "notes": "",
    })
    resp = client.get("/api/seasonal/current")
    assert resp.status_code == 200
    obj = resp.json()["objective"]
    assert obj is not None
    assert obj["season"] == 82


def test_history(client):
    client.post("/api/seasonal", json={"season": 80, "strategy": "maintain"})
    client.post("/api/seasonal", json={"season": 81, "strategy": "youth"})
    resp = client.get("/api/seasonal/history")
    assert resp.status_code == 200
    assert len(resp.json()["history"]) >= 2


def test_update_existing_season(client):
    client.post("/api/seasonal", json={"season": 82, "strategy": "maintain", "notes": "prima"})
    client.post("/api/seasonal", json={"season": 82, "strategy": "promote", "notes": "dopo"})
    resp = client.get("/api/seasonal/current")
    assert resp.json()["objective"]["strategy"] == "promote"
    assert resp.json()["objective"]["notes"] == "dopo"
    hist = client.get("/api/seasonal/history")
    seasons = [r["season"] for r in hist.json()["history"]]
    assert seasons.count(82) == 1  # non duplicato


# ---------------------------------------------------------------------------
# Task 4: /api/seasonal/status e /api/seasonal/analysis/*
# ---------------------------------------------------------------------------

from app.models.match_snapshot import MatchSnapshot
from app.models.player import Player
from app.models.rival_team import RivalTeam
from app.models.rival_player import RivalPlayer
from datetime import datetime


def _seed_snapshot(db, season=82, matchround=5, position=2, points=10, played=4):
    db.add(MatchSnapshot(
        snapshot_date=datetime(2026, 5, 21),
        season=season, matchround=matchround,
        league_position=position, league_points=points,
        league_played=played, league_goals_for=8,
        league_goals_against=3, league_series="VII.935",
        lineup_json="{}", ratings_json="{}",
    ))
    db.commit()


def _seed_players(db, n=11):
    for i in range(1, n + 1):
        db.add(Player(
            id=i, first_name=f"P{i}", last_name="X", age=25,
            goalkeeper=0 if i > 1 else 8,
            defending=7 if i < 6 else 0,
            playmaking=7 if 6 <= i <= 9 else 0,
            scoring=7 if i >= 10 else 0,
            winger=6 if i in (6, 9) else 0,
            passing=5, form=7, stamina=7,
            salary=50000, injury_days=-1,
        ))
    db.commit()


def test_seasonal_status_on_track(client, db):
    _seed_snapshot(db, position=2, points=10, played=4)
    from app.models.seasonal_objective import SeasonalObjective
    db.add(SeasonalObjective(
        season=82, league_position=2, league_points=10,
        league_series="VII.935", budget_manual=0,
        strategy="promote", notes="", recommendation="",
    ))
    db.commit()
    r = client.get("/api/seasonal/status")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] in ("on_track", "at_risk", "off_track")
    assert "projected_points" in data
    assert isinstance(data["history"], list)


def test_seasonal_status_no_data(client):
    r = client.get("/api/seasonal/status")
    assert r.status_code == 200
    assert r.json()["status"] == "on_track"


def test_analysis_maintain(client, db):
    _seed_players(db)
    r = client.get("/api/seasonal/analysis/maintain")
    assert r.status_code == 200
    data = r.json()
    assert "best_formation" in data
    assert "weakest_sector" in data


def test_analysis_youth(client, db):
    _seed_players(db)
    r = client.get("/api/seasonal/analysis/youth")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)


def test_analysis_promote_no_rivals(client, db):
    _seed_players(db)
    r = client.get("/api/seasonal/analysis/promote")
    assert r.status_code == 200
    assert r.json()["rival_avg"] is None


def test_analysis_promote_with_rivals(client, db):
    _seed_players(db)
    _seed_snapshot(db)
    db.add(RivalTeam(team_id=500, team_name="FC Forte",
                     league_series="VII.935", season=82,
                     updated_at=datetime.utcnow()))
    for i in range(11):
        db.add(RivalPlayer(
            team_id=500, player_id=2000 + i,
            first_name="R", last_name=str(i),
            goalkeeper=10 if i == 0 else 0,
            defending=10 if i < 5 else 0,
            playmaking=10 if 5 <= i <= 8 else 0,
            scoring=10 if i >= 9 else 0,
            winger=8, passing=8, form=7, stamina=7, injury_days=-1,
        ))
    db.commit()
    r = client.get("/api/seasonal/analysis/promote")
    assert r.status_code == 200
    data = r.json()
    assert data["rival_avg"] is not None
    assert len(data["needed_skills"]) > 0
