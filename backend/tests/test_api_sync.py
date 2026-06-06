from pathlib import Path
from unittest.mock import patch
from app.models.settings import CHPPSettings
from app.models.player_skill_history import PlayerSkillHistory

SQUAD_XML = (Path(__file__).parent / "fixtures" / "squad.xml").read_bytes()


def _seed_settings(db) -> None:
    db.add(
        CHPPSettings(
            id=1,
            consumer_key="ck",
            consumer_secret="cs",
            access_token="at",
            access_token_secret="ats",
        )
    )
    db.commit()


def test_sync_unknown_entity_returns_400(client):
    response = client.post("/api/sync/unknown")
    assert response.status_code == 400


def test_sync_without_settings_returns_400(client):
    response = client.post("/api/sync/squad")
    assert response.status_code == 400
    assert "configured" in response.json()["detail"].lower()


def test_sync_squad_upserts_players(client, db):
    _seed_settings(db)
    with patch("app.api.sync.CHPPClient") as MockClient:
        MockClient.return_value.fetch.return_value = SQUAD_XML
        response = client.post("/api/sync/squad")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    squad = client.get("/api/squad").json()
    assert len(squad) == 2


def test_sync_squad_updates_sync_log(client, db):
    _seed_settings(db)
    with patch("app.api.sync.CHPPClient") as MockClient:
        MockClient.return_value.fetch.return_value = SQUAD_XML
        client.post("/api/sync/squad")
    status = client.get("/api/sync/status").json()
    assert "squad" in status
    assert status["squad"]["status"] == "ok"
    assert status["squad"]["last_sync_at"] is not None


def test_sync_squad_is_idempotent(client, db):
    _seed_settings(db)
    with patch("app.api.sync.CHPPClient") as MockClient:
        MockClient.return_value.fetch.return_value = SQUAD_XML
        client.post("/api/sync/squad")
        client.post("/api/sync/squad")
    squad = client.get("/api/squad").json()
    assert len(squad) == 2


def test_sync_squad_saves_skill_history(client, db):
    _seed_settings(db)
    with patch("app.api.sync.CHPPClient") as MockClient:
        MockClient.return_value.fetch.return_value = SQUAD_XML
        client.post("/api/sync/squad")
    history = db.query(PlayerSkillHistory).all()
    assert len(history) == 2  # 2 players in squad.xml
    assert all(h.source == "CHPP" for h in history)


def test_sync_squad_history_is_idempotent(client, db):
    _seed_settings(db)
    with patch("app.api.sync.CHPPClient") as MockClient:
        MockClient.return_value.fetch.return_value = SQUAD_XML
        client.post("/api/sync/squad")
        client.post("/api/sync/squad")
    history = db.query(PlayerSkillHistory).all()
    assert len(history) == 2  # second sync same day: no duplicates
