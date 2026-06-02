# Hattrick Dashboard — Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working Hattrick Dashboard with FastAPI backend (CHPP OAuth 1.0a sync, SQLite) e React frontend (squad view, settings, dashboard KPI).

**Architecture:** FastAPI espone un'API REST su SQLite via SQLAlchemy 2.x; il client CHPP recupera XML da hattrick.org con OAuth 1.0a (requests-oauthlib) e lo fa parsare con lxml prima di fare upsert sul DB. Il frontend React (Vite + TS) usa TanStack Query per il fetching e TanStack Table per la vista rosa.

**Tech Stack:** Python 3.11, FastAPI 0.115, SQLAlchemy 2.x, SQLite, requests-oauthlib, lxml, pytest, httpx; React 18, Vite 5, TypeScript 5, react-router-dom 6, @tanstack/react-query 5, @tanstack/react-table 8

---

## File Structure

### Backend
| File | Responsabilità |
|---|---|
| `backend/requirements.txt` | Dipendenze Python |
| `backend/pytest.ini` | Configurazione pytest (pythonpath, testpaths) |
| `backend/app/main.py` | App FastAPI, CORS, registrazione router, `create_all` |
| `backend/app/database.py` | Engine SQLAlchemy, `SessionLocal`, `Base`, `get_db` |
| `backend/app/models/settings.py` | `CHPPSettings` (token OAuth 1.0a) |
| `backend/app/models/player.py` | `Player` (skills, meta) |
| `backend/app/models/sync_log.py` | `SyncLog` (entity, last_sync_at, status) |
| `backend/app/chpp/client.py` | `CHPPClient`: OAuth1Session wrapper, `fetch(file, params)` |
| `backend/app/chpp/parsers/squad.py` | `parse_squad(xml_bytes)` → `list[dict]` |
| `backend/app/api/settings.py` | Router `GET/POST /api/settings` |
| `backend/app/api/squad.py` | Router `GET /api/squad` |
| `backend/app/api/sync.py` | Router `POST /api/sync/{entity}`, `GET /api/sync/status` |
| `backend/tests/conftest.py` | Fixture pytest: DB in-memory, TestClient |
| `backend/tests/fixtures/squad.xml` | XML CHPP realistico per test parser |
| `backend/tests/test_chpp_parser.py` | Unit test parser XML |
| `backend/tests/test_api_settings.py` | Test API settings |
| `backend/tests/test_api_squad.py` | Test API squad |
| `backend/tests/test_api_sync.py` | Test API sync |

### Frontend
| File | Responsabilità |
|---|---|
| `frontend/package.json` | Dipendenze Node |
| `frontend/vite.config.ts` | Config Vite + proxy `/api` → backend |
| `frontend/src/main.tsx` | Entry: `QueryClientProvider` + `RouterProvider` |
| `frontend/src/App.tsx` | Definizione router + layout nav |
| `frontend/src/api/client.ts` | Wrapper fetch base, gestione errori |
| `frontend/src/api/squad.ts` | `getSquad()` → `Player[]`, interfaccia `Player` |
| `frontend/src/api/settings.ts` | `getSettings()`, `saveSettings()`, interfacce |
| `frontend/src/api/sync.ts` | `triggerSync()`, `getSyncStatus()` |
| `frontend/src/components/SkillBar.tsx` | Barra visuale 0-20 per una skill |
| `frontend/src/components/SyncButton.tsx` | Bottone con loading state + timestamp |
| `frontend/src/pages/Settings.tsx` | Form inserimento token CHPP |
| `frontend/src/pages/Squad.tsx` | TanStack Table rosa + SkillBar |
| `frontend/src/pages/Dashboard.tsx` | KPI: n° giocatori, forma media, miglior attaccante |

### Root
| File | Responsabilità |
|---|---|
| `Makefile` | Target `install`, `dev`, `test` |
| `.gitignore` | Python, Node, SQLite |

---

## Task 1: Repository scaffolding

**Files:**
- Create: `.gitignore`
- Create: `Makefile`
- Create: `backend/` (directory structure)
- Create: `frontend/` (directory placeholder)

- [ ] **Step 1: Crea struttura directory backend**

```bash
mkdir -p backend/app/api
mkdir -p backend/app/chpp/parsers
mkdir -p backend/app/models
mkdir -p backend/tests/fixtures
mkdir -p backend/data
touch backend/app/__init__.py
touch backend/app/api/__init__.py
touch backend/app/chpp/__init__.py
touch backend/app/chpp/parsers/__init__.py
touch backend/app/models/__init__.py
touch backend/tests/__init__.py
```

- [ ] **Step 2: Crea `.gitignore`**

```
# Python
__pycache__/
*.pyc
*.pyo
.venv/
venv/
*.egg-info/

# SQLite
backend/data/
*.db
*.sqlite3

# Node
frontend/node_modules/
frontend/dist/

# Env
.env
.env.local
```

- [ ] **Step 3: Crea `Makefile`**

```makefile
.PHONY: install dev test backend frontend

install:
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

dev:
	$(MAKE) -j2 backend frontend

backend:
	cd backend && uvicorn app.main:app --reload --port 8765

frontend:
	cd frontend && npm run dev

test:
	cd backend && pytest -v
```

- [ ] **Step 4: Commit**

```bash
git add .gitignore Makefile backend/
git commit -m "chore: repository scaffolding — directory structure, Makefile, gitignore"
```

---

## Task 2: Backend — dipendenze e scheletro app

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/pytest.ini`
- Create: `backend/app/database.py`
- Create: `backend/app/main.py`

- [ ] **Step 1: Crea `backend/requirements.txt`**

```
fastapi==0.115.5
uvicorn[standard]==0.32.1
sqlalchemy==2.0.36
requests-oauthlib==2.0.0
lxml==5.3.0
pytest==8.3.3
httpx==0.27.2
```

- [ ] **Step 2: Installa le dipendenze**

```bash
cd backend && pip install -r requirements.txt
```

Expected: nessun errore.

- [ ] **Step 3: Crea `backend/pytest.ini`**

```ini
[pytest]
testpaths = tests
pythonpath = .
```

- [ ] **Step 4: Crea `backend/app/database.py`**

```python
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DB_DIR = Path(__file__).parent.parent / "data"
DB_DIR.mkdir(exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_DIR / 'hattrick.db'}")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 5: Crea `backend/app/main.py` (scheletro — router aggiunti in Task 10)**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Hattrick Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- [ ] **Step 6: Verifica che l'app si avvii**

```bash
cd backend && uvicorn app.main:app --port 8765
```

Expected: `Application startup complete.` — poi Ctrl+C.

- [ ] **Step 7: Commit**

```bash
git add backend/requirements.txt backend/pytest.ini backend/app/database.py backend/app/main.py
git commit -m "feat: backend skeleton — FastAPI app, SQLAlchemy engine, CORS"
```

---

## Task 3: SQLAlchemy models

**Files:**
- Create: `backend/app/models/settings.py`
- Create: `backend/app/models/player.py`
- Create: `backend/app/models/sync_log.py`

- [ ] **Step 1: Crea `backend/app/models/settings.py`**

```python
from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class CHPPSettings(Base):
    __tablename__ = "chpp_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    consumer_key: Mapped[str] = mapped_column(String, nullable=False)
    consumer_secret: Mapped[str] = mapped_column(String, nullable=False)
    access_token: Mapped[str] = mapped_column(String, nullable=False)
    access_token_secret: Mapped[str] = mapped_column(String, nullable=False)
```

- [ ] **Step 2: Crea `backend/app/models/player.py`**

```python
from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # CHPP PlayerID
    first_name: Mapped[str] = mapped_column(String, default="")
    last_name: Mapped[str] = mapped_column(String, default="")
    age: Mapped[int] = mapped_column(Integer, default=0)
    age_days: Mapped[int] = mapped_column(Integer, default=0)
    tsi: Mapped[int] = mapped_column(Integer, default=0)
    form: Mapped[int] = mapped_column(Integer, default=0)
    stamina: Mapped[int] = mapped_column(Integer, default=0)
    injury_days: Mapped[int] = mapped_column(Integer, default=-1)  # -1 = sano, >0 = settimane out
    salary: Mapped[int] = mapped_column(Integer, default=0)
    goalkeeper: Mapped[int] = mapped_column(Integer, default=0)
    defending: Mapped[int] = mapped_column(Integer, default=0)
    playmaking: Mapped[int] = mapped_column(Integer, default=0)
    winger: Mapped[int] = mapped_column(Integer, default=0)
    passing: Mapped[int] = mapped_column(Integer, default=0)
    scoring: Mapped[int] = mapped_column(Integer, default=0)
    set_pieces: Mapped[int] = mapped_column(Integer, default=0)
```

- [ ] **Step 3: Crea `backend/app/models/sync_log.py`**

```python
from datetime import datetime
from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class SyncLog(Base):
    __tablename__ = "sync_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String, default="ok")
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/
git commit -m "feat: SQLAlchemy models — CHPPSettings, Player, SyncLog"
```

---

## Task 4: XML fixture CHPP

**Files:**
- Create: `backend/tests/fixtures/squad.xml`

- [ ] **Step 1: Crea `backend/tests/fixtures/squad.xml`**

Questo file simula la risposta CHPP per `file=players`. Usato solo nei test, mai in produzione.

```xml
<?xml version="1.0" encoding="utf-8"?>
<HattrickData>
  <Version>2.7</Version>
  <UserID>123456</UserID>
  <Fetcheddate>2026-05-17 10:00:00</Fetcheddate>
  <IsYouthTeam>False</IsYouthTeam>
  <IsPlayingMatch>False</IsPlayingMatch>
  <Team>
    <TeamID>654321</TeamID>
    <TeamName>My Team FC</TeamName>
    <Players>
      <Player>
        <PlayerID>1000001</PlayerID>
        <FirstName>John</FirstName>
        <LastName>Doe</LastName>
        <Age>25</Age>
        <AgeDays>100</AgeDays>
        <TSI>4200</TSI>
        <PlayerForm>7</PlayerForm>
        <InjuryLevel>-1</InjuryLevel>
        <Salary>7800</Salary>
        <Stamina>8</Stamina>
        <Goalkeeper>5</Goalkeeper>
        <Defending>6</Defending>
        <Playmaking>8</Playmaking>
        <Winger>4</Winger>
        <Passing>7</Passing>
        <Scoring>9</Scoring>
        <SetPieces>3</SetPieces>
      </Player>
      <Player>
        <PlayerID>1000002</PlayerID>
        <FirstName>Marco</FirstName>
        <LastName>Rossi</LastName>
        <Age>28</Age>
        <AgeDays>50</AgeDays>
        <TSI>6800</TSI>
        <PlayerForm>5</PlayerForm>
        <InjuryLevel>2</InjuryLevel>
        <Salary>11200</Salary>
        <Stamina>6</Stamina>
        <Goalkeeper>2</Goalkeeper>
        <Defending>10</Defending>
        <Playmaking>7</Playmaking>
        <Winger>3</Winger>
        <Passing>8</Passing>
        <Scoring>4</Scoring>
        <SetPieces>5</SetPieces>
      </Player>
    </Players>
  </Team>
</HattrickData>
```

- [ ] **Step 2: Commit**

```bash
git add backend/tests/fixtures/squad.xml
git commit -m "test: add CHPP squad XML fixture for parser tests"
```

---

## Task 5: Parser XML squad (TDD)

**Files:**
- Create: `backend/tests/test_chpp_parser.py`
- Create: `backend/app/chpp/parsers/squad.py`

- [ ] **Step 1: Scrivi il test fallente**

```python
# backend/tests/test_chpp_parser.py
from pathlib import Path
from app.chpp.parsers.squad import parse_squad

FIXTURE = (Path(__file__).parent / "fixtures" / "squad.xml").read_bytes()


def test_parse_squad_returns_two_players():
    result = parse_squad(FIXTURE)
    assert len(result) == 2


def test_parse_squad_first_player_fields():
    result = parse_squad(FIXTURE)
    p = result[0]
    assert p["id"] == 1000001
    assert p["first_name"] == "John"
    assert p["last_name"] == "Doe"
    assert p["age"] == 25
    assert p["age_days"] == 100
    assert p["tsi"] == 4200
    assert p["form"] == 7
    assert p["injury_days"] == -1
    assert p["salary"] == 7800
    assert p["stamina"] == 8
    assert p["goalkeeper"] == 5
    assert p["defending"] == 6
    assert p["playmaking"] == 8
    assert p["winger"] == 4
    assert p["passing"] == 7
    assert p["scoring"] == 9
    assert p["set_pieces"] == 3


def test_parse_squad_injured_player():
    result = parse_squad(FIXTURE)
    p = result[1]
    assert p["id"] == 1000002
    assert p["first_name"] == "Marco"
    assert p["injury_days"] == 2
    assert p["defending"] == 10
```

- [ ] **Step 2: Esegui — verifica che fallisca**

```bash
cd backend && pytest tests/test_chpp_parser.py -v
```

Expected: `ImportError` o `ModuleNotFoundError` (parser non ancora implementato).

- [ ] **Step 3: Implementa `backend/app/chpp/parsers/squad.py`**

```python
from lxml import etree


def parse_squad(xml_bytes: bytes) -> list[dict]:
    root = etree.fromstring(xml_bytes)
    players = []
    for p in root.findall(".//Player"):
        players.append({
            "id": int(p.findtext("PlayerID", "0")),
            "first_name": p.findtext("FirstName", ""),
            "last_name": p.findtext("LastName", ""),
            "age": int(p.findtext("Age", "0")),
            "age_days": int(p.findtext("AgeDays", "0")),
            "tsi": int(p.findtext("TSI", "0")),
            "form": int(p.findtext("PlayerForm", "0")),
            "injury_days": int(p.findtext("InjuryLevel", "-1")),
            "salary": int(p.findtext("Salary", "0")),
            "stamina": int(p.findtext("Stamina", "0")),
            "goalkeeper": int(p.findtext("Goalkeeper", "0")),
            "defending": int(p.findtext("Defending", "0")),
            "playmaking": int(p.findtext("Playmaking", "0")),
            "winger": int(p.findtext("Winger", "0")),
            "passing": int(p.findtext("Passing", "0")),
            "scoring": int(p.findtext("Scoring", "0")),
            "set_pieces": int(p.findtext("SetPieces", "0")),
        })
    return players
```

- [ ] **Step 4: Esegui — verifica che passi**

```bash
cd backend && pytest tests/test_chpp_parser.py -v
```

Expected: `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/chpp/parsers/squad.py backend/tests/test_chpp_parser.py
git commit -m "feat: CHPP squad XML parser with unit tests"
```

---

## Task 6: CHPP client

**Files:**
- Create: `backend/app/chpp/client.py`

Questo modulo non ha test unitari propri: viene mockato nei test di sync (Task 9). Il suo corretto funzionamento viene verificato in produzione al primo sync manuale.

- [ ] **Step 1: Implementa `backend/app/chpp/client.py`**

```python
from requests_oauthlib import OAuth1Session

CHPP_URL = "https://chpp.hattrick.org/chppxml.ashx"


class CHPPClient:
    def __init__(
        self,
        consumer_key: str,
        consumer_secret: str,
        access_token: str,
        access_token_secret: str,
    ) -> None:
        self._session = OAuth1Session(
            consumer_key,
            client_secret=consumer_secret,
            resource_owner_key=access_token,
            resource_owner_secret=access_token_secret,
        )

    def fetch(self, file: str, params: dict | None = None) -> bytes:
        p = {"file": file, "version": "2.7"}
        if params:
            p.update(params)
        response = self._session.get(CHPP_URL, params=p)
        response.raise_for_status()
        return response.content
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/chpp/client.py
git commit -m "feat: CHPP OAuth 1.0a client"
```

---

## Task 7: Conftest pytest

**Files:**
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: Crea `backend/tests/conftest.py`**

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

- [ ] **Step 2: Commit**

```bash
git add backend/tests/conftest.py
git commit -m "test: pytest conftest — in-memory SQLite, TestClient fixture"
```

---

## Task 8: Settings API (TDD)

**Files:**
- Create: `backend/tests/test_api_settings.py`
- Create: `backend/app/api/settings.py`

- [ ] **Step 1: Scrivi il test fallente**

```python
# backend/tests/test_api_settings.py


def test_get_settings_unconfigured(client):
    response = client.get("/api/settings")
    assert response.status_code == 200
    assert response.json()["configured"] is False


def test_post_settings_saves(client):
    payload = {
        "consumer_key": "ck",
        "consumer_secret": "cs",
        "access_token": "at",
        "access_token_secret": "ats",
    }
    response = client.post("/api/settings", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "saved"


def test_get_settings_after_save(client):
    client.post(
        "/api/settings",
        json={"consumer_key": "ck", "consumer_secret": "cs", "access_token": "at", "access_token_secret": "ats"},
    )
    response = client.get("/api/settings")
    data = response.json()
    assert data["configured"] is True
    assert data["consumer_key"] == "ck"
    assert data["access_token"] == "at"
    assert "consumer_secret" not in data
    assert "access_token_secret" not in data


def test_post_settings_overwrites(client):
    client.post(
        "/api/settings",
        json={"consumer_key": "ck1", "consumer_secret": "cs1", "access_token": "at1", "access_token_secret": "ats1"},
    )
    client.post(
        "/api/settings",
        json={"consumer_key": "ck2", "consumer_secret": "cs2", "access_token": "at2", "access_token_secret": "ats2"},
    )
    response = client.get("/api/settings")
    assert response.json()["consumer_key"] == "ck2"
```

- [ ] **Step 2: Esegui — verifica che fallisca**

```bash
cd backend && pytest tests/test_api_settings.py -v
```

Expected: `404 Not Found` (route non esistente).

- [ ] **Step 3: Implementa `backend/app/api/settings.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models.settings import CHPPSettings

router = APIRouter()


class SettingsPayload(BaseModel):
    consumer_key: str
    consumer_secret: str
    access_token: str
    access_token_secret: str


@router.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    s = db.query(CHPPSettings).first()
    if not s:
        return {"configured": False}
    return {
        "configured": True,
        "consumer_key": s.consumer_key,
        "access_token": s.access_token,
    }


@router.post("/settings")
def save_settings(payload: SettingsPayload, db: Session = Depends(get_db)):
    s = db.query(CHPPSettings).first()
    if s:
        s.consumer_key = payload.consumer_key
        s.consumer_secret = payload.consumer_secret
        s.access_token = payload.access_token
        s.access_token_secret = payload.access_token_secret
    else:
        s = CHPPSettings(
            id=1,
            consumer_key=payload.consumer_key,
            consumer_secret=payload.consumer_secret,
            access_token=payload.access_token,
            access_token_secret=payload.access_token_secret,
        )
        db.add(s)
    db.commit()
    return {"status": "saved"}
```

- [ ] **Step 4: Registra il router in `backend/app/main.py`**

Aggiungi dopo le import esistenti:

```python
from app.api import settings as settings_router

# dopo app.add_middleware(...)
app.include_router(settings_router.router, prefix="/api")
```

- [ ] **Step 5: Esegui — verifica che passi**

```bash
cd backend && pytest tests/test_api_settings.py -v
```

Expected: `4 passed`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/settings.py backend/tests/test_api_settings.py backend/app/main.py
git commit -m "feat: settings API (GET/POST /api/settings) with tests"
```

---

## Task 9: Squad API (TDD)

**Files:**
- Create: `backend/tests/test_api_squad.py`
- Create: `backend/app/api/squad.py`

- [ ] **Step 1: Scrivi il test fallente**

```python
# backend/tests/test_api_squad.py
from app.models.player import Player


def test_get_squad_empty(client):
    response = client.get("/api/squad")
    assert response.status_code == 200
    assert response.json() == []


def test_get_squad_returns_players(client, db):
    db.add(
        Player(
            id=1000001,
            first_name="John",
            last_name="Doe",
            age=25,
            age_days=100,
            tsi=4200,
            form=7,
            stamina=8,
            injury_days=-1,
            salary=7800,
            goalkeeper=5,
            defending=6,
            playmaking=8,
            winger=4,
            passing=7,
            scoring=9,
            set_pieces=3,
        )
    )
    db.commit()
    response = client.get("/api/squad")
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == 1000001
    assert data[0]["first_name"] == "John"
    assert data[0]["scoring"] == 9
    assert data[0]["injury_days"] == -1
```

- [ ] **Step 2: Esegui — verifica che fallisca**

```bash
cd backend && pytest tests/test_api_squad.py -v
```

Expected: `404 Not Found`.

- [ ] **Step 3: Implementa `backend/app/api/squad.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.player import Player

router = APIRouter()

PLAYER_FIELDS = [
    "id", "first_name", "last_name", "age", "age_days", "tsi", "form",
    "stamina", "injury_days", "salary", "goalkeeper", "defending",
    "playmaking", "winger", "passing", "scoring", "set_pieces",
]


@router.get("/squad")
def get_squad(db: Session = Depends(get_db)):
    players = db.query(Player).all()
    return [{field: getattr(p, field) for field in PLAYER_FIELDS} for p in players]
```

- [ ] **Step 4: Registra il router in `backend/app/main.py`**

Aggiungi dopo la riga `from app.api import settings as settings_router`:

```python
from app.api import squad as squad_router

# dopo app.include_router(settings_router.router, ...)
app.include_router(squad_router.router, prefix="/api")
```

- [ ] **Step 5: Esegui — verifica che passi**

```bash
cd backend && pytest tests/test_api_squad.py -v
```

Expected: `2 passed`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/squad.py backend/tests/test_api_squad.py backend/app/main.py
git commit -m "feat: squad API (GET /api/squad) with tests"
```

---

## Task 10: Sync API (TDD)

**Files:**
- Create: `backend/tests/test_api_sync.py`
- Create: `backend/app/api/sync.py`

- [ ] **Step 1: Scrivi il test fallente**

```python
# backend/tests/test_api_sync.py
from pathlib import Path
from unittest.mock import patch
from app.models.settings import CHPPSettings

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
```

- [ ] **Step 2: Esegui — verifica che fallisca**

```bash
cd backend && pytest tests/test_api_sync.py -v
```

Expected: `404 Not Found` o errori di import.

- [ ] **Step 3: Implementa `backend/app/api/sync.py`**

```python
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.settings import CHPPSettings
from app.models.player import Player
from app.models.sync_log import SyncLog
from app.chpp.client import CHPPClient
from app.chpp.parsers.squad import parse_squad

router = APIRouter()

SUPPORTED_ENTITIES = {"squad"}


@router.get("/sync/status")
def sync_status(db: Session = Depends(get_db)):
    logs = db.query(SyncLog).all()
    return {
        log.entity: {
            "last_sync_at": log.last_sync_at.isoformat() if log.last_sync_at else None,
            "status": log.status,
        }
        for log in logs
    }


@router.post("/sync/{entity}")
def trigger_sync(entity: str, db: Session = Depends(get_db)):
    if entity not in SUPPORTED_ENTITIES:
        raise HTTPException(status_code=400, detail=f"Unknown entity: {entity}")

    s = db.query(CHPPSettings).first()
    if not s:
        raise HTTPException(status_code=400, detail="CHPP not configured — go to /settings")

    client = CHPPClient(s.consumer_key, s.consumer_secret, s.access_token, s.access_token_secret)

    if entity == "squad":
        xml_bytes = client.fetch("players")
        for pd in parse_squad(xml_bytes):
            existing = db.get(Player, pd["id"])
            if existing:
                for k, v in pd.items():
                    setattr(existing, k, v)
            else:
                db.add(Player(**pd))

    now = datetime.now(timezone.utc)
    log = db.query(SyncLog).filter_by(entity=entity).first()
    if log:
        log.last_sync_at = now
        log.status = "ok"
    else:
        db.add(SyncLog(entity=entity, last_sync_at=now, status="ok"))

    db.commit()
    return {"status": "ok", "synced_at": now.isoformat()}
```

- [ ] **Step 4: Registra il router in `backend/app/main.py`**

Aggiungi dopo le import esistenti:

```python
from app.api import sync as sync_router

# dopo app.include_router(squad_router.router, ...)
app.include_router(sync_router.router, prefix="/api")
```

- [ ] **Step 5: Esegui tutti i test backend**

```bash
cd backend && pytest -v
```

Expected: `10 passed` (3 parser + 4 settings + 2 squad + 5 sync — conta i tuoi).

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/sync.py backend/tests/test_api_sync.py backend/app/main.py
git commit -m "feat: sync API (POST /api/sync/{entity}, GET /api/sync/status) with tests"
```

---

## Task 11: Frontend — scaffolding

**Files:**
- Create: `frontend/` (via create-vite)
- Modify: `frontend/package.json` (aggiungi dipendenze)
- Create: `frontend/vite.config.ts`

- [ ] **Step 1: Crea progetto Vite**

```bash
npm create vite@latest frontend -- --template react-ts
```

Expected: cartella `frontend/` con `src/App.tsx`, `src/main.tsx`, `vite.config.ts`, `package.json`, `tsconfig.json`.

- [ ] **Step 2: Installa dipendenze base**

```bash
cd frontend && npm install
```

- [ ] **Step 3: Aggiungi le dipendenze di progetto**

```bash
cd frontend && npm install react-router-dom @tanstack/react-query @tanstack/react-table recharts
```

- [ ] **Step 4: Sovrascrivi `frontend/vite.config.ts`**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8765',
    },
  },
})
```

Il proxy elimina il bisogno di VITE_API_URL in dev: tutte le chiamate a `/api/...` vengono inoltrate al backend.

- [ ] **Step 5: Crea struttura cartelle src**

```bash
mkdir -p frontend/src/api
mkdir -p frontend/src/components
mkdir -p frontend/src/pages
```

- [ ] **Step 6: Verifica che Vite si avvii**

```bash
cd frontend && npm run dev
```

Expected: `Local: http://localhost:5173/` — poi Ctrl+C.

- [ ] **Step 7: Commit**

```bash
git add frontend/
git commit -m "chore: frontend scaffolding — Vite + React + TS + routing + query"
```

---

## Task 12: API client TypeScript

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/squad.ts`
- Create: `frontend/src/api/settings.ts`
- Create: `frontend/src/api/sync.ts`

- [ ] **Step 1: Crea `frontend/src/api/client.ts`**

```typescript
export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error((err as { detail?: string }).detail ?? res.statusText)
  }
  return res.json() as Promise<T>
}
```

- [ ] **Step 2: Crea `frontend/src/api/squad.ts`**

```typescript
import { apiFetch } from './client'

export interface Player {
  id: number
  first_name: string
  last_name: string
  age: number
  age_days: number
  tsi: number
  form: number
  stamina: number
  injury_days: number
  salary: number
  goalkeeper: number
  defending: number
  playmaking: number
  winger: number
  passing: number
  scoring: number
  set_pieces: number
}

export function getSquad(): Promise<Player[]> {
  return apiFetch<Player[]>('/api/squad')
}
```

- [ ] **Step 3: Crea `frontend/src/api/settings.ts`**

```typescript
import { apiFetch } from './client'

export interface Settings {
  configured: boolean
  consumer_key?: string
  access_token?: string
}

export interface SettingsPayload {
  consumer_key: string
  consumer_secret: string
  access_token: string
  access_token_secret: string
}

export function getSettings(): Promise<Settings> {
  return apiFetch<Settings>('/api/settings')
}

export function saveSettings(payload: SettingsPayload): Promise<{ status: string }> {
  return apiFetch('/api/settings', { method: 'POST', body: JSON.stringify(payload) })
}
```

- [ ] **Step 4: Crea `frontend/src/api/sync.ts`**

```typescript
import { apiFetch } from './client'

export interface SyncStatusEntry {
  last_sync_at: string | null
  status: string
}

export function triggerSync(entity: string): Promise<{ status: string; synced_at: string }> {
  return apiFetch(`/api/sync/${entity}`, { method: 'POST' })
}

export function getSyncStatus(): Promise<Record<string, SyncStatusEntry>> {
  return apiFetch('/api/sync/status')
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/
git commit -m "feat: TypeScript API client — squad, settings, sync"
```

---

## Task 13: App shell e routing

**Files:**
- Modify: `frontend/src/main.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Sovrascrivi `frontend/src/main.tsx`**

```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 60_000 } },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
)
```

- [ ] **Step 2: Sovrascrivi `frontend/src/App.tsx`**

```tsx
import { createBrowserRouter, RouterProvider, NavLink, Outlet } from 'react-router-dom'
import { Dashboard } from './pages/Dashboard'
import { Squad } from './pages/Squad'
import { Settings } from './pages/Settings'

function Layout() {
  const navStyle = ({ isActive }: { isActive: boolean }): React.CSSProperties => ({
    padding: '8px 16px',
    textDecoration: 'none',
    color: isActive ? '#3b82f6' : '#374151',
    fontWeight: isActive ? 600 : 400,
    borderBottom: isActive ? '2px solid #3b82f6' : '2px solid transparent',
  })

  return (
    <div style={{ minHeight: '100vh', fontFamily: 'system-ui, sans-serif', background: '#f9fafb' }}>
      <nav
        style={{
          display: 'flex',
          gap: 4,
          padding: '0 24px',
          borderBottom: '1px solid #e5e7eb',
          background: '#fff',
        }}
      >
        <NavLink to="/" end style={navStyle}>Dashboard</NavLink>
        <NavLink to="/squad" style={navStyle}>Rosa</NavLink>
        <NavLink to="/settings" style={navStyle}>Impostazioni</NavLink>
      </nav>
      <main style={{ padding: '24px' }}>
        <Outlet />
      </main>
    </div>
  )
}

const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: 'squad', element: <Squad /> },
      { path: 'settings', element: <Settings /> },
    ],
  },
])

export default function App() {
  return <RouterProvider router={router} />
}
```

- [ ] **Step 3: Crea placeholder per le pagine** (le implementiamo nelle task successive)

```bash
echo 'export function Dashboard() { return <p>Dashboard</p> }' > frontend/src/pages/Dashboard.tsx
echo 'export function Squad() { return <p>Rosa</p> }' > frontend/src/pages/Squad.tsx
echo 'export function Settings() { return <p>Settings</p> }' > frontend/src/pages/Settings.tsx
```

- [ ] **Step 4: Avvia il dev server e verifica nel browser**

```bash
# Terminale 1
cd backend && uvicorn app.main:app --reload --port 8765

# Terminale 2
cd frontend && npm run dev
```

Apri `http://localhost:5173` — devi vedere la nav con "Dashboard / Rosa / Impostazioni" e il testo placeholder. Clicca i link e verifica che la navigazione funzioni.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/main.tsx frontend/src/App.tsx frontend/src/pages/
git commit -m "feat: React Router shell — layout, nav, placeholder pages"
```

---

## Task 14: Pagina Settings

**Files:**
- Modify: `frontend/src/pages/Settings.tsx`

- [ ] **Step 1: Implementa `frontend/src/pages/Settings.tsx`**

```tsx
import { useState, useEffect, FormEvent } from 'react'
import { getSettings, saveSettings, SettingsPayload } from '../api/settings'

const FIELDS: Array<{ key: keyof SettingsPayload; label: string; secret: boolean }> = [
  { key: 'consumer_key', label: 'Consumer Key', secret: false },
  { key: 'consumer_secret', label: 'Consumer Secret', secret: true },
  { key: 'access_token', label: 'Access Token', secret: false },
  { key: 'access_token_secret', label: 'Access Token Secret', secret: true },
]

export function Settings() {
  const [form, setForm] = useState<SettingsPayload>({
    consumer_key: '',
    consumer_secret: '',
    access_token: '',
    access_token_secret: '',
  })
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getSettings().then((s) => {
      if (s.configured) {
        setForm((f) => ({
          ...f,
          consumer_key: s.consumer_key ?? '',
          access_token: s.access_token ?? '',
        }))
      }
    })
  }, [])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSaved(false)
    try {
      await saveSettings(form)
      setSaved(true)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Errore sconosciuto')
    }
  }

  return (
    <div style={{ maxWidth: 480 }}>
      <h1 style={{ marginTop: 0 }}>Configurazione CHPP</h1>
      <p style={{ color: '#6b7280', fontSize: 14 }}>
        Inserisci le credenziali ottenute dalla{' '}
        <a href="https://chpp.hattrick.org" target="_blank" rel="noreferrer">
          pagina CHPP di Hattrick
        </a>
        .
      </p>
      <form onSubmit={handleSubmit}>
        {FIELDS.map(({ key, label, secret }) => (
          <div key={key} style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>{label}</label>
            <input
              type={secret ? 'password' : 'text'}
              value={form[key]}
              onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
              style={{
                width: '100%',
                padding: '8px 10px',
                border: '1px solid #d1d5db',
                borderRadius: 6,
                fontSize: 14,
                boxSizing: 'border-box',
              }}
            />
          </div>
        ))}
        <button
          type="submit"
          style={{
            padding: '8px 20px',
            background: '#3b82f6',
            color: '#fff',
            border: 'none',
            borderRadius: 6,
            cursor: 'pointer',
            fontSize: 14,
          }}
        >
          Salva
        </button>
        {saved && (
          <span style={{ marginLeft: 12, color: '#10b981', fontSize: 14 }}>✓ Salvato</span>
        )}
        {error && (
          <span style={{ marginLeft: 12, color: '#ef4444', fontSize: 14 }}>{error}</span>
        )}
      </form>
    </div>
  )
}
```

- [ ] **Step 2: Verifica nel browser**

Con backend e frontend in esecuzione, vai su `http://localhost:5173/settings`. Inserisci valori di test e clicca Salva — devi vedere "✓ Salvato". Ricarica la pagina — consumer_key e access_token devono essere ripopolati.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Settings.tsx
git commit -m "feat: Settings page — CHPP token form"
```

---

## Task 15: Componenti SkillBar e SyncButton

**Files:**
- Create: `frontend/src/components/SkillBar.tsx`
- Create: `frontend/src/components/SyncButton.tsx`

- [ ] **Step 1: Crea `frontend/src/components/SkillBar.tsx`**

```tsx
interface Props {
  value: number
  max?: number
}

export function SkillBar({ value, max = 20 }: Props) {
  const pct = Math.min((value / max) * 100, 100)
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6, minWidth: 80 }}>
      <div
        style={{
          flex: 1,
          height: 6,
          background: '#e5e7eb',
          borderRadius: 3,
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            width: `${pct}%`,
            height: '100%',
            background: '#3b82f6',
            borderRadius: 3,
          }}
        />
      </div>
      <span style={{ minWidth: 18, textAlign: 'right', fontSize: 12, color: '#374151' }}>
        {value}
      </span>
    </div>
  )
}
```

- [ ] **Step 2: Crea `frontend/src/components/SyncButton.tsx`**

```tsx
import { useState } from 'react'
import { triggerSync } from '../api/sync'

interface Props {
  entity: string
  onSynced?: () => void
}

export function SyncButton({ entity, onSynced }: Props) {
  const [loading, setLoading] = useState(false)
  const [syncedAt, setSyncedAt] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function handleSync() {
    setLoading(true)
    setError(null)
    try {
      const result = await triggerSync(entity)
      setSyncedAt(result.synced_at)
      onSynced?.()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Errore')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <button
        onClick={handleSync}
        disabled={loading}
        style={{
          padding: '6px 14px',
          background: loading ? '#93c5fd' : '#3b82f6',
          color: '#fff',
          border: 'none',
          borderRadius: 6,
          cursor: loading ? 'not-allowed' : 'pointer',
          fontSize: 13,
        }}
      >
        {loading ? 'Sincronizzazione…' : 'Sincronizza'}
      </button>
      {syncedAt && (
        <span style={{ fontSize: 12, color: '#6b7280' }}>
          Aggiornato: {new Date(syncedAt).toLocaleString('it-IT')}
        </span>
      )}
      {error && <span style={{ fontSize: 12, color: '#ef4444' }}>{error}</span>}
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/
git commit -m "feat: SkillBar and SyncButton components"
```

---

## Task 16: Pagina Squad

**Files:**
- Modify: `frontend/src/pages/Squad.tsx`

- [ ] **Step 1: Implementa `frontend/src/pages/Squad.tsx`**

```tsx
import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
} from '@tanstack/react-table'
import { getSquad, type Player } from '../api/squad'
import { SkillBar } from '../components/SkillBar'
import { SyncButton } from '../components/SyncButton'

const col = createColumnHelper<Player>()

const columns = [
  col.accessor((p) => `${p.first_name} ${p.last_name}`, {
    id: 'name',
    header: 'Nome',
  }),
  col.accessor('age', { header: 'Età' }),
  col.accessor('form', { header: 'Forma' }),
  col.accessor('tsi', {
    header: 'TSI',
    cell: (info) => info.getValue().toLocaleString('it-IT'),
  }),
  col.accessor('stamina', {
    header: 'Sta.',
    cell: (info) => <SkillBar value={info.getValue()} />,
  }),
  col.accessor('goalkeeper', {
    header: 'Por.',
    cell: (info) => <SkillBar value={info.getValue()} />,
  }),
  col.accessor('defending', {
    header: 'Dif.',
    cell: (info) => <SkillBar value={info.getValue()} />,
  }),
  col.accessor('playmaking', {
    header: 'Cen.',
    cell: (info) => <SkillBar value={info.getValue()} />,
  }),
  col.accessor('winger', {
    header: 'Ala',
    cell: (info) => <SkillBar value={info.getValue()} />,
  }),
  col.accessor('passing', {
    header: 'Pas.',
    cell: (info) => <SkillBar value={info.getValue()} />,
  }),
  col.accessor('scoring', {
    header: 'Att.',
    cell: (info) => <SkillBar value={info.getValue()} />,
  }),
  col.accessor('set_pieces', {
    header: 'Cal.',
    cell: (info) => <SkillBar value={info.getValue()} />,
  }),
  col.accessor('salary', {
    header: 'Stipendio',
    cell: (info) => `€${info.getValue().toLocaleString('it-IT')}`,
  }),
  col.accessor('injury_days', {
    header: 'Infort.',
    cell: (info) => {
      const v = info.getValue()
      return v === -1 ? '—' : <span style={{ color: '#ef4444' }}>{v}w</span>
    },
  }),
]

export function Squad() {
  const qc = useQueryClient()
  const [sorting, setSorting] = useState<SortingState>([])
  const { data: players = [], isLoading, error } = useQuery({
    queryKey: ['squad'],
    queryFn: getSquad,
  })

  const table = useReactTable({
    data: players,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  })

  return (
    <div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 16,
        }}
      >
        <h1 style={{ margin: 0 }}>Rosa ({players.length})</h1>
        <SyncButton entity="squad" onSynced={() => qc.invalidateQueries({ queryKey: ['squad'] })} />
      </div>

      {isLoading && <p>Caricamento…</p>}
      {error && <p style={{ color: '#ef4444' }}>Errore: {(error as Error).message}</p>}

      {!isLoading && players.length === 0 && (
        <p style={{ color: '#6b7280' }}>
          Nessun giocatore. Configura le credenziali CHPP e clicca Sincronizza.
        </p>
      )}

      {players.length > 0 && (
        <div style={{ overflowX: 'auto' }}>
          <table
            style={{
              width: '100%',
              borderCollapse: 'collapse',
              background: '#fff',
              borderRadius: 8,
              overflow: 'hidden',
            }}
          >
            <thead>
              {table.getHeaderGroups().map((hg) => (
                <tr key={hg.id}>
                  {hg.headers.map((h) => (
                    <th
                      key={h.id}
                      onClick={h.column.getToggleSortingHandler()}
                      style={{
                        padding: '10px 12px',
                        textAlign: 'left',
                        borderBottom: '2px solid #e5e7eb',
                        cursor: h.column.getCanSort() ? 'pointer' : 'default',
                        whiteSpace: 'nowrap',
                        fontSize: 13,
                        color: '#6b7280',
                        userSelect: 'none',
                      }}
                    >
                      {flexRender(h.column.columnDef.header, h.getContext())}
                      {h.column.getIsSorted() === 'asc'
                        ? ' ↑'
                        : h.column.getIsSorted() === 'desc'
                        ? ' ↓'
                        : ''}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody>
              {table.getRowModel().rows.map((row, i) => (
                <tr
                  key={row.id}
                  style={{ background: i % 2 === 0 ? '#fff' : '#f9fafb' }}
                >
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} style={{ padding: '8px 12px', fontSize: 13 }}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Verifica nel browser**

Vai su `http://localhost:5173/squad`. Se hai già salvato i token CHPP e sincronizzato, devi vedere la tabella. Altrimenti vedi il messaggio "Nessun giocatore". Clicca l'header di colonna per verificare l'ordinamento.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Squad.tsx
git commit -m "feat: Squad page — sortable TanStack Table with SkillBar"
```

---

## Task 17: Pagina Dashboard

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`

- [ ] **Step 1: Implementa `frontend/src/pages/Dashboard.tsx`**

```tsx
import { useQuery } from '@tanstack/react-query'
import { getSquad } from '../api/squad'

function KPI({ label, value }: { label: string; value: string | number }) {
  return (
    <div
      style={{
        padding: '20px 24px',
        background: '#fff',
        border: '1px solid #e5e7eb',
        borderRadius: 8,
        minWidth: 180,
      }}
    >
      <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        {label}
      </div>
      <div style={{ fontSize: 26, fontWeight: 700, color: '#111827' }}>{value}</div>
    </div>
  )
}

export function Dashboard() {
  const { data: players = [], isLoading } = useQuery({
    queryKey: ['squad'],
    queryFn: getSquad,
  })

  if (isLoading) return <p>Caricamento…</p>

  const playerCount = players.length
  const avgForm =
    playerCount > 0
      ? (players.reduce((s, p) => s + p.form, 0) / playerCount).toFixed(1)
      : '—'
  const topScorer =
    playerCount > 0 ? [...players].sort((a, b) => b.scoring - a.scoring)[0] : null
  const injured = players.filter((p) => p.injury_days > 0).length

  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Dashboard</h1>

      {playerCount === 0 ? (
        <p style={{ color: '#6b7280' }}>
          Nessun dato. Vai in{' '}
          <a href="/settings">Impostazioni</a> per configurare CHPP, poi{' '}
          <a href="/squad">sincronizza la rosa</a>.
        </p>
      ) : (
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
          <KPI label="Giocatori in rosa" value={playerCount} />
          <KPI label="Forma media" value={avgForm} />
          <KPI
            label="Miglior attaccante"
            value={
              topScorer
                ? `${topScorer.first_name} ${topScorer.last_name} (${topScorer.scoring})`
                : '—'
            }
          />
          <KPI label="Infortunati" value={injured} />
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Verifica nel browser**

Vai su `http://localhost:5173/`. Con giocatori sincronizzati devi vedere 4 KPI card. Senza dati vedi il messaggio con link.

- [ ] **Step 3: Esegui tutti i test backend per regressioni**

```bash
cd backend && pytest -v
```

Expected: tutti i test passano.

- [ ] **Step 4: Commit finale**

```bash
git add frontend/src/pages/Dashboard.tsx
git commit -m "feat: Dashboard page — KPI cards (giocatori, forma, top scorer, infortunati)"
```

---

## Verifica end-to-end

Dopo aver completato tutti i task:

- [ ] **1. Avvia il sistema completo**

```bash
make dev
```

- [ ] **2. Percorso golden path**

1. Apri `http://localhost:5173`
2. Vai in `/settings` — inserisci le credenziali CHPP reali — clicca Salva
3. Vai in `/squad` — clicca Sincronizza — attendi il messaggio "Aggiornato: ..."
4. Verifica che la tabella si popoli con i giocatori reali
5. Torna in `/` — verifica che le KPI mostrino dati reali

- [ ] **3. Edge cases**

- Prova Sincronizza senza credenziali configurate → deve apparire un messaggio d'errore nel SyncButton
- Naviga tra le pagine — verifica che la nav evidenzi la pagina corrente
- Clicca gli header della tabella in `/squad` → verifica l'ordinamento

- [ ] **4. Test backend completi**

```bash
cd backend && pytest -v
```

Expected: tutti i test passano.

---

## Self-review

**Copertura spec:**
- ✅ Backend: FastAPI + SQLAlchemy + SQLite
- ✅ CHPP OAuth 1.0a via requests-oauthlib
- ✅ Parsing XML con lxml
- ✅ Endpoint: `/api/squad`, `/api/settings` (GET+POST), `/api/sync/{entity}`, `/api/sync/status`
- ✅ Frontend: React + Vite + TypeScript
- ✅ Navigazione: React Router
- ✅ Fetching/cache: TanStack Query
- ✅ Tabelle: TanStack Table con ordinamento
- ✅ Pagine: Dashboard, `/squad`, `/settings`
- ✅ Componenti: `SkillBar`, `SyncButton`
- ✅ Test unitari parser XML con fixture reali
- ✅ Test endpoint FastAPI con in-memory SQLite
- ✅ Makefile con `install`, `dev`, `test`
- ✅ Gestione errori: 400 per entità sconosciuta, 400 per token mancanti, messaggio leggibile nel frontend
- ⚠️ Grafici (Recharts): non inclusi — le pagine `/players/:id`, `/training`, `/finances` sono nei piani B, C, D
- ⚠️ `/next-match`: Piano E separato

**Nessun placeholder trovato** — ogni step contiene codice completo.

**Consistenza tipi:** `Player` definito in `squad.ts` usato ovunque nel frontend. Campi backend (`first_name`, `last_name`, `injury_days`, `set_pieces`) consistenti tra modello SQLAlchemy, parser, API response, e interfaccia TypeScript.
