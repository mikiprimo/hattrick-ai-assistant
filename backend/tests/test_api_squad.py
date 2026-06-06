from datetime import datetime
from app.models.player import Player
from app.models.player_skill_history import PlayerSkillHistory


def _player(id: int, first: str = "Test", last: str = "Player") -> Player:
    return Player(
        id=id, first_name=first, last_name=last, age=25, age_days=100,
        tsi=4200, form=7, stamina=8, injury_days=-1, salary=7800,
        goalkeeper=5, defending=6, playmaking=8, winger=4,
        passing=7, scoring=9, set_pieces=3,
    )


def _snap(player_id: int, date: datetime) -> PlayerSkillHistory:
    return PlayerSkillHistory(
        player_id=player_id, snapshot_date=date, source="HRF",
        form=7, stamina=8, speed=5, goalkeeper=5, defending=6,
        playmaking=8, winger=4, passing=7, scoring=9, set_pieces=3,
        leadership=5, experience=5, loyalty=7,
    )


D1 = datetime(2026, 5, 13)
D2 = datetime(2026, 5, 20)


def test_get_squad_empty(client):
    response = client.get("/api/squad")
    assert response.status_code == 200
    assert response.json() == []


def test_get_squad_demo_fallback_no_snapshots(client, db):
    # Without snapshots, returns all players (demo mode)
    db.add(_player(9000001, "Demo", "Player"))
    db.commit()
    data = client.get("/api/squad").json()
    assert len(data) == 1
    assert data[0]["id"] == 9000001


def test_get_squad_shows_only_latest_snapshot_players(client, db):
    # Current player: has snapshot at D2 (latest)
    db.add(_player(1000001, "John", "Doe"))
    db.add(_snap(1000001, D2))
    # Former player: only has older snapshot
    db.add(_player(1000002, "Former", "Player"))
    db.add(_snap(1000002, D1))
    db.commit()

    data = client.get("/api/squad").json()
    assert len(data) == 1
    assert data[0]["id"] == 1000001


def test_get_squad_excludes_demo_players_when_snapshots_exist(client, db):
    # Demo player (no snapshot)
    db.add(_player(9000001, "Demo", "Player"))
    # Real player with snapshot
    db.add(_player(1000001, "Real", "Player"))
    db.add(_snap(1000001, D2))
    db.commit()

    data = client.get("/api/squad").json()
    assert len(data) == 1
    assert data[0]["id"] == 1000001


def test_get_squad_returns_all_current_players(client, db):
    db.add(_player(1000001, "John", "Doe"))
    db.add(_player(1000002, "Jane", "Smith"))
    db.add(_snap(1000001, D2))
    db.add(_snap(1000002, D2))
    db.commit()

    data = client.get("/api/squad").json()
    assert len(data) == 2
    ids = {p["id"] for p in data}
    assert ids == {1000001, 1000002}
