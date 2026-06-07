import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, configure_mappers
from sqlalchemy.pool import StaticPool
from app.main import app
from app.database import Base, get_db

configure_mappers()


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db):
    def override():
        yield db
    app.dependency_overrides[get_db] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_rival_tables_exist(db):
    inspector = inspect(db.bind)
    tables = inspector.get_table_names()
    assert "rival_team" in tables
    assert "rival_player" in tables
    assert "rival_ratings_manual" in tables


def test_seasonal_objective_has_strategy_changed_at(db):
    inspector = inspect(db.bind)
    cols = {c["name"] for c in inspector.get_columns("seasonal_objective")}
    assert "strategy_changed_at" in cols


def test_create_rival(client):
    r = client.post("/api/rivals", json={
        "team_id": 999, "team_name": "FC Test",
        "league_series": "VII.935", "season": 82,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["team_name"] == "FC Test"
    assert data["team_id"] == 999


def test_list_rivals(client):
    client.post("/api/rivals", json={"team_id": 1, "team_name": "A", "league_series": "VII.1", "season": 82})
    client.post("/api/rivals", json={"team_id": 2, "team_name": "B", "league_series": "VII.1", "season": 82})
    r = client.get("/api/rivals")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_delete_rival(client):
    client.post("/api/rivals", json={"team_id": 10, "team_name": "X", "league_series": "VII.1", "season": 82})
    r = client.delete("/api/rivals/10")
    assert r.status_code == 200
    assert client.get("/api/rivals").json() == []


_SAMPLE_XML = """<?xml version="1.0"?>
<HattrickData>
  <Team>
    <TeamID>123</TeamID>
    <TeamName>FC Avversario</TeamName>
    <PlayerList>
      <Player>
        <PlayerID>1001</PlayerID><FirstName>Mario</FirstName><LastName>Rossi</LastName>
        <PlayerForm>7</PlayerForm><StaminaSkill>8</StaminaSkill><InjuryLevel>-1</InjuryLevel>
        <KeeperSkill>0</KeeperSkill><DefenderSkill>7</DefenderSkill>
        <PlaymakerSkill>6</PlaymakerSkill><ScorerSkill>5</ScorerSkill>
        <PassingSkill>6</PassingSkill><WingerSkill>5</WingerSkill>
      </Player>
    </PlayerList>
  </Team>
</HattrickData>"""


def test_import_rival_xml(client):
    client.post("/api/rivals", json={"team_id": 123, "team_name": "FC Avversario",
                                     "league_series": "VII.935", "season": 82})
    r = client.post("/api/rivals/123/import-xml", json={"xml": _SAMPLE_XML})
    assert r.status_code == 200
    assert r.json()["players_imported"] == 1


def test_import_rival_xml_unknown_team(client):
    r = client.post("/api/rivals/999/import-xml", json={"xml": _SAMPLE_XML})
    assert r.status_code == 404


def test_set_manual_ratings(client):
    client.post("/api/rivals", json={"team_id": 50, "team_name": "Y",
                                     "league_series": "VII.1", "season": 82})
    r = client.put("/api/rivals/50/ratings", json={"defense": 7.5, "midfield": 8.0, "attack": 6.5})
    assert r.status_code == 200
    assert r.json()["midfield"] == 8.0
