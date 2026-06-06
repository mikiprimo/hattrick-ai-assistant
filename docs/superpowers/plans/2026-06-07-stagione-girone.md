# Stagione Dashboard + Girone Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Trasformare Stagione in una dashboard stagionale viva con 3 modalità (Promozione/Mantenimento/Sviluppo Giovani) e aggiungere la pagina Girone per la gestione delle squadre rivali del campionato.

**Architecture:** Un nuovo modulo `seasonal_analysis.py` con funzioni pure testabili; 3 nuovi modelli DB per i rivali; 6 nuovi endpoint API; 2 pagine frontend (Girone nuova, Stagione riscritta). La logica di calcolo dei rating sfrutta le funzioni già esistenti in `strategy.py`.

**Tech Stack:** FastAPI + SQLAlchemy + SQLite backend; React 19 + TypeScript + Recharts + TanStack Query frontend; `strategy.py` per `_build_lineup` e `role_rating`.

---

## File Map

**Crea:**
- `backend/app/models/rival_team.py`
- `backend/app/models/rival_player.py`
- `backend/app/models/rival_ratings_manual.py`
- `backend/app/api/rivals.py`
- `backend/app/hrf/seasonal_analysis.py`
- `backend/tests/test_seasonal_analysis.py`
- `backend/tests/test_api_rivals.py`
- `frontend/src/pages/Girone.tsx`
- `frontend/src/api/rivals.ts`

**Modifica:**
- `backend/app/main.py` — importa 3 nuovi modelli, monta rivals router
- `backend/app/migrations.py` — aggiunge tabelle rival + colonna `strategy_changed_at`
- `backend/app/models/seasonal_objective.py` — aggiunge `strategy_changed_at`
- `backend/app/api/seasonal.py` — aggiunge `/status` e `/analysis/*`
- `frontend/src/App.tsx` — aggiunge route `/girone`
- `frontend/src/pages/Stagione.tsx` — riscrittura completa
- `frontend/src/api/seasonal.ts` — aggiunge funzioni status + analysis

---

## Task 1: Modelli DB rivali + migrazione

**Files:**
- Create: `backend/app/models/rival_team.py`
- Create: `backend/app/models/rival_player.py`
- Create: `backend/app/models/rival_ratings_manual.py`
- Modify: `backend/app/models/seasonal_objective.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/migrations.py`

- [ ] **Step 1: Crea `rival_team.py`**

```python
# backend/app/models/rival_team.py
from datetime import datetime
from sqlalchemy import Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class RivalTeam(Base):
    __tablename__ = "rival_team"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    team_name: Mapped[str] = mapped_column(String, default="")
    league_series: Mapped[str] = mapped_column(String, default="")
    season: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
```

- [ ] **Step 2: Crea `rival_player.py`**

```python
# backend/app/models/rival_player.py
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class RivalPlayer(Base):
    __tablename__ = "rival_player"
    __table_args__ = (UniqueConstraint("team_id", "player_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(Integer, nullable=False)
    player_id: Mapped[int] = mapped_column(Integer, nullable=False)
    first_name: Mapped[str] = mapped_column(String, default="")
    last_name: Mapped[str] = mapped_column(String, default="")
    goalkeeper: Mapped[int] = mapped_column(Integer, default=0)
    defending: Mapped[int] = mapped_column(Integer, default=0)
    playmaking: Mapped[int] = mapped_column(Integer, default=0)
    scoring: Mapped[int] = mapped_column(Integer, default=0)
    passing: Mapped[int] = mapped_column(Integer, default=0)
    winger: Mapped[int] = mapped_column(Integer, default=0)
    set_pieces: Mapped[int] = mapped_column(Integer, default=0)
    form: Mapped[int] = mapped_column(Integer, default=7)
    stamina: Mapped[int] = mapped_column(Integer, default=7)
    injury_days: Mapped[int] = mapped_column(Integer, default=-1)
    imported_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
```

- [ ] **Step 3: Crea `rival_ratings_manual.py`**

```python
# backend/app/models/rival_ratings_manual.py
from datetime import datetime
from sqlalchemy import Integer, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class RivalRatingsManual(Base):
    __tablename__ = "rival_ratings_manual"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    defense: Mapped[float] = mapped_column(Float, nullable=True)
    midfield: Mapped[float] = mapped_column(Float, nullable=True)
    attack: Mapped[float] = mapped_column(Float, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
```

- [ ] **Step 4: Aggiunge `strategy_changed_at` a `SeasonalObjective`**

In `backend/app/models/seasonal_objective.py`, aggiungi dopo `recommendation`:

```python
    strategy_changed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
```

- [ ] **Step 5: Importa i 3 nuovi modelli in `main.py`**

In `backend/app/main.py`, aggiungi dopo l'import di `SeasonalObjective`:

```python
from app.models.rival_team import RivalTeam  # noqa: F401
from app.models.rival_player import RivalPlayer  # noqa: F401
from app.models.rival_ratings_manual import RivalRatingsManual  # noqa: F401
```

- [ ] **Step 6: Aggiorna `migrations.py`**

In `backend/app/migrations.py`, aggiungi prima del blocco `Base.metadata.create_all`:

```python
    if "seasonal_objective" in tables:
        so_cols = {c["name"] for c in inspector.get_columns("seasonal_objective")}
        if "strategy_changed_at" not in so_cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE seasonal_objective ADD COLUMN strategy_changed_at DATETIME"))
```

- [ ] **Step 7: Scrivi il test che verifica la creazione delle tabelle**

```python
# backend/tests/test_api_rivals.py
def test_rival_tables_exist(db):
    from sqlalchemy import inspect
    inspector = inspect(db.bind)
    tables = inspector.get_table_names()
    assert "rival_team" in tables
    assert "rival_player" in tables
    assert "rival_ratings_manual" in tables
```

- [ ] **Step 8: Esegui il test**

```bash
cd backend && pytest tests/test_api_rivals.py::test_rival_tables_exist -v
```

Atteso: `PASSED`

- [ ] **Step 9: Commit**

```bash
git add backend/app/models/rival_team.py backend/app/models/rival_player.py \
        backend/app/models/rival_ratings_manual.py \
        backend/app/models/seasonal_objective.py \
        backend/app/main.py backend/app/migrations.py \
        backend/tests/test_api_rivals.py
git commit -m "feat: add rival_team, rival_player, rival_ratings_manual models + migration"
```

---

## Task 2: API `/api/rivals`

**Files:**
- Create: `backend/app/api/rivals.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_api_rivals.py`

- [ ] **Step 1: Scrivi i test prima dell'implementazione**

```python
# backend/tests/test_api_rivals.py  (aggiungi/sostituisci il contenuto)
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
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
    from sqlalchemy import inspect
    inspector = inspect(db.bind)
    tables = inspector.get_table_names()
    assert "rival_team" in tables
    assert "rival_player" in tables
    assert "rival_ratings_manual" in tables


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
```

- [ ] **Step 2: Esegui i test per verificare che falliscano**

```bash
cd backend && pytest tests/test_api_rivals.py -v --tb=short
```

Atteso: `FAILED` — `404 Not Found` su tutti gli endpoint `/api/rivals`.

- [ ] **Step 3: Implementa `backend/app/api/rivals.py`**

```python
# backend/app/api/rivals.py
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.rival_team import RivalTeam
from app.models.rival_player import RivalPlayer
from app.models.rival_ratings_manual import RivalRatingsManual
from app.hrf.opponent_parser import parse_opponent_players

router = APIRouter()


class RivalCreateRequest(BaseModel):
    team_id: int
    team_name: str
    league_series: str = ""
    season: int = 0


class RivalXMLRequest(BaseModel):
    xml: str


class RivalRatingsRequest(BaseModel):
    defense: float | None = None
    midfield: float | None = None
    attack: float | None = None


def _serialize_team(t: RivalTeam, player_count: int, manual: RivalRatingsManual | None) -> dict:
    return {
        "team_id": t.team_id,
        "team_name": t.team_name,
        "league_series": t.league_series,
        "season": t.season,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
        "player_count": player_count,
        "manual_ratings": {
            "defense": manual.defense if manual else None,
            "midfield": manual.midfield if manual else None,
            "attack": manual.attack if manual else None,
        } if manual else None,
    }


@router.get("/rivals")
def list_rivals(db: Session = Depends(get_db)):
    teams = db.query(RivalTeam).order_by(RivalTeam.team_name).all()
    result = []
    for t in teams:
        count = db.query(RivalPlayer).filter_by(team_id=t.team_id).count()
        manual = db.query(RivalRatingsManual).filter_by(team_id=t.team_id).first()
        result.append(_serialize_team(t, count, manual))
    return result


@router.post("/rivals")
def create_rival(body: RivalCreateRequest, db: Session = Depends(get_db)):
    existing = db.query(RivalTeam).filter_by(team_id=body.team_id).first()
    if existing:
        existing.team_name = body.team_name
        existing.league_series = body.league_series
        existing.season = body.season
        existing.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        t = existing
    else:
        t = RivalTeam(
            team_id=body.team_id,
            team_name=body.team_name,
            league_series=body.league_series,
            season=body.season,
            updated_at=datetime.now(timezone.utc),
        )
        db.add(t)
        db.commit()
        db.refresh(t)
    return _serialize_team(t, 0, None)


@router.post("/rivals/{team_id}/import-xml")
def import_rival_xml(team_id: int, body: RivalXMLRequest, db: Session = Depends(get_db)):
    team = db.query(RivalTeam).filter_by(team_id=team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail=f"Squadra {team_id} non trovata")

    try:
        _parsed_team_id, _name, players = parse_opponent_players(body.xml)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"XML non valido: {e}")

    now = datetime.now(timezone.utc)
    db.query(RivalPlayer).filter_by(team_id=team_id).delete()
    for p in players:
        db.add(RivalPlayer(
            team_id=team_id,
            player_id=p.player_id,
            first_name=p.first_name,
            last_name=p.last_name,
            goalkeeper=p.goalkeeper,
            defending=p.defending,
            playmaking=p.playmaking,
            scoring=p.scoring,
            passing=p.passing,
            winger=p.winger,
            set_pieces=p.set_pieces,
            form=p.form,
            stamina=p.stamina,
            injury_days=p.injury_days,
            imported_at=now,
        ))
    team.updated_at = now
    db.commit()
    return {"players_imported": len(players), "team_id": team_id}


@router.put("/rivals/{team_id}/ratings")
def set_manual_ratings(team_id: int, body: RivalRatingsRequest, db: Session = Depends(get_db)):
    if not db.query(RivalTeam).filter_by(team_id=team_id).first():
        raise HTTPException(status_code=404, detail=f"Squadra {team_id} non trovata")
    manual = db.query(RivalRatingsManual).filter_by(team_id=team_id).first()
    now = datetime.now(timezone.utc)
    if manual:
        manual.defense = body.defense
        manual.midfield = body.midfield
        manual.attack = body.attack
        manual.updated_at = now
    else:
        manual = RivalRatingsManual(
            team_id=team_id,
            defense=body.defense,
            midfield=body.midfield,
            attack=body.attack,
            updated_at=now,
        )
        db.add(manual)
    db.commit()
    db.refresh(manual)
    return {"team_id": team_id, "defense": manual.defense,
            "midfield": manual.midfield, "attack": manual.attack}


@router.delete("/rivals/{team_id}")
def delete_rival(team_id: int, db: Session = Depends(get_db)):
    team = db.query(RivalTeam).filter_by(team_id=team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail=f"Squadra {team_id} non trovata")
    db.query(RivalPlayer).filter_by(team_id=team_id).delete()
    db.query(RivalRatingsManual).filter_by(team_id=team_id).delete()
    db.delete(team)
    db.commit()
    return {"deleted": team_id}
```

- [ ] **Step 4: Monta il router in `main.py`**

In `backend/app/main.py`, aggiungi:

```python
from app.api import rivals as rivals_router
# ...
app.include_router(rivals_router.router, prefix="/api")
```

- [ ] **Step 5: Esegui i test**

```bash
cd backend && pytest tests/test_api_rivals.py -v
```

Atteso: tutti i test `PASSED`.

- [ ] **Step 6: Esegui la suite completa**

```bash
cd backend && pytest -v --tb=short 2>&1 | tail -5
```

Atteso: `N passed` (tutti i test precedenti ancora verdi).

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/rivals.py backend/app/main.py backend/tests/test_api_rivals.py
git commit -m "feat: add /api/rivals CRUD + XML import endpoints"
```

---

## Task 3: Motore di analisi stagionale

**Files:**
- Create: `backend/app/hrf/seasonal_analysis.py`
- Create: `backend/tests/test_seasonal_analysis.py`

- [ ] **Step 1: Scrivi i test**

```python
# backend/tests/test_seasonal_analysis.py
import pytest
from dataclasses import dataclass, field
from app.hrf.seasonal_analysis import (
    compute_status,
    analyze_youth,
    analyze_maintain,
    analyze_promote,
)


@dataclass
class P:
    """Minimal player proxy for testing."""
    id: int
    first_name: str
    last_name: str
    age: int
    age_days: int = 0
    goalkeeper: int = 0
    defending: int = 0
    playmaking: int = 0
    scoring: int = 0
    passing: int = 0
    winger: int = 0
    set_pieces: int = 0
    form: int = 7
    stamina: int = 7
    injury_days: int = -1
    salary: int = 50_000
    speciality: str = ""


def _squad():
    """11 generic players with reasonable skills."""
    return [
        P(1,  "GK",  "A", 25, goalkeeper=9),
        P(2,  "RB",  "B", 26, defending=7, winger=6),
        P(3,  "CB",  "C", 27, defending=8, playmaking=5),
        P(4,  "CB",  "D", 28, defending=8, playmaking=5),
        P(5,  "LB",  "E", 26, defending=7, winger=6),
        P(6,  "RM",  "F", 24, winger=8, playmaking=6),
        P(7,  "CM",  "G", 23, playmaking=8, passing=7),
        P(8,  "CM",  "H", 22, playmaking=7, passing=6),
        P(9,  "LM",  "I", 25, winger=7, playmaking=6),
        P(10, "FW",  "J", 24, scoring=8, passing=6),
        P(11, "FW",  "K", 23, scoring=7, passing=5),
    ]


# --- compute_status ---

def test_status_promote_on_track():
    r = compute_status("promote", position=2, points=18, played=9, history=[])
    assert r["status"] == "on_track"
    assert abs(r["projected_points"] - 28.0) < 0.1


def test_status_promote_at_risk():
    r = compute_status("promote", position=4, points=14, played=9, history=[])
    assert r["status"] == "at_risk"


def test_status_promote_off_track():
    r = compute_status("promote", position=6, points=8, played=9, history=[])
    assert r["status"] == "off_track"
    assert r["suggested_strategy"] == "maintain"


def test_status_maintain_on_track():
    r = compute_status("maintain", position=4, points=16, played=9, history=[])
    assert r["status"] == "on_track"


def test_status_maintain_at_risk():
    r = compute_status("maintain", position=7, points=10, played=9, history=[])
    assert r["status"] == "at_risk"


def test_status_no_games_played():
    r = compute_status("promote", position=0, points=0, played=0, history=[])
    assert r["status"] == "on_track"
    assert r["projected_points"] == 0


# --- analyze_youth ---

def test_analyze_youth_filters_over_24():
    players = _squad()  # all >= 22, with some >= 24
    result = analyze_youth(players, [])
    assert all(p["age"] < 24 for p in result)


def test_analyze_youth_sorted_by_potential():
    players = [
        P(1, "Young", "A", 19, playmaking=8),
        P(2, "Old", "B", 23, playmaking=9),
    ]
    result = analyze_youth(players, [])
    assert result[0]["age"] == 19  # higher potential despite lower skill


def test_analyze_youth_delta():
    @dataclass
    class FakeHistory:
        player_id: int
        snapshot_date: object
        playmaking: int
        goalkeeper: int = 0
        defending: int = 0
        scoring: int = 0
        passing: int = 0
        winger: int = 0

    from datetime import date
    history = [
        FakeHistory(1, date(2026, 1, 1), playmaking=6),
        FakeHistory(1, date(2026, 5, 1), playmaking=8),
    ]
    players = [P(1, "A", "B", 20, playmaking=8)]
    result = analyze_youth(players, history)
    assert result[0]["skill_delta"] == 2


# --- analyze_maintain ---

def test_analyze_maintain_returns_formation():
    result = analyze_maintain(_squad())
    assert result["best_formation"] in [
        "4-4-2","3-5-2","4-3-3","3-4-3","5-4-1","4-5-1","5-3-2","5-2-3","5-5-0","2-5-3"
    ]


def test_analyze_maintain_weakest_sector():
    # GK strong, attack very weak
    players = [
        P(1, "GK", "A", 25, goalkeeper=12),
        P(2, "CB", "B", 25, defending=10),
        P(3, "CB", "C", 25, defending=10),
        P(4, "CB", "D", 25, defending=10),
        P(5, "CM", "E", 25, playmaking=8),
        P(6, "CM", "F", 25, playmaking=8),
        P(7, "CM", "G", 25, playmaking=8),
        P(8, "WG", "H", 25, winger=8),
        P(9, "WG", "I", 25, winger=8),
        P(10, "FW", "J", 25, scoring=3),
        P(11, "FW", "K", 25, scoring=3),
    ]
    result = analyze_maintain(players)
    assert result["weakest_sector"] == "attack"


# --- analyze_promote ---

def test_analyze_promote_no_rivals():
    result = analyze_promote(_squad(), [])
    assert "message" in result
    assert result["rival_avg"] is None


def test_analyze_promote_with_rivals():
    strong_rival_players = [
        P(i, "R", str(i), 25, defending=10, playmaking=10, scoring=10, winger=9, goalkeeper=9)
        for i in range(11)
    ]
    rivals = [{"team_name": "FC Forte", "players": strong_rival_players, "manual_ratings": None}]
    result = analyze_promote(_squad(), rivals)
    assert result["rival_avg"] is not None
    assert len(result["needed_skills"]) > 0
    assert any(gap < 0 for gap in result["gaps"].values())


def test_analyze_promote_manual_ratings_override():
    rivals = [{"team_name": "FC Manual", "players": [], "manual_ratings": {
        "defense": 9.0, "midfield": 9.0, "attack": 9.0,
    }}]
    result = analyze_promote(_squad(), rivals)
    assert result["rival_avg"]["defense"] == pytest.approx(9.0)
```

- [ ] **Step 2: Esegui per verificare che falliscano**

```bash
cd backend && pytest tests/test_seasonal_analysis.py -v --tb=short 2>&1 | head -20
```

Atteso: `ModuleNotFoundError: No module named 'app.hrf.seasonal_analysis'`

- [ ] **Step 3: Implementa `backend/app/hrf/seasonal_analysis.py`**

```python
# backend/app/hrf/seasonal_analysis.py
from __future__ import annotations
from dataclasses import dataclass

SKILL_LABELS: dict[int, str] = {
    0: "inesistente", 1: "disastroso", 2: "tremendo", 3: "scarso",
    4: "debole", 5: "insufficiente", 6: "accettabile", 7: "buono",
    8: "eccellente", 9: "formidabile", 10: "straordinario",
    11: "splendido", 12: "magnifico", 13: "fuoriclasse",
    14: "sovrannaturale", 15: "titanico", 16: "extraterrestre",
    17: "mitico", 18: "magico", 19: "utopico", 20: "divino",
}

_PRIMARY_SKILLS = ["goalkeeper", "defending", "playmaking", "scoring", "passing", "winger"]

LINE_IT = {
    "goalkeeper": "Portiere",
    "defense": "Difesa",
    "midfield": "Centrocampo",
    "attack": "Attacco",
}


def _primary_skill(player) -> tuple[str, int]:
    return max(
        ((s, getattr(player, s, 0)) for s in _PRIMARY_SKILLS),
        key=lambda x: x[1],
    )


def _potential_score(player) -> float:
    _, val = _primary_skill(player)
    return round(val * max(0, 24 - player.age) / 24, 2)


def compute_status(
    strategy: str,
    position: int,
    points: int,
    played: int,
    history: list[dict],
) -> dict:
    projected = round((points / played) * 14, 1) if played > 0 else 0.0
    status, message, suggested = _classify(strategy, position, points, played, projected)
    return {
        "status": status,
        "projected_points": projected,
        "current_points": points,
        "current_position": position,
        "played": played,
        "remaining": 14 - played,
        "message": message,
        "suggested_strategy": suggested,
        "history": history,
    }


def _classify(
    strategy: str, position: int, points: int, played: int, projected: float
) -> tuple[str, str, str | None]:
    if played == 0:
        return "on_track", "Stagione non ancora iniziata.", None

    if strategy == "promote":
        if position <= 2 and projected >= 26:
            return "on_track", f"Sei {position}° con {points} pt. Ottimo ritmo per la promozione.", None
        if position <= 4 or projected >= 20:
            sug = "maintain" if position > 4 else None
            return "at_risk", f"Sei {position}° con {points} pt. Ritmo a rischio (proiezione: {projected:.0f} pt).", sug
        return "off_track", (
            f"Sei {position}° con {points} pt. La promozione è difficile — valuta di cambiare obiettivo."
        ), "maintain"

    if strategy == "maintain":
        if position <= 6 and projected >= 16:
            return "on_track", f"Sei {position}° con {points} pt. Salvezza gestita.", None
        if projected >= 12:
            return "at_risk", f"Sei {position}° con {points} pt (proiezione: {projected:.0f}). Attenzione alla retrocessione.", None
        return "off_track", f"Sei in zona retrocessione ({position}°, {points} pt). Serve un cambio di rotta.", None

    # youth — no quantitative threshold
    return "on_track", "Stagione di sviluppo. Monitora i progressi dei giovani.", None


def analyze_youth(players: list, skill_history: list) -> list[dict]:
    young = [p for p in players if p.age < 24 and getattr(p, "injury_days", -1) <= 0]

    by_player: dict[int, list] = {}
    for h in skill_history:
        by_player.setdefault(h.player_id, []).append(h)

    deltas: dict[int, int] = {}
    for pid, entries in by_player.items():
        if len(entries) >= 2:
            entries.sort(key=lambda h: h.snapshot_date)
            first, last = entries[0], entries[-1]
            deltas[pid] = sum(
                max(0, getattr(last, s, 0) - getattr(first, s, 0))
                for s in _PRIMARY_SKILLS
            )
        else:
            deltas[pid] = 0

    result = []
    for p in young:
        skill_name, skill_val = _primary_skill(p)
        result.append({
            "player_id": p.id,
            "name": f"{p.first_name} {p.last_name}",
            "age": p.age,
            "primary_skill": skill_name,
            "primary_skill_value": skill_val,
            "primary_skill_label": SKILL_LABELS.get(skill_val, str(skill_val)),
            "potential_score": _potential_score(p),
            "skill_delta": deltas.get(p.id, 0),
            "speciality": getattr(p, "speciality", None),
        })

    result.sort(key=lambda x: x["potential_score"], reverse=True)
    return result


def analyze_maintain(players: list) -> dict:
    from app.hrf.strategy import _build_lineup, FORMATIONS

    healthy = [p for p in players if getattr(p, "injury_days", -1) <= 0]
    if not healthy:
        return {"error": "Nessun giocatore sano disponibile"}

    best_name, best_score, best_ratings = None, float("-inf"), None
    for name in FORMATIONS:
        data = _build_lineup(healthy, name)
        lr = data["line_ratings"]
        score = sum(lr.values())
        if score > best_score:
            best_score, best_name, best_ratings = score, name, lr

    weakest = min(best_ratings, key=lambda k: best_ratings[k])
    return {
        "best_formation": best_name,
        "line_ratings": {k: round(v, 2) for k, v in best_ratings.items()},
        "weakest_sector": weakest,
        "weakest_sector_label": LINE_IT[weakest],
        "weakest_rating": round(best_ratings[weakest], 2),
        "message": (
            f"Il reparto più debole è la {LINE_IT[weakest].lower()} "
            f"(rating {best_ratings[weakest]:.1f}). Schema consigliato: {best_name}."
        ),
    }


@dataclass
class _RivalProxy:
    goalkeeper: int = 0
    defending: int = 0
    playmaking: int = 0
    scoring: int = 0
    passing: int = 0
    winger: int = 0
    set_pieces: int = 0
    form: int = 7
    stamina: int = 7
    injury_days: int = -1
    speciality: str = ""


def _rival_line_ratings(players: list, manual: dict | None) -> dict:
    if manual and any(manual.get(k) for k in ("defense", "midfield", "attack")):
        return {
            "goalkeeper": float(manual.get("goalkeeper") or 0),
            "defense":    float(manual.get("defense")    or 0),
            "midfield":   float(manual.get("midfield")   or 0),
            "attack":     float(manual.get("attack")     or 0),
        }
    if not players:
        return {"goalkeeper": 0.0, "defense": 0.0, "midfield": 0.0, "attack": 0.0}

    from app.hrf.strategy import _build_lineup
    proxies = [_RivalProxy(
        goalkeeper=rp.goalkeeper, defending=rp.defending,
        playmaking=rp.playmaking, scoring=rp.scoring,
        passing=rp.passing, winger=rp.winger, set_pieces=rp.set_pieces,
    ) for rp in players]
    return _build_lineup(proxies, "4-4-2")["line_ratings"]


def analyze_promote(my_players: list, rivals: list) -> dict:
    """
    rivals: list of dicts with keys:
      team_name: str
      players: list of objects with goalkeeper/defending/… attributes
      manual_ratings: dict | None  — {"defense": float, "midfield": float, "attack": float}
    """
    from app.hrf.strategy import _build_lineup, FORMATIONS, role_rating

    healthy = [p for p in my_players if getattr(p, "injury_days", -1) <= 0]
    if not healthy:
        return {"error": "Nessun giocatore sano disponibile"}

    best_name, best_score, my_ratings = None, float("-inf"), None
    for name in FORMATIONS:
        data = _build_lineup(healthy, name)
        lr = data["line_ratings"]
        score = sum(lr.values())
        if score > best_score:
            best_score, best_name, my_ratings = score, name, lr

    if not rivals:
        return {
            "best_formation": best_name,
            "my_ratings": {k: round(v, 2) for k, v in my_ratings.items()},
            "rival_avg": None,
            "gaps": {},
            "needed_skills": [],
            "sell_candidates": [],
            "message": (
                "Nessuna squadra rivale registrata. "
                "Aggiungi le squadre del girone nella sezione Girone."
            ),
        }

    rival_ratings_list = [
        _rival_line_ratings(r.get("players", []), r.get("manual_ratings"))
        for r in rivals
    ]
    rival_avg = {
        line: round(sum(r[line] for r in rival_ratings_list) / len(rival_ratings_list), 2)
        for line in ("goalkeeper", "defense", "midfield", "attack")
    }

    gaps = {
        line: round(my_ratings[line] - rival_avg[line], 2)
        for line in ("goalkeeper", "defense", "midfield", "attack")
    }

    _ROLES = ["goalkeeper", "side_defender", "center_defender", "inside_mid", "winger", "forward"]

    def contribution(p) -> float:
        return max(role_rating(p, r) for r in _ROLES)

    needed_skills = []
    for line, gap in gaps.items():
        if gap < -0.5:
            skill_val = min(20, round(rival_avg[line] + 1.5))
            needed_skills.append({
                "sector": line,
                "sector_label": LINE_IT[line],
                "gap": gap,
                "min_skill_value": skill_val,
                "min_skill_label": SKILL_LABELS.get(skill_val, str(skill_val)),
            })
    needed_skills.sort(key=lambda x: x["gap"])

    avg_salary = sum(getattr(p, "salary", 0) for p in healthy) / len(healthy)
    avg_rating = sum(my_ratings.values()) / 4
    sell_candidates = [
        {
            "player_id": p.id,
            "name": f"{p.first_name} {p.last_name}",
            "age": p.age,
            "salary": getattr(p, "salary", 0),
            "contribution": round(contribution(p), 2),
        }
        for p in healthy
        if getattr(p, "salary", 0) > avg_salary and contribution(p) < avg_rating
    ]
    sell_candidates.sort(key=lambda x: x["salary"], reverse=True)

    message = f"Schema consigliato: {best_name}."
    if needed_skills:
        worst = needed_skills[0]
        message += (
            f" Gap critico in {worst['sector_label'].lower()} (∆ {worst['gap']:.1f}): "
            f"cerca almeno un giocatore '{worst['min_skill_label']}' in quel reparto."
        )

    return {
        "best_formation": best_name,
        "my_ratings": {k: round(v, 2) for k, v in my_ratings.items()},
        "rival_avg": rival_avg,
        "gaps": gaps,
        "needed_skills": needed_skills,
        "sell_candidates": sell_candidates[:3],
        "message": message,
    }
```

- [ ] **Step 4: Esegui i test**

```bash
cd backend && pytest tests/test_seasonal_analysis.py -v
```

Atteso: tutti `PASSED`.

- [ ] **Step 5: Suite completa**

```bash
cd backend && pytest -v --tb=short 2>&1 | tail -5
```

Atteso: tutti i test precedenti ancora verdi.

- [ ] **Step 6: Commit**

```bash
git add backend/app/hrf/seasonal_analysis.py backend/tests/test_seasonal_analysis.py
git commit -m "feat: add seasonal_analysis engine (status, youth, maintain, promote)"
```

---

## Task 4: Endpoint `/api/seasonal/status` e `/api/seasonal/analysis/*`

**Files:**
- Modify: `backend/app/api/seasonal.py`
- Create (aggiungi a): `backend/tests/test_api_seasonal.py` — nuovi test per i 4 endpoint

- [ ] **Step 1: Aggiungi i test ai test seasonal esistenti**

Apri `backend/tests/test_api_seasonal.py` e aggiungi alla fine:

```python
# ---- nuovi test per status e analysis ----
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
    db.add(__import__("app.models.seasonal_objective", fromlist=["SeasonalObjective"]).SeasonalObjective(
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
```

- [ ] **Step 2: Esegui per verificare il fallimento**

```bash
cd backend && pytest tests/test_api_seasonal.py::test_seasonal_status_on_track \
    tests/test_api_seasonal.py::test_analysis_maintain -v --tb=short
```

Atteso: `FAILED` — `404` sugli endpoint.

- [ ] **Step 3: Aggiungi i 4 endpoint in `backend/app/api/seasonal.py`**

In cima al file, aggiungi gli import:

```python
from app.models.player import Player
from app.models.player_skill_history import PlayerSkillHistory
from app.models.match_snapshot import MatchSnapshot
from app.models.rival_team import RivalTeam
from app.models.rival_player import RivalPlayer
from app.models.rival_ratings_manual import RivalRatingsManual
from app.hrf.seasonal_analysis import (
    compute_status, analyze_youth, analyze_maintain, analyze_promote,
)
```

Poi aggiungi questi 4 endpoint dopo gli endpoint esistenti (prima di `_serialize`):

```python
@router.get("/seasonal/status")
def get_status(db: Session = Depends(get_db)):
    obj = db.query(SeasonalObjective).order_by(SeasonalObjective.season.desc()).first()
    latest = db.query(MatchSnapshot).order_by(MatchSnapshot.snapshot_date.desc()).first()

    if not obj or not latest:
        return compute_status("maintain", 0, 0, 0, [])

    history_rows = (
        db.query(MatchSnapshot)
        .filter(MatchSnapshot.season == latest.season)
        .order_by(MatchSnapshot.matchround)
        .all()
    )
    history = [
        {"matchround": s.matchround, "points": s.league_points, "position": s.league_position}
        for s in history_rows
    ]
    return compute_status(
        obj.strategy,
        latest.league_position,
        latest.league_points,
        latest.league_played,
        history,
    )


@router.get("/seasonal/analysis/youth")
def analysis_youth(db: Session = Depends(get_db)):
    latest = db.query(MatchSnapshot).order_by(MatchSnapshot.snapshot_date.desc()).first()
    players = db.query(Player).all()
    history = []
    if latest:
        history = (
            db.query(PlayerSkillHistory)
            .join(MatchSnapshot, PlayerSkillHistory.snapshot_date == MatchSnapshot.snapshot_date)
            .filter(MatchSnapshot.season == latest.season)
            .all()
        )
    return analyze_youth(players, history)


@router.get("/seasonal/analysis/maintain")
def analysis_maintain(db: Session = Depends(get_db)):
    players = db.query(Player).all()
    return analyze_maintain(players)


@router.get("/seasonal/analysis/promote")
def analysis_promote(db: Session = Depends(get_db)):
    players = db.query(Player).all()
    latest = db.query(MatchSnapshot).order_by(MatchSnapshot.snapshot_date.desc()).first()
    series = latest.league_series if latest else ""

    teams = db.query(RivalTeam).filter_by(league_series=series).all() if series else []
    rivals = []
    for t in teams:
        rp = db.query(RivalPlayer).filter_by(team_id=t.team_id).all()
        manual = db.query(RivalRatingsManual).filter_by(team_id=t.team_id).first()
        rivals.append({
            "team_name": t.team_name,
            "players": rp,
            "manual_ratings": {
                "defense": manual.defense,
                "midfield": manual.midfield,
                "attack": manual.attack,
            } if manual else None,
        })
    return analyze_promote(players, rivals)
```

- [ ] **Step 4: Esegui i nuovi test**

```bash
cd backend && pytest tests/test_api_seasonal.py -v --tb=short 2>&1 | tail -20
```

Atteso: tutti i test di questo file `PASSED`.

- [ ] **Step 5: Suite completa**

```bash
cd backend && pytest -v --tb=short 2>&1 | tail -5
```

Atteso: tutti `PASSED`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/seasonal.py backend/tests/test_api_seasonal.py
git commit -m "feat: add /api/seasonal/status and /api/seasonal/analysis/* endpoints"
```

---

## Task 5: Frontend — pagina Girone

**Files:**
- Create: `frontend/src/api/rivals.ts`
- Create: `frontend/src/pages/Girone.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Crea `frontend/src/api/rivals.ts`**

```typescript
// frontend/src/api/rivals.ts
import { apiFetch } from './client'

export interface RivalTeam {
  team_id: number
  team_name: string
  league_series: string
  season: number
  updated_at: string | null
  player_count: number
  manual_ratings: { defense: number | null; midfield: number | null; attack: number | null } | null
}

export function getRivals(): Promise<RivalTeam[]> {
  return apiFetch<RivalTeam[]>('/api/rivals')
}

export function createRival(body: {
  team_id: number; team_name: string; league_series: string; season: number
}): Promise<RivalTeam> {
  return apiFetch<RivalTeam>('/api/rivals', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export function importRivalXml(team_id: number, xml: string): Promise<{ players_imported: number }> {
  return apiFetch(`/api/rivals/${team_id}/import-xml`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ xml }),
  })
}

export function setRivalRatings(
  team_id: number,
  ratings: { defense?: number; midfield?: number; attack?: number }
): Promise<{ team_id: number; defense: number; midfield: number; attack: number }> {
  return apiFetch(`/api/rivals/${team_id}/ratings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(ratings),
  })
}

export function deleteRival(team_id: number): Promise<{ deleted: number }> {
  return apiFetch(`/api/rivals/${team_id}`, { method: 'DELETE' })
}
```

- [ ] **Step 2: Crea `frontend/src/pages/Girone.tsx`**

```tsx
// frontend/src/pages/Girone.tsx
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getLatestLeague } from '../api/matches'
import { getRivals, createRival, importRivalXml, setRivalRatings, deleteRival } from '../api/rivals'

const sec: React.CSSProperties = {
  background: '#fff', borderRadius: 8, padding: 20, marginBottom: 16,
  boxShadow: '0 1px 3px rgba(0,0,0,.08)',
}
const inp: React.CSSProperties = {
  border: '1px solid #d1d5db', borderRadius: 6, padding: '6px 10px',
  fontSize: 14, width: '100%', boxSizing: 'border-box',
}
const btnP: React.CSSProperties = {
  background: '#3b82f6', color: '#fff', border: 'none', borderRadius: 6,
  padding: '7px 16px', cursor: 'pointer', fontSize: 13, fontWeight: 600,
}
const btnD: React.CSSProperties = {
  background: '#fee2e2', color: '#dc2626', border: 'none', borderRadius: 6,
  padding: '5px 10px', cursor: 'pointer', fontSize: 12,
}

export function Girone() {
  const qc = useQueryClient()
  const leagueQ = useQuery({ queryKey: ['latest-league'], queryFn: getLatestLeague })
  const rivalsQ = useQuery({ queryKey: ['rivals'], queryFn: getRivals })

  const [newId, setNewId] = useState('')
  const [newName, setNewName] = useState('')
  const [xmlMap, setXmlMap] = useState<Record<number, string>>({})
  const [ratingMap, setRatingMap] = useState<Record<number, { defense: string; midfield: string; attack: string }>>({})
  const [expandedId, setExpandedId] = useState<number | null>(null)

  const series = leagueQ.data?.league_series ?? ''
  const season = leagueQ.data?.season ?? 0

  const createMut = useMutation({
    mutationFn: () => createRival({
      team_id: parseInt(newId), team_name: newName, league_series: series, season,
    }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['rivals'] }); setNewId(''); setNewName('') },
  })

  const xmlMut = useMutation({
    mutationFn: ({ team_id, xml }: { team_id: number; xml: string }) => importRivalXml(team_id, xml),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['rivals'] }),
  })

  const ratingMut = useMutation({
    mutationFn: ({ team_id, r }: { team_id: number; r: { defense: string; midfield: string; attack: string } }) =>
      setRivalRatings(team_id, {
        defense: parseFloat(r.defense) || undefined,
        midfield: parseFloat(r.midfield) || undefined,
        attack: parseFloat(r.attack) || undefined,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['rivals'] }),
  })

  const deleteMut = useMutation({
    mutationFn: (team_id: number) => deleteRival(team_id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['rivals'] }),
  })

  const rivals = rivalsQ.data ?? []

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 4 }}>Girone</h2>
      {series && (
        <p style={{ fontSize: 14, color: '#6b7280', marginBottom: 20 }}>
          Serie: <strong>{series}</strong> · Stagione {season}
        </p>
      )}

      {/* Aggiungi squadra */}
      <div style={sec}>
        <h3 style={{ margin: '0 0 12px', fontSize: 15 }}>Aggiungi squadra rivale</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr auto', gap: 8, alignItems: 'end' }}>
          <div>
            <label style={{ fontSize: 12, color: '#6b7280', display: 'block', marginBottom: 4 }}>Team ID</label>
            <input style={inp} type="number" value={newId} onChange={e => setNewId(e.target.value)} placeholder="123456" />
          </div>
          <div>
            <label style={{ fontSize: 12, color: '#6b7280', display: 'block', marginBottom: 4 }}>Nome squadra</label>
            <input style={inp} type="text" value={newName} onChange={e => setNewName(e.target.value)} placeholder="FC Avversario" />
          </div>
          <button style={btnP} disabled={!newId || !newName || createMut.isPending}
            onClick={() => createMut.mutate()}>
            Aggiungi
          </button>
        </div>
      </div>

      {/* Lista rivali */}
      {rivals.length === 0 && (
        <p style={{ color: '#9ca3af', fontSize: 14, textAlign: 'center', padding: 32 }}>
          Nessuna squadra rivale registrata.
        </p>
      )}
      {rivals.map(t => {
        const expanded = expandedId === t.team_id
        const xml = xmlMap[t.team_id] ?? ''
        const r = ratingMap[t.team_id] ?? { defense: '', midfield: '', attack: '' }
        const mr = t.manual_ratings
        return (
          <div key={t.team_id} style={{ ...sec, border: expanded ? '1px solid #bfdbfe' : undefined }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <span style={{ fontWeight: 600, fontSize: 15 }}>{t.team_name}</span>
                <span style={{ fontSize: 12, color: '#9ca3af', marginLeft: 8 }}>#{t.team_id}</span>
                {t.player_count > 0 && (
                  <span style={{ fontSize: 12, color: '#059669', marginLeft: 8 }}>
                    {t.player_count} giocatori
                  </span>
                )}
                {mr && (mr.defense || mr.midfield || mr.attack) && (
                  <span style={{ fontSize: 12, color: '#7c3aed', marginLeft: 8 }}>
                    Dif {mr.defense?.toFixed(1)} · Cen {mr.midfield?.toFixed(1)} · Att {mr.attack?.toFixed(1)}
                  </span>
                )}
              </div>
              <div style={{ display: 'flex', gap: 6 }}>
                <button style={{ ...btnP, background: expanded ? '#e0e7ff' : '#3b82f6',
                  color: expanded ? '#3730a3' : '#fff' }}
                  onClick={() => setExpandedId(expanded ? null : t.team_id)}>
                  {expanded ? 'Chiudi' : 'Gestisci'}
                </button>
                <button style={btnD} onClick={() => deleteMut.mutate(t.team_id)}>Elimina</button>
              </div>
            </div>

            {expanded && (
              <div style={{ marginTop: 16, display: 'grid', gap: 16 }}>
                {/* Import XML */}
                <div>
                  <label style={{ fontSize: 13, fontWeight: 600, display: 'block', marginBottom: 6 }}>
                    Importa giocatori (incolla XML CHPP)
                  </label>
                  <textarea value={xml}
                    onChange={e => setXmlMap(m => ({ ...m, [t.team_id]: e.target.value }))}
                    placeholder="Incolla il contenuto del file XML della squadra avversaria..."
                    style={{ ...inp, height: 100, resize: 'vertical', fontFamily: 'monospace', fontSize: 12 }} />
                  <button style={{ ...btnP, marginTop: 6 }}
                    disabled={!xml || xmlMut.isPending}
                    onClick={() => xmlMut.mutate({ team_id: t.team_id, xml })}>
                    Importa giocatori
                  </button>
                </div>

                {/* Rating manuali */}
                <div>
                  <label style={{ fontSize: 13, fontWeight: 600, display: 'block', marginBottom: 6 }}>
                    Rating manuali (opzionali — sovrascrivono XML)
                  </label>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr auto', gap: 8, alignItems: 'end' }}>
                    {(['defense', 'midfield', 'attack'] as const).map(f => (
                      <div key={f}>
                        <label style={{ fontSize: 12, color: '#6b7280', display: 'block', marginBottom: 4 }}>
                          {f === 'defense' ? 'Difesa' : f === 'midfield' ? 'Centrocampo' : 'Attacco'}
                        </label>
                        <input style={inp} type="number" step="0.1" min="0" max="20"
                          value={r[f]}
                          onChange={e => setRatingMap(m => ({ ...m, [t.team_id]: { ...r, [f]: e.target.value } }))}
                          placeholder={mr?.[f]?.toFixed(1) ?? '—'} />
                      </div>
                    ))}
                    <button style={btnP}
                      disabled={ratingMut.isPending}
                      onClick={() => ratingMut.mutate({ team_id: t.team_id, r })}>
                      Salva
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
```

- [ ] **Step 3: Aggiorna `App.tsx`**

```tsx
// Aggiungi l'import:
import { Girone } from './pages/Girone'

// Aggiungi nel nav dentro <Layout>:
<NavLink to="/girone" style={navStyle}>Girone</NavLink>

// Aggiungi nella children array del router:
{ path: 'girone', element: <Girone /> },
```

- [ ] **Step 4: Build check**

```bash
cd frontend && npm run build 2>&1 | tail -10
```

Atteso: `✓ built in Xs` senza errori TypeScript.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/rivals.ts frontend/src/pages/Girone.tsx frontend/src/App.tsx
git commit -m "feat: add Girone page with rival team management"
```

---

## Task 6: Frontend — riscrittura pagina Stagione

**Files:**
- Modify: `frontend/src/api/seasonal.ts`
- Modify: `frontend/src/pages/Stagione.tsx`

- [ ] **Step 1: Aggiorna `frontend/src/api/seasonal.ts`**

Aggiungi alla fine del file esistente:

```typescript
export interface SeasonStatus {
  status: 'on_track' | 'at_risk' | 'off_track'
  projected_points: number
  current_points: number
  current_position: number
  played: number
  remaining: number
  message: string
  suggested_strategy: string | null
  history: { matchround: number; points: number; position: number }[]
}

export interface YouthPlayer {
  player_id: number
  name: string
  age: number
  primary_skill: string
  primary_skill_value: number
  primary_skill_label: string
  potential_score: number
  skill_delta: number
  speciality: string | null
}

export interface MaintainAnalysis {
  best_formation: string
  line_ratings: Record<string, number>
  weakest_sector: string
  weakest_sector_label: string
  weakest_rating: number
  message: string
}

export interface PromoteAnalysis {
  best_formation: string
  my_ratings: Record<string, number>
  rival_avg: Record<string, number> | null
  gaps: Record<string, number>
  needed_skills: { sector: string; sector_label: string; gap: number; min_skill_value: number; min_skill_label: string }[]
  sell_candidates: { player_id: number; name: string; age: number; salary: number; contribution: number }[]
  message: string
}

export function getSeasonalStatus(): Promise<SeasonStatus> {
  return apiFetch<SeasonStatus>('/api/seasonal/status')
}

export function getAnalysisYouth(): Promise<YouthPlayer[]> {
  return apiFetch<YouthPlayer[]>('/api/seasonal/analysis/youth')
}

export function getAnalysisMaintain(): Promise<MaintainAnalysis> {
  return apiFetch<MaintainAnalysis>('/api/seasonal/analysis/maintain')
}

export function getAnalysisPromote(): Promise<PromoteAnalysis> {
  return apiFetch<PromoteAnalysis>('/api/seasonal/analysis/promote')
}
```

- [ ] **Step 2: Riscrivi completamente `frontend/src/pages/Stagione.tsx`**

```tsx
// frontend/src/pages/Stagione.tsx
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { LineChart, Line, XAxis, YAxis, Tooltip, ReferenceLine, ResponsiveContainer } from 'recharts'
import {
  getSeasonalCurrent, getSeasonalHistory, saveSeasonalObjective,
  getSeasonalStatus, getAnalysisYouth, getAnalysisMaintain, getAnalysisPromote,
  type SeasonalObjective,
} from '../api/seasonal'
import { getLatestLeague } from '../api/matches'
import { useState, useEffect } from 'react'

type Strategy = 'promote' | 'maintain' | 'youth'

const STRATEGY_META: Record<Strategy, { label: string; color: string; icon: string }> = {
  promote:  { label: 'Promozione',        color: '#f59e0b', icon: '🏆' },
  maintain: { label: 'Mantenimento',      color: '#3b82f6', icon: '🛡️' },
  youth:    { label: 'Sviluppo Giovani',  color: '#10b981', icon: '🌱' },
}

const STATUS_STYLE: Record<string, { bg: string; text: string; label: string }> = {
  on_track: { bg: '#d1fae5', text: '#065f46', label: 'In linea ✓' },
  at_risk:  { bg: '#fef3c7', text: '#92400e', label: 'A rischio ⚠' },
  off_track:{ bg: '#fee2e2', text: '#991b1b', label: 'Fuori strada ✗' },
}

const sec: React.CSSProperties = {
  background: '#fff', borderRadius: 8, padding: 20, marginBottom: 16,
  boxShadow: '0 1px 3px rgba(0,0,0,.08)',
}

const LINE_IT: Record<string, string> = {
  goalkeeper: 'Portiere', defense: 'Difesa', midfield: 'Centrocampo', attack: 'Attacco',
}

const SKILL_LABELS: Record<string, string> = {
  goalkeeper: 'Parate', defending: 'Difesa', playmaking: 'Regia',
  scoring: 'Attacco', passing: 'Passaggi', winger: 'Cross',
}

export function Stagione() {
  const qc = useQueryClient()
  const currentQ  = useQuery({ queryKey: ['seasonal-current'], queryFn: getSeasonalCurrent })
  const historyQ  = useQuery({ queryKey: ['seasonal-history'], queryFn: getSeasonalHistory })
  const latestQ   = useQuery({ queryKey: ['latest-league'],   queryFn: getLatestLeague })
  const statusQ   = useQuery({ queryKey: ['seasonal-status'], queryFn: getSeasonalStatus })

  const obj = currentQ.data?.objective
  const [strategy, setStrategy] = useState<Strategy>('maintain')

  useEffect(() => {
    if (!currentQ.isFetched || !latestQ.isFetched) return
    const hrf = latestQ.data
    if (obj && (!hrf || obj.season === hrf.season)) {
      setStrategy(obj.strategy as Strategy)
    }
  }, [currentQ.isFetched, latestQ.isFetched, obj, latestQ.data])

  const saveMut = useMutation({
    mutationFn: (s: Strategy) => saveSeasonalObjective({
      season: latestQ.data?.season ?? obj?.season ?? 0,
      league_position: latestQ.data?.league_position ?? obj?.league_position ?? 0,
      league_points: latestQ.data?.league_points ?? obj?.league_points ?? 0,
      league_series: latestQ.data?.league_series ?? obj?.league_series ?? '',
      budget_manual: obj?.budget_manual ?? 0,
      strategy: s,
      notes: obj?.notes ?? '',
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['seasonal-current'] })
      qc.invalidateQueries({ queryKey: ['seasonal-status'] })
    },
  })

  const handleStrategyChange = (s: Strategy) => {
    setStrategy(s)
    saveMut.mutate(s)
  }

  const status = statusQ.data
  const statusStyle = STATUS_STYLE[status?.status ?? 'on_track']

  // Build chart data: history points + projected target line
  const chartData = (status?.history ?? []).map(h => ({
    round: h.matchround,
    punti: h.points,
    obiettivo: strategy === 'promote' ? Math.round((26 / 14) * h.matchround)
             : strategy === 'maintain' ? Math.round((16 / 14) * h.matchround)
             : undefined,
  }))

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 20 }}>Stagione</h2>

      {/* ZONA 1: Selezione obiettivo */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 16 }}>
        {(Object.entries(STRATEGY_META) as [Strategy, typeof STRATEGY_META[Strategy]][]).map(([key, meta]) => {
          const active = strategy === key
          const isStatus = active && status
          const ss = isStatus ? STATUS_STYLE[status.status] : null
          return (
            <button key={key} onClick={() => handleStrategyChange(key)}
              style={{
                padding: 16, borderRadius: 10, cursor: 'pointer', textAlign: 'left',
                border: `2px solid ${active ? meta.color : '#e5e7eb'}`,
                background: active ? '#fafafa' : '#fff',
                boxShadow: active ? `0 0 0 3px ${meta.color}22` : 'none',
              }}>
              <div style={{ fontSize: 22, marginBottom: 4 }}>{meta.icon}</div>
              <div style={{ fontWeight: 700, fontSize: 14, color: active ? meta.color : '#374151' }}>
                {meta.label}
              </div>
              {isStatus && ss && (
                <div style={{ marginTop: 6, fontSize: 11, background: ss.bg,
                  color: ss.text, borderRadius: 4, padding: '2px 6px', display: 'inline-block' }}>
                  {ss.label}
                </div>
              )}
            </button>
          )
        })}
      </div>

      {/* ZONA 2: Grafico andamento */}
      {status && status.played > 0 && (
        <div style={sec}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
            <div>
              <h3 style={{ margin: 0, fontSize: 15 }}>Andamento stagionale</h3>
              <p style={{ margin: '4px 0 0', fontSize: 13, color: '#6b7280' }}>
                Giornata {status.played}/14 · {status.current_position}° posto · {status.current_points} pt
                · Proiezione finale: <strong>{status.projected_points.toFixed(0)} pt</strong>
              </p>
            </div>
            <div style={{ ...STATUS_STYLE[status.status], padding: '4px 10px', borderRadius: 6, fontSize: 12, fontWeight: 600,
              background: STATUS_STYLE[status.status].bg, color: STATUS_STYLE[status.status].text }}>
              {STATUS_STYLE[status.status].label}
            </div>
          </div>

          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={chartData} margin={{ top: 4, right: 12, bottom: 4, left: 0 }}>
              <XAxis dataKey="round" label={{ value: 'Giornata', position: 'insideBottom', offset: -2, fontSize: 11 }}
                tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} domain={[0, 42]} />
              <Tooltip formatter={(v: number, name: string) =>
                [v, name === 'punti' ? 'Punti reali' : 'Obiettivo']} />
              <Line type="monotone" dataKey="punti" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3 }} />
              {strategy !== 'youth' && (
                <Line type="monotone" dataKey="obiettivo" stroke="#d1d5db"
                  strokeDasharray="4 4" dot={false} strokeWidth={1.5} />
              )}
            </LineChart>
          </ResponsiveContainer>

          {/* Banner cambio strategia */}
          {status.suggested_strategy && (
            <div style={{ marginTop: 12, background: '#fff7ed', border: '1px solid #fed7aa',
              borderRadius: 6, padding: '10px 14px', fontSize: 13, color: '#9a3412' }}>
              ⚠ {status.message}
              {' '}
              <button onClick={() => handleStrategyChange(status.suggested_strategy as Strategy)}
                style={{ background: '#ea580c', color: '#fff', border: 'none', borderRadius: 4,
                  padding: '3px 10px', cursor: 'pointer', fontSize: 12, marginLeft: 8 }}>
                Passa a {STRATEGY_META[status.suggested_strategy as Strategy]?.label}
              </button>
            </div>
          )}
          {!status.suggested_strategy && (
            <p style={{ margin: '10px 0 0', fontSize: 13, color: '#6b7280' }}>{status.message}</p>
          )}
        </div>
      )}

      {/* ZONA 3: Analisi per obiettivo */}
      {strategy === 'youth'    && <YouthSection />}
      {strategy === 'maintain' && <MaintainSection />}
      {strategy === 'promote'  && <PromoteSection />}

      {/* Storico stagioni */}
      <PreviousSeasonsTable historyQ={historyQ} />
    </div>
  )
}

function YouthSection() {
  const q = useQuery({ queryKey: ['analysis-youth'], queryFn: getAnalysisYouth })
  if (q.isLoading) return <div style={{ textAlign: 'center', padding: 32, color: '#9ca3af' }}>Caricamento...</div>
  const players = q.data ?? []
  if (players.length === 0) return (
    <div style={{ ...sec, color: '#6b7280', textAlign: 'center' }}>
      Nessun giocatore under-24 in rosa.
    </div>
  )
  return (
    <div style={sec}>
      <h3 style={{ margin: '0 0 16px', fontSize: 15 }}>Giovani da valorizzare (under-24)</h3>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
            {['Giocatore', 'Età', 'Skill principale', 'Potenziale', 'Progressi'].map(h => (
              <th key={h} style={{ textAlign: 'left', padding: '6px 8px', color: '#6b7280', fontWeight: 600 }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {players.map((p, i) => (
            <tr key={p.player_id} style={{ borderBottom: '1px solid #f3f4f6',
              background: i === 0 ? '#f0fdf4' : undefined }}>
              <td style={{ padding: '8px', fontWeight: 600 }}>{p.name}</td>
              <td style={{ padding: '8px', color: '#6b7280' }}>{p.age} anni</td>
              <td style={{ padding: '8px' }}>
                <span style={{ fontWeight: 600 }}>{SKILL_LABELS[p.primary_skill] ?? p.primary_skill}</span>
                {' '}<span style={{ color: '#6b7280', fontSize: 12 }}>({p.primary_skill_label})</span>
              </td>
              <td style={{ padding: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <div style={{ width: 60, height: 6, background: '#e5e7eb', borderRadius: 3, overflow: 'hidden' }}>
                    <div style={{ width: `${(p.potential_score / 20) * 100}%`, height: '100%', background: '#10b981', borderRadius: 3 }} />
                  </div>
                  <span style={{ fontSize: 12, color: '#6b7280' }}>{p.potential_score.toFixed(1)}</span>
                </div>
              </td>
              <td style={{ padding: '8px' }}>
                {p.skill_delta > 0
                  ? <span style={{ color: '#059669', fontWeight: 600 }}>+{p.skill_delta} ↑</span>
                  : <span style={{ color: '#9ca3af' }}>—</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function MaintainSection() {
  const q = useQuery({ queryKey: ['analysis-maintain'], queryFn: getAnalysisMaintain })
  if (q.isLoading) return <div style={{ textAlign: 'center', padding: 32, color: '#9ca3af' }}>Caricamento...</div>
  const d = q.data
  if (!d || 'error' in d) return <div style={{ ...sec, color: '#dc2626' }}>{(d as any)?.error ?? 'Errore analisi'}</div>
  return (
    <div style={sec}>
      <h3 style={{ margin: '0 0 12px', fontSize: 15 }}>Analisi rosa — Mantenimento</h3>
      <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
        <div style={{ background: '#eff6ff', borderRadius: 8, padding: '10px 16px' }}>
          <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 2 }}>Schema consigliato</div>
          <div style={{ fontWeight: 700, fontSize: 18, color: '#1d4ed8' }}>{d.best_formation}</div>
        </div>
        <div style={{ background: '#fff1f2', borderRadius: 8, padding: '10px 16px' }}>
          <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 2 }}>Reparto più debole</div>
          <div style={{ fontWeight: 700, fontSize: 18, color: '#dc2626' }}>{d.weakest_sector_label}</div>
          <div style={{ fontSize: 12, color: '#9ca3af' }}>rating {d.weakest_rating.toFixed(1)}</div>
        </div>
      </div>

      <div style={{ display: 'grid', gap: 8 }}>
        {(['goalkeeper', 'defense', 'midfield', 'attack'] as const).map(line => {
          const val = d.line_ratings[line] ?? 0
          const isWeak = line === d.weakest_sector
          return (
            <div key={line}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 3 }}>
                <span style={{ color: isWeak ? '#dc2626' : '#374151', fontWeight: isWeak ? 600 : 400 }}>
                  {LINE_IT[line]}
                </span>
                <span style={{ color: '#6b7280' }}>{val.toFixed(1)}</span>
              </div>
              <div style={{ height: 6, background: '#e5e7eb', borderRadius: 3, overflow: 'hidden' }}>
                <div style={{ width: `${(val / 12) * 100}%`, height: '100%', borderRadius: 3,
                  background: isWeak ? '#dc2626' : '#3b82f6' }} />
              </div>
            </div>
          )
        })}
      </div>
      <p style={{ margin: '12px 0 0', fontSize: 13, color: '#374151' }}>{d.message}</p>
    </div>
  )
}

function PromoteSection() {
  const q = useQuery({ queryKey: ['analysis-promote'], queryFn: getAnalysisPromote })
  if (q.isLoading) return <div style={{ textAlign: 'center', padding: 32, color: '#9ca3af' }}>Caricamento...</div>
  const d = q.data
  if (!d || 'error' in d) return <div style={{ ...sec, color: '#dc2626' }}>{(d as any)?.error ?? 'Errore analisi'}</div>

  return (
    <div>
      <div style={sec}>
        <h3 style={{ margin: '0 0 4px', fontSize: 15 }}>Analisi promozione</h3>
        <p style={{ margin: '0 0 16px', fontSize: 13, color: '#6b7280' }}>
          Schema consigliato: <strong>{d.best_formation}</strong>
        </p>
        {d.rival_avg ? (
          <div style={{ display: 'grid', gap: 10 }}>
            {(['goalkeeper', 'defense', 'midfield', 'attack'] as const).map(line => {
              const mine = d.my_ratings[line] ?? 0
              const rival = d.rival_avg![line] ?? 0
              const gap = d.gaps[line] ?? 0
              return (
                <div key={line}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 4 }}>
                    <span style={{ color: '#374151' }}>{LINE_IT[line]}</span>
                    <span>
                      <span style={{ fontWeight: 600, color: gap >= 0 ? '#059669' : '#dc2626' }}>
                        {mine.toFixed(1)}
                      </span>
                      <span style={{ color: '#9ca3af', margin: '0 6px' }}>vs</span>
                      <span style={{ color: '#6b7280' }}>{rival.toFixed(1)}</span>
                      <span style={{ marginLeft: 8, fontSize: 12,
                        color: gap >= 0 ? '#059669' : '#dc2626' }}>
                        {gap >= 0 ? `+${gap.toFixed(1)}` : gap.toFixed(1)}
                      </span>
                    </span>
                  </div>
                  <div style={{ height: 6, background: '#e5e7eb', borderRadius: 3, position: 'relative', overflow: 'hidden' }}>
                    <div style={{ width: `${(mine / 12) * 100}%`, height: '100%', background: gap >= 0 ? '#3b82f6' : '#ef4444', borderRadius: 3 }} />
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <p style={{ color: '#9ca3af', fontSize: 13 }}>{d.message}</p>
        )}
      </div>

      {d.needed_skills.length > 0 && (
        <div style={sec}>
          <h3 style={{ margin: '0 0 12px', fontSize: 15 }}>Rinforzi necessari</h3>
          {d.needed_skills.map(ns => (
            <div key={ns.sector} style={{ display: 'flex', justifyContent: 'space-between',
              alignItems: 'center', padding: '8px 0', borderBottom: '1px solid #f3f4f6' }}>
              <span style={{ fontWeight: 600, fontSize: 13 }}>{ns.sector_label}</span>
              <span style={{ fontSize: 13, color: '#6b7280' }}>
                gap <span style={{ color: '#dc2626' }}>{ns.gap.toFixed(1)}</span> — cerca almeno{' '}
                <strong>{ns.min_skill_label}</strong> ({ns.min_skill_value})
              </span>
            </div>
          ))}
        </div>
      )}

      {d.sell_candidates.length > 0 && (
        <div style={sec}>
          <h3 style={{ margin: '0 0 12px', fontSize: 15 }}>Possibili cessioni</h3>
          {d.sell_candidates.map(p => (
            <div key={p.player_id} style={{ display: 'flex', justifyContent: 'space-between',
              alignItems: 'center', padding: '6px 0', borderBottom: '1px solid #f3f4f6', fontSize: 13 }}>
              <span style={{ fontWeight: 600 }}>{p.name}</span>
              <span style={{ color: '#6b7280' }}>
                {p.age} anni · €{p.salary.toLocaleString()} · contributo {p.contribution.toFixed(1)}
              </span>
            </div>
          ))}
        </div>
      )}

      {d.rival_avg && (
        <p style={{ fontSize: 13, color: '#374151', padding: '0 4px' }}>{d.message}</p>
      )}
    </div>
  )
}

function PreviousSeasonsTable({ historyQ }: { historyQ: any }) {
  const history = historyQ.data?.history ?? []
  if (history.length <= 1) return null
  const STRATEGY_LABELS: Record<string, string> = {
    promote: 'Promozione', maintain: 'Mantenimento', youth: 'Sviluppo giovani',
  }
  return (
    <div style={{ ...sec, marginTop: 8 }}>
      <h3 style={{ margin: '0 0 16px', fontSize: 15 }}>Stagioni precedenti</h3>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
            {['Stagione', 'Pos.', 'Punti', 'Serie', 'Obiettivo'].map(h => (
              <th key={h} style={{ textAlign: 'left', padding: '6px 8px', color: '#6b7280' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {history.slice(1).map((r: SeasonalObjective) => (
            <tr key={r.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
              <td style={{ padding: '6px 8px', fontWeight: 600 }}>{r.season}</td>
              <td style={{ padding: '6px 8px' }}>{r.league_position}</td>
              <td style={{ padding: '6px 8px' }}>{r.league_points}</td>
              <td style={{ padding: '6px 8px' }}>{r.league_series}</td>
              <td style={{ padding: '6px 8px' }}>{STRATEGY_LABELS[r.strategy] ?? r.strategy}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

- [ ] **Step 3: Build check**

```bash
cd frontend && npm run build 2>&1 | tail -10
```

Atteso: `✓ built in Xs` senza errori TypeScript.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/seasonal.ts frontend/src/pages/Stagione.tsx
git commit -m "feat: rewrite Stagione as live season dashboard with 3 strategy modes"
```

---

## Verifica finale

- [ ] **Suite backend completa**

```bash
cd backend && pytest -v 2>&1 | tail -10
```

Atteso: tutti `PASSED` (110+ test).

- [ ] **Build frontend pulita**

```bash
cd frontend && npm run build 2>&1 | grep -E "built|error"
```

Atteso: `✓ built in Xs`

- [ ] **Commit di chiusura**

```bash
git add -A
git commit -m "chore: final integration — Stagione dashboard + Girone rivals complete"
```
