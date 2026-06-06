from datetime import datetime
from app.models.player import Player
from app.models.player_skill_history import PlayerSkillHistory


def _p(id: int, first: str = "Test", last: str = "Player", age: int = 24) -> Player:
    return Player(
        id=id, first_name=first, last_name=last, age=age, age_days=0,
        salary=8000, form=7, stamina=8, goalkeeper=3, defending=7,
        playmaking=9, winger=6, passing=8, scoring=10, set_pieces=4,
    )


def _snap(player_id: int, date: datetime, **skills) -> PlayerSkillHistory:
    defaults = dict(
        source="HRF", form=6, stamina=7, speed=5,
        goalkeeper=3, defending=7, playmaking=8, winger=6,
        passing=8, scoring=10, set_pieces=4,
        leadership=5, experience=5, loyalty=7,
    )
    defaults.update(skills)
    return PlayerSkillHistory(player_id=player_id, snapshot_date=date, **defaults)


D1 = datetime(2026, 5, 13)
D2 = datetime(2026, 5, 20)
D3 = datetime(2026, 5, 27)


def test_training_no_history_returns_empty_sessions(client):
    resp = client.get("/api/training")
    assert resp.status_code == 200
    assert resp.json() == {"sessions": []}


def test_training_one_snapshot_per_player_returns_empty(client, db):
    db.add(_p(1))
    db.add(_snap(1, D1))
    db.commit()
    resp = client.get("/api/training")
    assert resp.json() == {"sessions": []}


def test_training_two_dates_one_changed_player(client, db):
    db.add(_p(1, "Mario", "Rossi", age=22))
    db.add(_snap(1, D1, defending=7))
    db.add(_snap(1, D2, defending=8))
    db.commit()

    resp = client.get("/api/training")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["sessions"]) == 1

    session = data["sessions"][0]
    assert session["synced_at"].startswith("2026-05-20")
    assert session["previous_sync"].startswith("2026-05-13")
    assert session["unchanged_count"] == 0
    assert len(session["changed_players"]) == 1

    player = session["changed_players"][0]
    assert player["player_id"] == 1
    assert player["first_name"] == "Mario"
    assert player["last_name"] == "Rossi"
    assert player["age"] == 22
    assert player["deltas"]["defending"] == 1
    assert player["deltas"]["playmaking"] == 0


def test_training_unchanged_player_counted(client, db):
    db.add(_p(1, "Mario", "Rossi"))
    db.add(_p(2, "Luca", "Bianchi"))
    db.add(_snap(1, D1, defending=7))
    db.add(_snap(1, D2, defending=8))  # changed
    db.add(_snap(2, D1, defending=5))
    db.add(_snap(2, D2, defending=5))  # unchanged
    db.commit()

    data = client.get("/api/training").json()
    session = data["sessions"][0]
    assert len(session["changed_players"]) == 1
    assert session["changed_players"][0]["player_id"] == 1
    assert session["unchanged_count"] == 1


def test_training_previous_and_current_values(client, db):
    db.add(_p(1))
    db.add(_snap(1, D1, defending=7, playmaking=8))
    db.add(_snap(1, D2, defending=8, playmaking=9))
    db.commit()

    data = client.get("/api/training").json()
    player = data["sessions"][0]["changed_players"][0]
    assert player["previous_values"]["defending"] == 7
    assert player["current_values"]["defending"] == 8
    assert player["previous_values"]["playmaking"] == 8
    assert player["current_values"]["playmaking"] == 9
    # unchanged skills not in previous_values/current_values
    assert "goalkeeper" not in player["previous_values"]
    assert "goalkeeper" not in player["current_values"]


def test_training_three_dates_two_sessions(client, db):
    db.add(_p(1))
    db.add(_snap(1, D1, defending=6))
    db.add(_snap(1, D2, defending=7))
    db.add(_snap(1, D3, defending=8))
    db.commit()

    data = client.get("/api/training").json()
    assert len(data["sessions"]) == 2
    # most recent first
    assert data["sessions"][0]["synced_at"].startswith("2026-05-27")
    assert data["sessions"][1]["synced_at"].startswith("2026-05-20")


def test_training_sessions_most_recent_first(client, db):
    db.add(_p(1))
    db.add(_snap(1, D1, defending=5))
    db.add(_snap(1, D2, defending=6))
    db.add(_snap(1, D3, defending=7))
    db.commit()

    data = client.get("/api/training").json()
    dates = [s["synced_at"][:10] for s in data["sessions"]]
    assert dates == sorted(dates, reverse=True)


def test_training_changed_sorted_by_num_changes(client, db):
    db.add(_p(1, "A", "A"))
    db.add(_p(2, "B", "B"))
    # player 1: 1 change, player 2: 2 changes — player 2 should come first
    db.add(_snap(1, D1, defending=7, playmaking=8))
    db.add(_snap(1, D2, defending=8, playmaking=8))  # 1 change
    db.add(_snap(2, D1, defending=5, playmaking=5))
    db.add(_snap(2, D2, defending=6, playmaking=6))  # 2 changes
    db.commit()

    data = client.get("/api/training").json()
    players = data["sessions"][0]["changed_players"]
    assert len(players) == 2
    assert players[0]["player_id"] == 2  # more changes first
    assert players[1]["player_id"] == 1
