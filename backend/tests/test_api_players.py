from datetime import datetime
from app.models.player import Player
from app.models.player_skill_history import PlayerSkillHistory
from app.api.players import PLAYER_DETAIL_FIELDS
from app.constants import SKILL_FIELDS as HISTORY_SKILL_FIELDS


def _make_player(id: int, **kwargs) -> Player:
    defaults = dict(
        first_name="Test", last_name="Player", age=25, age_days=100,
        tsi=4000, form=7, stamina=8, injury_days=-1, salary=10000,
        goalkeeper=3, defending=7, playmaking=9, winger=6,
        passing=8, scoring=10, set_pieces=4,
        speed=6, leadership=5, experience=6, loyalty=7,
        market_value=500000,
    )
    defaults.update(kwargs)
    return Player(id=id, **defaults)


def _make_snapshot(player_id: int, date: datetime, **overrides) -> PlayerSkillHistory:
    defaults = dict(
        source="HRF", form=6, stamina=7, speed=5,
        goalkeeper=3, defending=7, playmaking=8, winger=6,
        passing=8, scoring=10, set_pieces=4,
        leadership=5, experience=5, loyalty=7,
    )
    defaults.update(overrides)
    return PlayerSkillHistory(player_id=player_id, snapshot_date=date, **defaults)


def test_get_player_not_found(client):
    resp = client.get("/api/players/999")
    assert resp.status_code == 404


def test_get_player_returns_all_fields(client, db):
    db.add(_make_player(1))
    db.commit()
    resp = client.get("/api/players/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == 1
    assert data["first_name"] == "Test"
    assert set(data.keys()) == set(PLAYER_DETAIL_FIELDS)
    assert data["playmaking"] == 9
    assert data["speed"] == 6
    assert data["leadership"] == 5
    assert data["market_value"] == 500000
    assert data["data_source"] == "CHPP"
    assert data["speciality"] is None
    assert data["last_match_rating"] is None
    assert data["transfer_listed"] is False


def test_get_player_history_not_found(client):
    resp = client.get("/api/players/999/history")
    assert resp.status_code == 404


def test_get_player_history_empty(client, db):
    db.add(_make_player(2))
    db.commit()
    resp = client.get("/api/players/2/history")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_player_history_sorted_ascending(client, db):
    db.add(_make_player(3))
    db.add(_make_snapshot(3, datetime(2026, 5, 20), playmaking=9))
    db.add(_make_snapshot(3, datetime(2026, 5, 13), playmaking=8))
    db.commit()
    resp = client.get("/api/players/3/history")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["playmaking"] == 8
    assert data[1]["playmaking"] == 9
    assert set(data[0].keys()) == {"snapshot_date"} | set(HISTORY_SKILL_FIELDS)
    assert data[0]["snapshot_date"].startswith("2026-05-13")
    assert data[1]["snapshot_date"].startswith("2026-05-20")
