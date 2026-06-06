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
