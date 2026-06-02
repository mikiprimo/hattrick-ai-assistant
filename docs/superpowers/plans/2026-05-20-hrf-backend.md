# Piano B1 — HRF Backend Integration

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Aggiungere il percorso HRF come sorgente dati primaria: parser INI, scanner cartella, nuovi modelli DB, endpoint scan — senza toccare il codice CHPP esistente.

**Architecture:** Nuovo modulo `app/hrf/` (parallelo a `app/chpp/`, immutato). Il modello `Player` viene esteso con 11 campi nullable. Nuova tabella `PlayerSkillHistory` cattura uno snapshot per giocatore per file HRF importato. `POST /api/hrf/scan` scansiona `/program/ho/` (o path configurato) e popola il DB. Auto-migrazione al startup via `run_migrations(engine)`.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.x, SQLite, `configparser` (stdlib), `pytest`

---

## File Map

| Azione | Percorso | Responsabilità |
|--------|----------|----------------|
| Crea | `backend/app/hrf/__init__.py` | package marker (vuoto) |
| Crea | `backend/app/hrf/models.py` | dataclass `HRFPlayer`, `HRFSnapshot` |
| Crea | `backend/app/hrf/parser.py` | parse file .hrf INI → `HRFSnapshot` |
| Crea | `backend/app/hrf/scanner.py` | scansiona cartella → `list[HRFSnapshot]` |
| Crea | `backend/app/models/player_skill_history.py` | SQLAlchemy model `PlayerSkillHistory` |
| Crea | `backend/app/models/hrf_settings.py` | SQLAlchemy model `HRFSettings` |
| Crea | `backend/app/migrations.py` | `run_migrations(engine)` — ALTER TABLE per nuovi campi |
| Crea | `backend/app/api/hrf.py` | router: `GET/POST /api/hrf/settings`, `POST /api/hrf/scan`, `GET /api/hrf/files` |
| Crea | `backend/tests/fixtures/549298-2026-05-20.hrf` | fixture realistica per test |
| Crea | `backend/tests/fixtures/549298-2026-05-13.hrf` | seconda fixture (per test scanner storico) |
| Crea | `backend/tests/test_hrf_parser.py` | unit test parser |
| Crea | `backend/tests/test_hrf_scanner.py` | unit test scanner |
| Crea | `backend/tests/test_api_hrf.py` | test endpoint HRF |
| Modifica | `backend/app/models/player.py` | +11 campi nullable |
| Modifica | `backend/app/main.py` | import modelli espliciti prima di `create_all` + `run_migrations` + router hrf |

---

## Task 1 — HRF dataclasses + parser filename

**Files:**
- Crea: `backend/app/hrf/__init__.py`
- Crea: `backend/app/hrf/models.py`
- Crea: `backend/app/hrf/parser.py` (solo `_extract_filename_metadata`)
- Crea: `backend/tests/test_hrf_parser.py`

- [ ] **Step 1: Scrivi i test fallenti per `_extract_filename_metadata`**

```python
# backend/tests/test_hrf_parser.py
import pytest
from datetime import datetime
from app.hrf.parser import _extract_filename_metadata


def test_extract_valid_filename():
    team_id, date = _extract_filename_metadata("549298-2026-05-20.hrf")
    assert team_id == 549298
    assert date == datetime(2026, 5, 20)


def test_extract_invalid_filename_raises():
    with pytest.raises(ValueError, match="Invalid HRF filename"):
        _extract_filename_metadata("invalid_file.hrf")


def test_extract_missing_extension_raises():
    with pytest.raises(ValueError, match="Invalid HRF filename"):
        _extract_filename_metadata("549298-2026-05-20")
```

- [ ] **Step 2: Esegui i test per verificare che falliscano**

```bash
cd /media/michel/Lavoro/source/myhattrick/backend
python -m pytest tests/test_hrf_parser.py -v
```
Risultato atteso: `ModuleNotFoundError: No module named 'app.hrf'`

- [ ] **Step 3: Crea i file del modulo**

`backend/app/hrf/__init__.py` — file vuoto.

```python
# backend/app/hrf/models.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class HRFPlayer:
    player_id: int
    first_name: str
    last_name: str
    age: int
    age_days: int
    salary: int
    injury_days: int
    form: int
    stamina: int
    speed: int
    scoring: int
    passing: int
    winger: int
    defending: int
    playmaking: int
    goalkeeper: int
    set_pieces: int
    leadership: int
    experience: int
    loyalty: int
    market_value: int
    speciality: Optional[str]
    last_match_rating: Optional[float]
    transfer_listed: bool
    country_id: Optional[int]
    homegrown: bool


@dataclass
class HRFSnapshot:
    team_id: int
    snapshot_date: datetime
    file_path: str
    players: list[HRFPlayer] = field(default_factory=list)
```

```python
# backend/app/hrf/parser.py
import re
import configparser
from datetime import datetime
from pathlib import Path
from typing import Optional
from app.hrf.models import HRFPlayer, HRFSnapshot

_FILENAME_RE = re.compile(r'^(\d+)-(\d{4}-\d{2}-\d{2})\.hrf$')
_PLAYER_SECTION_RE = re.compile(r'^player(\d+)$')


def _extract_filename_metadata(filename: str) -> tuple[int, datetime]:
    m = _FILENAME_RE.match(filename)
    if not m:
        raise ValueError(f"Invalid HRF filename: {filename}")
    return int(m.group(1)), datetime.strptime(m.group(2), "%Y-%m-%d")


def parse_hrf_file(file_path: str) -> HRFSnapshot:
    path = Path(file_path)
    team_id, snapshot_date = _extract_filename_metadata(path.name)

    cfg = configparser.ConfigParser()
    cfg.optionxform = str  # preserva maiuscole/minuscole nei nomi chiave
    cfg.read(str(path), encoding="utf-8")

    players = []
    for section in cfg.sections():
        m = _PLAYER_SECTION_RE.match(section)
        if not m:
            continue
        sec = cfg[section]
        if not sec.get("for", "").strip():  # salta allenatore (campi vuoti)
            continue
        players.append(_parse_player(int(m.group(1)), sec))

    return HRFSnapshot(team_id=team_id, snapshot_date=snapshot_date,
                       file_path=str(path), players=players)


def _parse_player(player_id: int, sec: configparser.SectionProxy) -> HRFPlayer:
    def i(key: str, default: int = 0) -> int:
        try:
            return int(sec.get(key, str(default)).strip() or default)
        except (ValueError, TypeError):
            return default

    def f(key: str) -> Optional[float]:
        try:
            v = sec.get(key, "").strip()
            return float(v) if v else None
        except (ValueError, TypeError):
            return None

    def b(key: str) -> bool:
        return sec.get(key, "False").strip().lower() == "true"

    return HRFPlayer(
        player_id=player_id,
        first_name=sec.get("firstname", "").strip(),
        last_name=sec.get("lastname", "").strip(),
        age=i("ald"),
        age_days=i("agedays"),
        salary=i("sal"),
        injury_days=i("ska", -1),
        form=i("for"),
        stamina=i("uth"),
        speed=i("spe"),
        scoring=i("mal"),
        passing=i("fra"),
        winger=i("ytt"),
        defending=i("fas"),
        playmaking=i("bac"),
        goalkeeper=i("mlv"),
        set_pieces=i("rut"),
        leadership=i("led"),
        experience=i("gev"),
        loyalty=i("loy"),
        market_value=i("mkt"),
        speciality=sec.get("specialityLabel", "").strip() or None,
        last_match_rating=f("LastMatch_Rating"),
        transfer_listed=b("TransferListed"),
        country_id=i("CountryID") or None,
        homegrown=b("homegr"),
    )
```

- [ ] **Step 4: Esegui i test per verificare che passino**

```bash
cd /media/michel/Lavoro/source/myhattrick/backend
python -m pytest tests/test_hrf_parser.py::test_extract_valid_filename tests/test_hrf_parser.py::test_extract_invalid_filename_raises tests/test_hrf_parser.py::test_extract_missing_extension_raises -v
```
Risultato atteso: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/hrf/ backend/tests/test_hrf_parser.py
git commit -m "feat: add HRF module skeleton with dataclasses and filename parser"
```

---

## Task 2 — HRF parser completo

**Files:**
- Crea: `backend/tests/fixtures/549298-2026-05-20.hrf`
- Crea: `backend/tests/fixtures/549298-2026-05-13.hrf`
- Modifica: `backend/tests/test_hrf_parser.py` (aggiungi test per `parse_hrf_file`)

- [ ] **Step 1: Crea le fixture HRF**

```ini
# backend/tests/fixtures/549298-2026-05-20.hrf
[basics]
application=HO
teamID=549298
teamName=Test FC
date=2026-05-20 21:57:45

[player100001]
name=Mario Rossi
firstname=Mario
lastname=Rossi
ald=25
agedays=100
ska=-1
for=7
uth=8
spe=6
mal=4
fra=8
ytt=3
fas=10
bac=12
mlv=1
rut=5
led=4
gev=15
loy=18
mkt=45000
sal=80000
speciality=0
specialityLabel=
TransferListed=False
CountryID=4
homegr=True
LastMatch_Rating=7.5
PlayerNumber=1

[player100002]
name=Luca Bianchi
firstname=Luca
lastname=Bianchi
ald=30
agedays=50
ska=-1
for=5
uth=6
spe=8
mal=9
fra=7
ytt=12
fas=5
bac=6
mlv=1
rut=4
led=3
gev=20
loy=15
mkt=30000
sal=60000
speciality=2
specialityLabel=Veloce
TransferListed=True
CountryID=7
homegr=False
LastMatch_Rating=6.0
PlayerNumber=2

[player295000001]
name=null Trainer
firstname=
lastname=Trainer
ald=51
agedays=78
for=
uth=
spe=
fas=
bac=
mlv=
TrainerType=2
TrainerSkillLevel=4
```

```ini
# backend/tests/fixtures/549298-2026-05-13.hrf
[basics]
application=HO
teamID=549298
teamName=Test FC
date=2026-05-13 20:00:00

[player100001]
name=Mario Rossi
firstname=Mario
lastname=Rossi
ald=25
agedays=93
ska=-1
for=6
uth=8
spe=6
mal=4
fra=7
ytt=3
fas=9
bac=12
mlv=1
rut=5
led=4
gev=15
loy=18
mkt=44000
sal=80000
speciality=0
specialityLabel=
TransferListed=False
CountryID=4
homegr=True
LastMatch_Rating=7.0
PlayerNumber=1

[player100002]
name=Luca Bianchi
firstname=Luca
lastname=Bianchi
ald=30
agedays=43
ska=-1
for=5
uth=6
spe=8
mal=8
fra=7
ytt=12
fas=5
bac=6
mlv=1
rut=4
led=3
gev=20
loy=15
mkt=29000
sal=60000
speciality=2
specialityLabel=Veloce
TransferListed=False
CountryID=7
homegr=False
LastMatch_Rating=5.5
PlayerNumber=2
```

- [ ] **Step 2: Scrivi i test per `parse_hrf_file`**

Aggiungi in fondo a `backend/tests/test_hrf_parser.py`:

```python
from pathlib import Path
from app.hrf.parser import parse_hrf_file

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_hrf_file_returns_snapshot():
    snapshot = parse_hrf_file(str(FIXTURES / "549298-2026-05-20.hrf"))
    assert snapshot.team_id == 549298
    assert snapshot.snapshot_date.year == 2026
    assert snapshot.snapshot_date.month == 5
    assert snapshot.snapshot_date.day == 20


def test_parse_hrf_file_extracts_players():
    snapshot = parse_hrf_file(str(FIXTURES / "549298-2026-05-20.hrf"))
    assert len(snapshot.players) == 2  # trainer escluso


def test_parse_hrf_player_skills():
    snapshot = parse_hrf_file(str(FIXTURES / "549298-2026-05-20.hrf"))
    mario = next(p for p in snapshot.players if p.player_id == 100001)
    assert mario.form == 7
    assert mario.stamina == 8
    assert mario.defending == 10
    assert mario.playmaking == 12
    assert mario.age == 25
    assert mario.age_days == 100
    assert mario.salary == 80000
    assert mario.homegrown is True
    assert mario.transfer_listed is False
    assert mario.last_match_rating == 7.5
    assert mario.speciality is None  # specialityLabel vuoto → None


def test_parse_hrf_player_speciality():
    snapshot = parse_hrf_file(str(FIXTURES / "549298-2026-05-20.hrf"))
    luca = next(p for p in snapshot.players if p.player_id == 100002)
    assert luca.speciality == "Veloce"
    assert luca.transfer_listed is True
    assert luca.country_id == 7


def test_parse_hrf_skips_trainer():
    snapshot = parse_hrf_file(str(FIXTURES / "549298-2026-05-20.hrf"))
    ids = {p.player_id for p in snapshot.players}
    assert 295000001 not in ids
```

- [ ] **Step 3: Esegui i test per verificare che falliscano**

```bash
cd /media/michel/Lavoro/source/myhattrick/backend
python -m pytest tests/test_hrf_parser.py -v
```
Risultato atteso: 3 pass (filename tests), 5 fail (file non ancora trovate/parser incompleto).

- [ ] **Step 4: Verifica che `parse_hrf_file` sia già implementato nel Task 1**

Il codice è già completo nel Task 1. I test dovrebbero passare tutti ora.

```bash
python -m pytest tests/test_hrf_parser.py -v
```
Risultato atteso: `8 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/tests/fixtures/ backend/tests/test_hrf_parser.py
git commit -m "feat: add HRF parser with full section parsing and test fixtures"
```

---

## Task 3 — HRF directory scanner

**Files:**
- Crea: `backend/app/hrf/scanner.py`
- Crea: `backend/tests/test_hrf_scanner.py`

- [ ] **Step 1: Scrivi i test fallenti**

```python
# backend/tests/test_hrf_scanner.py
import shutil
from pathlib import Path
import pytest
from app.hrf.scanner import scan_hrf_directory

FIXTURES = Path(__file__).parent / "fixtures"


def test_scan_returns_snapshots_ordered_by_date(tmp_path):
    shutil.copy(FIXTURES / "549298-2026-05-13.hrf", tmp_path)
    shutil.copy(FIXTURES / "549298-2026-05-20.hrf", tmp_path)
    snapshots = scan_hrf_directory(str(tmp_path))
    assert len(snapshots) == 2
    assert snapshots[0].snapshot_date < snapshots[1].snapshot_date


def test_scan_skips_invalid_filenames(tmp_path):
    shutil.copy(FIXTURES / "549298-2026-05-20.hrf", tmp_path)
    (tmp_path / "invalid_file.hrf").write_text("[basics]\nteamID=1\n")
    snapshots = scan_hrf_directory(str(tmp_path))
    assert len(snapshots) == 1


def test_scan_empty_folder(tmp_path):
    snapshots = scan_hrf_directory(str(tmp_path))
    assert snapshots == []


def test_scan_nonexistent_folder_raises():
    with pytest.raises(FileNotFoundError):
        scan_hrf_directory("/nonexistent/path/")


def test_scan_since_date_filters(tmp_path):
    from datetime import datetime
    shutil.copy(FIXTURES / "549298-2026-05-13.hrf", tmp_path)
    shutil.copy(FIXTURES / "549298-2026-05-20.hrf", tmp_path)
    cutoff = datetime(2026, 5, 13)
    snapshots = scan_hrf_directory(str(tmp_path), since_date=cutoff)
    assert len(snapshots) == 1
    assert snapshots[0].snapshot_date.day == 20
```

- [ ] **Step 2: Esegui i test per verificare che falliscano**

```bash
cd /media/michel/Lavoro/source/myhattrick/backend
python -m pytest tests/test_hrf_scanner.py -v
```
Risultato atteso: `ModuleNotFoundError: No module named 'app.hrf.scanner'`

- [ ] **Step 3: Implementa lo scanner**

```python
# backend/app/hrf/scanner.py
from datetime import datetime
from pathlib import Path
from typing import Optional
from app.hrf.parser import parse_hrf_file, _extract_filename_metadata
from app.hrf.models import HRFSnapshot


def scan_hrf_directory(
    folder_path: str,
    since_date: Optional[datetime] = None,
) -> list[HRFSnapshot]:
    folder = Path(folder_path)
    if not folder.exists():
        raise FileNotFoundError(f"HRF folder not found: {folder_path}")

    snapshots = []
    for hrf_file in sorted(folder.glob("*.hrf")):
        try:
            _team_id, snapshot_date = _extract_filename_metadata(hrf_file.name)
        except ValueError:
            continue
        if since_date and snapshot_date <= since_date:
            continue
        try:
            snapshots.append(parse_hrf_file(str(hrf_file)))
        except Exception:
            continue

    return sorted(snapshots, key=lambda s: s.snapshot_date)
```

- [ ] **Step 4: Esegui i test per verificare che passino**

```bash
python -m pytest tests/test_hrf_scanner.py -v
```
Risultato atteso: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/hrf/scanner.py backend/tests/test_hrf_scanner.py
git commit -m "feat: add HRF directory scanner"
```

---

## Task 4 — Nuovi modelli DB (PlayerSkillHistory + HRFSettings)

**Files:**
- Crea: `backend/app/models/player_skill_history.py`
- Crea: `backend/app/models/hrf_settings.py`

- [ ] **Step 1: Crea `PlayerSkillHistory`**

```python
# backend/app/models/player_skill_history.py
from datetime import datetime
from sqlalchemy import Integer, DateTime, String, ForeignKey, UniqueConstraint, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class PlayerSkillHistory(Base):
    __tablename__ = "player_skill_history"
    __table_args__ = (
        UniqueConstraint("player_id", "snapshot_date", name="uq_player_snapshot"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"), nullable=False)
    snapshot_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    source: Mapped[str] = mapped_column(String, default="HRF")

    form: Mapped[int] = mapped_column(Integer, default=0)
    stamina: Mapped[int] = mapped_column(Integer, default=0)
    speed: Mapped[int] = mapped_column(Integer, default=0)
    scoring: Mapped[int] = mapped_column(Integer, default=0)
    passing: Mapped[int] = mapped_column(Integer, default=0)
    winger: Mapped[int] = mapped_column(Integer, default=0)
    defending: Mapped[int] = mapped_column(Integer, default=0)
    playmaking: Mapped[int] = mapped_column(Integer, default=0)
    goalkeeper: Mapped[int] = mapped_column(Integer, default=0)
    set_pieces: Mapped[int] = mapped_column(Integer, default=0)
    leadership: Mapped[int] = mapped_column(Integer, default=0)
    experience: Mapped[int] = mapped_column(Integer, default=0)
    loyalty: Mapped[int] = mapped_column(Integer, default=0)
```

- [ ] **Step 2: Crea `HRFSettings`**

```python
# backend/app/models/hrf_settings.py
from typing import Optional
from sqlalchemy import Integer, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class HRFSettings(Base):
    __tablename__ = "hrf_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hrf_folder_path: Mapped[str] = mapped_column(String, nullable=False)
    team_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
```

- [ ] **Step 3: Verifica importabilità**

```bash
cd /media/michel/Lavoro/source/myhattrick/backend
python -c "from app.models.player_skill_history import PlayerSkillHistory; from app.models.hrf_settings import HRFSettings; print('OK')"
```
Risultato atteso: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/player_skill_history.py backend/app/models/hrf_settings.py
git commit -m "feat: add PlayerSkillHistory and HRFSettings SQLAlchemy models"
```

---

## Task 5 — Estensione Player model + auto-migrazione

**Files:**
- Modifica: `backend/app/models/player.py`
- Crea: `backend/app/migrations.py`
- Crea: `backend/tests/test_migrations.py`

- [ ] **Step 1: Scrivi test per la migrazione**

```python
# backend/tests/test_migrations.py
from sqlalchemy import create_engine, inspect
from sqlalchemy.pool import StaticPool
from app.database import Base


def test_run_migrations_adds_hrf_columns():
    from app.models.player import Player  # noqa: F401
    from app.models.sync_log import SyncLog  # noqa: F401
    from app.models.settings import CHPPSettings  # noqa: F401
    from app.models.player_skill_history import PlayerSkillHistory  # noqa: F401
    from app.models.hrf_settings import HRFSettings  # noqa: F401
    from app.migrations import run_migrations

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Crea solo le tabelle originali (simula DB esistente senza colonne HRF)
    # Creiamo manualmente solo la tabella players senza i nuovi campi
    from sqlalchemy import text
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE players (
                id INTEGER PRIMARY KEY,
                first_name TEXT DEFAULT '',
                last_name TEXT DEFAULT '',
                age INTEGER DEFAULT 0,
                age_days INTEGER DEFAULT 0,
                tsi INTEGER DEFAULT 0,
                form INTEGER DEFAULT 0,
                stamina INTEGER DEFAULT 0,
                injury_days INTEGER DEFAULT -1,
                salary INTEGER DEFAULT 0,
                goalkeeper INTEGER DEFAULT 0,
                defending INTEGER DEFAULT 0,
                playmaking INTEGER DEFAULT 0,
                winger INTEGER DEFAULT 0,
                passing INTEGER DEFAULT 0,
                scoring INTEGER DEFAULT 0,
                set_pieces INTEGER DEFAULT 0
            )
        """))
        conn.execute(text("CREATE TABLE sync_log (id INTEGER PRIMARY KEY, entity TEXT UNIQUE, last_sync_at DATETIME, status TEXT DEFAULT 'ok')"))

    run_migrations(engine)

    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("players")}
    assert "speed" in cols
    assert "leadership" in cols
    assert "experience" in cols
    assert "loyalty" in cols
    assert "market_value" in cols
    assert "speciality" in cols
    assert "last_match_rating" in cols
    assert "transfer_listed" in cols
    assert "country_id" in cols
    assert "homegrown" in cols
    assert "data_source" in cols
    tables = inspector.get_table_names()
    assert "player_skill_history" in tables
    assert "hrf_settings" in tables
```

- [ ] **Step 2: Esegui il test per verificare che fallisca**

```bash
cd /media/michel/Lavoro/source/myhattrick/backend
python -m pytest tests/test_migrations.py -v
```
Risultato atteso: `ModuleNotFoundError: No module named 'app.migrations'`

- [ ] **Step 3: Estendi `Player` con i nuovi campi**

```python
# backend/app/models/player.py
from typing import Optional
from sqlalchemy import String, Integer, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String, default="")
    last_name: Mapped[str] = mapped_column(String, default="")
    age: Mapped[int] = mapped_column(Integer, default=0)
    age_days: Mapped[int] = mapped_column(Integer, default=0)
    tsi: Mapped[int] = mapped_column(Integer, default=0)
    form: Mapped[int] = mapped_column(Integer, default=0)
    stamina: Mapped[int] = mapped_column(Integer, default=0)
    injury_days: Mapped[int] = mapped_column(Integer, default=-1)
    salary: Mapped[int] = mapped_column(Integer, default=0)
    goalkeeper: Mapped[int] = mapped_column(Integer, default=0)
    defending: Mapped[int] = mapped_column(Integer, default=0)
    playmaking: Mapped[int] = mapped_column(Integer, default=0)
    winger: Mapped[int] = mapped_column(Integer, default=0)
    passing: Mapped[int] = mapped_column(Integer, default=0)
    scoring: Mapped[int] = mapped_column(Integer, default=0)
    set_pieces: Mapped[int] = mapped_column(Integer, default=0)
    # HRF fields
    speed: Mapped[int] = mapped_column(Integer, default=0)
    leadership: Mapped[int] = mapped_column(Integer, default=0)
    experience: Mapped[int] = mapped_column(Integer, default=0)
    loyalty: Mapped[int] = mapped_column(Integer, default=0)
    market_value: Mapped[int] = mapped_column(Integer, default=0)
    speciality: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_match_rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    transfer_listed: Mapped[bool] = mapped_column(Boolean, default=False)
    country_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    homegrown: Mapped[bool] = mapped_column(Boolean, default=False)
    data_source: Mapped[str] = mapped_column(String, default="CHPP")
```

- [ ] **Step 4: Crea `backend/app/migrations.py`**

```python
# backend/app/migrations.py
from sqlalchemy import inspect, text


def run_migrations(engine) -> None:
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    if "players" in tables:
        existing = {c["name"] for c in inspector.get_columns("players")}
        new_cols = [
            ("speed",             "INTEGER DEFAULT 0"),
            ("leadership",        "INTEGER DEFAULT 0"),
            ("experience",        "INTEGER DEFAULT 0"),
            ("loyalty",           "INTEGER DEFAULT 0"),
            ("market_value",      "INTEGER DEFAULT 0"),
            ("speciality",        "TEXT"),
            ("last_match_rating", "REAL"),
            ("transfer_listed",   "BOOLEAN DEFAULT 0"),
            ("country_id",        "INTEGER"),
            ("homegrown",         "BOOLEAN DEFAULT 0"),
            ("data_source",       "TEXT DEFAULT 'CHPP'"),
        ]
        with engine.begin() as conn:
            for col_name, col_def in new_cols:
                if col_name not in existing:
                    conn.execute(text(f"ALTER TABLE players ADD COLUMN {col_name} {col_def}"))

    from app.database import Base
    Base.metadata.create_all(bind=engine, checkfirst=True)
```

- [ ] **Step 5: Esegui il test per verificare che passi**

```bash
python -m pytest tests/test_migrations.py -v
```
Risultato atteso: `1 passed`

- [ ] **Step 6: Verifica che i test esistenti ancora passino**

```bash
python -m pytest tests/ -v --ignore=tests/test_migrations.py
```
Risultato atteso: tutti i test precedenti passano (no regressioni).

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/player.py backend/app/migrations.py backend/tests/test_migrations.py
git commit -m "feat: extend Player model with HRF fields and add auto-migration"
```

---

## Task 6 — API endpoints HRF

**Files:**
- Crea: `backend/app/api/hrf.py`
- Crea: `backend/tests/test_api_hrf.py`

- [ ] **Step 1: Scrivi i test fallenti**

```python
# backend/tests/test_api_hrf.py
import shutil
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def client_with_hrf_db(tmp_path):
    from app.models import player, settings, sync_log  # noqa
    from app.models.player_skill_history import PlayerSkillHistory  # noqa
    from app.models.hrf_settings import HRFSettings  # noqa

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
    client.post("/api/hrf/scan")  # seconda volta

    from app.models.player_skill_history import PlayerSkillHistory
    assert db.query(PlayerSkillHistory).count() == 2  # no duplicati


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
```

- [ ] **Step 2: Esegui i test per verificare che falliscano**

```bash
cd /media/michel/Lavoro/source/myhattrick/backend
python -m pytest tests/test_api_hrf.py -v
```
Risultato atteso: tutti falliscono con `404` o `AttributeError` (router non registrato).

- [ ] **Step 3: Implementa `backend/app/api/hrf.py`**

```python
# backend/app/api/hrf.py
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.hrf_settings import HRFSettings
from app.models.player import Player
from app.models.player_skill_history import PlayerSkillHistory
from app.models.sync_log import SyncLog
from app.hrf.scanner import scan_hrf_directory
from app.hrf.parser import _extract_filename_metadata

router = APIRouter()


class HRFSettingsRequest(BaseModel):
    hrf_folder_path: str
    team_id: Optional[int] = None
    enabled: bool = True


@router.get("/hrf/settings")
def get_hrf_settings(db: Session = Depends(get_db)):
    s = db.query(HRFSettings).first()
    if not s:
        raise HTTPException(status_code=404, detail="HRF not configured")
    return {"hrf_folder_path": s.hrf_folder_path, "team_id": s.team_id, "enabled": s.enabled}


@router.post("/hrf/settings")
def set_hrf_settings(body: HRFSettingsRequest, db: Session = Depends(get_db)):
    if not Path(body.hrf_folder_path).exists():
        raise HTTPException(status_code=400, detail=f"Path not found: {body.hrf_folder_path}")
    s = db.query(HRFSettings).first()
    if s:
        s.hrf_folder_path = body.hrf_folder_path
        s.team_id = body.team_id
        s.enabled = body.enabled
    else:
        db.add(HRFSettings(id=1, hrf_folder_path=body.hrf_folder_path,
                           team_id=body.team_id, enabled=body.enabled))
    db.commit()
    return {"status": "ok"}


@router.post("/hrf/scan")
def scan_and_import(db: Session = Depends(get_db)):
    s = db.query(HRFSettings).first()
    if not s or not s.enabled:
        raise HTTPException(status_code=400, detail="HRF not configured — POST /api/hrf/settings first")

    try:
        snapshots = scan_hrf_directory(s.hrf_folder_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    players_upserted = 0

    for snapshot in snapshots:
        for hp in snapshot.players:
            fields = {
                "first_name": hp.first_name, "last_name": hp.last_name,
                "age": hp.age, "age_days": hp.age_days,
                "salary": hp.salary, "injury_days": hp.injury_days,
                "form": hp.form, "stamina": hp.stamina, "speed": hp.speed,
                "scoring": hp.scoring, "passing": hp.passing, "winger": hp.winger,
                "defending": hp.defending, "playmaking": hp.playmaking,
                "goalkeeper": hp.goalkeeper, "set_pieces": hp.set_pieces,
                "leadership": hp.leadership, "experience": hp.experience,
                "loyalty": hp.loyalty, "market_value": hp.market_value,
                "speciality": hp.speciality, "last_match_rating": hp.last_match_rating,
                "transfer_listed": hp.transfer_listed, "country_id": hp.country_id,
                "homegrown": hp.homegrown, "data_source": "HRF",
            }
            existing = db.get(Player, hp.player_id)
            if existing:
                for k, v in fields.items():
                    setattr(existing, k, v)
            else:
                db.add(Player(id=hp.player_id, **fields))
            players_upserted += 1

            already = db.query(PlayerSkillHistory).filter_by(
                player_id=hp.player_id, snapshot_date=snapshot.snapshot_date
            ).first()
            if not already:
                db.add(PlayerSkillHistory(
                    player_id=hp.player_id,
                    snapshot_date=snapshot.snapshot_date,
                    source="HRF",
                    form=hp.form, stamina=hp.stamina, speed=hp.speed,
                    scoring=hp.scoring, passing=hp.passing, winger=hp.winger,
                    defending=hp.defending, playmaking=hp.playmaking,
                    goalkeeper=hp.goalkeeper, set_pieces=hp.set_pieces,
                    leadership=hp.leadership, experience=hp.experience,
                    loyalty=hp.loyalty,
                ))

    now = datetime.now(timezone.utc)
    log = db.query(SyncLog).filter_by(entity="hrf").first()
    if log:
        log.last_sync_at = now
        log.status = "ok"
    else:
        db.add(SyncLog(entity="hrf", last_sync_at=now, status="ok"))

    db.commit()
    return {
        "status": "ok",
        "scanned_at": now.isoformat(),
        "files_imported": len(snapshots),
        "players_upserted": players_upserted,
    }


@router.get("/hrf/files")
def list_hrf_files(db: Session = Depends(get_db)):
    s = db.query(HRFSettings).first()
    if not s:
        raise HTTPException(status_code=404, detail="HRF not configured")

    folder = Path(s.hrf_folder_path)
    if not folder.exists():
        raise HTTPException(status_code=404, detail=f"Folder not found: {s.hrf_folder_path}")

    files = []
    imported_dates = {
        row.snapshot_date.date()
        for row in db.query(PlayerSkillHistory.snapshot_date).distinct()
    }

    for hrf_file in sorted(folder.glob("*.hrf")):
        try:
            _team_id, snapshot_date = _extract_filename_metadata(hrf_file.name)
        except ValueError:
            continue
        files.append({
            "filename": hrf_file.name,
            "date": snapshot_date.strftime("%Y-%m-%d"),
            "imported": snapshot_date.date() in imported_dates,
        })

    return {"folder": str(folder), "files": files}
```

- [ ] **Step 4: Esegui i test per verificare che falliscano ancora (router non registrato)**

```bash
python -m pytest tests/test_api_hrf.py -v
```
Risultato atteso: `404` su tutti gli endpoint (router non ancora in `main.py`).

- [ ] **Step 5: Registra il router in `main.py` (vedi Task 7) e riesegui**

Questo step viene completato nel Task 7. Passa al Task 7 e poi torna qui.

---

## Task 7 — Wire up in main.py + suite completa

**Files:**
- Modifica: `backend/app/main.py`

- [ ] **Step 1: Aggiorna `main.py`**

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import tutti i modelli PRIMA di create_all per registrarli a Base.metadata
from app.models.player import Player  # noqa: F401
from app.models.settings import CHPPSettings  # noqa: F401
from app.models.sync_log import SyncLog  # noqa: F401
from app.models.player_skill_history import PlayerSkillHistory  # noqa: F401
from app.models.hrf_settings import HRFSettings  # noqa: F401

from app.database import engine, Base

Base.metadata.create_all(bind=engine)

from app.migrations import run_migrations
run_migrations(engine)

app = FastAPI(title="Hattrick Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api import auth as auth_router
from app.api import demo as demo_router
from app.api import settings as settings_router
from app.api import squad as squad_router
from app.api import sync as sync_router
from app.api import hrf as hrf_router

app.include_router(auth_router.router, prefix="/api")
app.include_router(demo_router.router, prefix="/api")
app.include_router(settings_router.router, prefix="/api")
app.include_router(squad_router.router, prefix="/api")
app.include_router(sync_router.router, prefix="/api")
app.include_router(hrf_router.router, prefix="/api")
```

- [ ] **Step 2: Esegui la suite HRF completa**

```bash
cd /media/michel/Lavoro/source/myhattrick/backend
python -m pytest tests/test_api_hrf.py -v
```
Risultato atteso: `7 passed`

- [ ] **Step 3: Esegui la suite completa — zero regressioni**

```bash
python -m pytest tests/ -v
```
Risultato atteso: tutti i test passano, inclusi quelli pre-esistenti.

- [ ] **Step 4: Verifica avvio applicazione**

```bash
cd /media/michel/Lavoro/source/myhattrick
make dev
```
Attendi che il backend parta senza errori. Verifica con:
```bash
curl http://localhost:8000/api/hrf/settings
# Atteso: {"detail":"HRF not configured"}  (404)

curl -X POST http://localhost:8000/api/hrf/settings \
  -H "Content-Type: application/json" \
  -d '{"hrf_folder_path": "/program/ho/"}'
# Atteso: {"status":"ok"}

curl -X POST http://localhost:8000/api/hrf/scan
# Atteso: {"status":"ok","files_imported":N,"players_upserted":M,...}
```

- [ ] **Step 5: Commit finale**

```bash
git add backend/app/main.py
git commit -m "feat: register HRF router and fix model import order in main.py"
```

---

## Self-Review

### Copertura spec

| Requisito | Task |
|-----------|------|
| Parser INI formato HRF | Task 1–2 |
| Skip sezioni trainer (campi vuoti) | Task 2 (test_parse_hrf_skips_trainer) |
| Skip sezioni `youthplayer` | Task 1 (regex `^player\d+$`) |
| Scanner cartella con filtro data | Task 3 |
| Modello `PlayerSkillHistory` | Task 4 |
| Modello `HRFSettings` (path configurabile) | Task 4 |
| Estensione `Player` con 11 campi HRF | Task 5 |
| Auto-migrazione senza Alembic | Task 5 |
| CHPP intatto | Nessun file CHPP toccato |
| `GET/POST /api/hrf/settings` | Task 6 |
| `POST /api/hrf/scan` | Task 6 |
| `GET /api/hrf/files` | Task 6 |
| Idempotenza import (no duplicati) | Task 6 (test_scan_is_idempotent) |
| Wire up in main.py | Task 7 |

### Punti fuori scope (Piano B2)

- Endpoint `GET /api/players/{id}` e `/history`
- Endpoint `GET /api/training`
- Frontend `/players/:id` (LineChart + RadarChart ruoli)
- Frontend `/training` (delta skill)
- Nascondere sezione CHPP nell'UI frontend
