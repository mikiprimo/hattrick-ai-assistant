import json
import shutil
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, get_db
from app.models.match_snapshot import MatchSnapshot
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def client_with_hrf_db(tmp_path):
    from app.models import player  # noqa
    from app.models.player_skill_history import PlayerSkillHistory  # noqa
    from app.models.hrf_settings import HRFSettings  # noqa
    from app.models.match_snapshot import MatchSnapshot  # noqa

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()

    def override():
        yield db

    app.dependency_overrides[get_db] = override
    with TestClient(app) as c:
        yield c, db, tmp_path
    app.dependency_overrides.clear()
    db.close()


def test_get_hrf_settings_not_configured(client_with_hrf_db):
    client, _db, _tmp = client_with_hrf_db
    r = client.get("/api/hrf/settings")
    assert r.status_code == 404


def test_post_hrf_settings_saves_folder(client_with_hrf_db, tmp_path):
    client, _db, _tmp = client_with_hrf_db
    r = client.post("/api/hrf/settings", json={"hrf_folder_path": str(tmp_path)})
    assert r.status_code == 200
    r2 = client.get("/api/hrf/settings")
    assert r2.status_code == 200
    assert r2.json()["hrf_folder_path"] == str(tmp_path)


def test_post_hrf_settings_invalid_path(client_with_hrf_db):
    client, _db, _tmp = client_with_hrf_db
    r = client.post("/api/hrf/settings", json={"hrf_folder_path": "/nonexistent/path"})
    assert r.status_code == 400


def test_scan_without_settings_returns_400(client_with_hrf_db):
    client, _db, _tmp = client_with_hrf_db
    r = client.post("/api/hrf/scan")
    assert r.status_code == 400


def test_scan_imports_players_and_snapshots(client_with_hrf_db, tmp_path):
    client, db, _tmp = client_with_hrf_db
    shutil.copy(FIXTURES / "549298-2026-05-20.hrf", tmp_path)
    client.post("/api/hrf/settings", json={"hrf_folder_path": str(tmp_path)})

    r = client.post("/api/hrf/scan")
    assert r.status_code == 200
    data = r.json()
    assert data["files_imported"] == 1
    assert data["players_upserted"] == 2

    from app.models.player import Player
    from app.models.player_skill_history import PlayerSkillHistory
    assert db.query(Player).count() == 2
    assert db.query(PlayerSkillHistory).count() == 2


def test_scan_is_idempotent(client_with_hrf_db, tmp_path):
    client, db, _tmp = client_with_hrf_db
    shutil.copy(FIXTURES / "549298-2026-05-20.hrf", tmp_path)
    client.post("/api/hrf/settings", json={"hrf_folder_path": str(tmp_path)})
    client.post("/api/hrf/scan")
    client.post("/api/hrf/scan")  # second scan

    from app.models.player_skill_history import PlayerSkillHistory
    assert db.query(PlayerSkillHistory).count() == 2  # no duplicates


def test_get_hrf_files_returns_list(client_with_hrf_db, tmp_path):
    client, _db, _tmp = client_with_hrf_db
    shutil.copy(FIXTURES / "549298-2026-05-20.hrf", tmp_path)
    client.post("/api/hrf/settings", json={"hrf_folder_path": str(tmp_path)})

    r = client.get("/api/hrf/files")
    assert r.status_code == 200
    data = r.json()
    assert len(data["files"]) == 1
    assert data["files"][0]["filename"] == "549298-2026-05-20.hrf"
    assert data["files"][0]["imported"] is False

    client.post("/api/hrf/scan")
    r2 = client.get("/api/hrf/files")
    assert r2.json()["files"][0]["imported"] is True


def test_scan_creates_match_snapshot(client_with_hrf_db, tmp_path):
    client, db, _tmp = client_with_hrf_db
    shutil.copy(FIXTURES / "549298-2026-05-21.hrf", tmp_path)
    client.post("/api/hrf/settings", json={"hrf_folder_path": str(tmp_path)})

    r = client.post("/api/hrf/scan")
    assert r.status_code == 200

    ms = db.query(MatchSnapshot).first()
    assert ms is not None
    assert ms.season == 82
    assert ms.matchround == 5
    assert ms.league_position == 2
    assert ms.league_points == 10
    lineup = json.loads(ms.lineup_json)
    assert lineup["keeper"] == 100001
    assert "insideBack1" not in lineup


def test_scan_match_snapshot_is_idempotent(client_with_hrf_db, tmp_path):
    client, db, _tmp = client_with_hrf_db
    shutil.copy(FIXTURES / "549298-2026-05-21.hrf", tmp_path)
    client.post("/api/hrf/settings", json={"hrf_folder_path": str(tmp_path)})

    client.post("/api/hrf/scan")
    client.post("/api/hrf/scan")  # secondo scan

    assert db.query(MatchSnapshot).count() == 1
