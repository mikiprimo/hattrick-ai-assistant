# Piano C — Partite: Formazioni e Classifica

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Aggiungere la pagina `/matches` che mostra, per ogni HRF importato, la formazione dell'ultima partita (lista compatta con navigazione prev/next) e l'andamento della classifica nel tempo (LineChart).

**Architecture:** Nuova tabella `match_snapshots` (una riga per HRF importato). Il parser HRF viene esteso per leggere `[basics]`, `[lastlineup]`, `[league]`. Lo scanner popola la tabella durante `POST /api/hrf/scan`. Il nuovo endpoint `GET /api/matches` restituisce la lista arricchita con i nomi dei giocatori.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.x, SQLite, configparser; React 18, TypeScript, TanStack Query, Recharts, inline styles.

**Nota:** Il progetto non usa git — omettere tutti i passi di commit.

---

## File map

| File | Azione |
|---|---|
| `backend/app/models/match_snapshot.py` | CREA — modello SQLAlchemy |
| `backend/app/main.py` | MODIFICA — importa MatchSnapshot, registra router matches |
| `backend/app/hrf/models.py` | MODIFICA — aggiunge HRFMatchData, estende HRFSnapshot |
| `backend/app/hrf/parser.py` | MODIFICA — aggiunge _parse_basics/_parse_lastlineup/_parse_league, estende parse_hrf_file |
| `backend/app/api/hrf.py` | MODIFICA — estende scan_and_import per upsertare MatchSnapshot |
| `backend/app/api/matches.py` | CREA — endpoint GET /api/matches |
| `backend/tests/fixtures/549298-2026-05-21.hrf` | CREA — fixture con dati completi per test scanner |
| `backend/tests/test_hrf_parser.py` | MODIFICA — aggiunge test per nuove funzioni parser |
| `backend/tests/test_api_hrf.py` | MODIFICA — aggiunge test upsert MatchSnapshot |
| `backend/tests/test_api_matches.py` | CREA — test endpoint matches |
| `frontend/src/api/matches.ts` | CREA — tipi e fetch function |
| `frontend/src/pages/Matches.tsx` | CREA — pagina con formazione e classifica |
| `frontend/src/App.tsx` | MODIFICA — route + link nav |

---

## Task 1: Modello MatchSnapshot

**Files:**
- Create: `backend/app/models/match_snapshot.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_api_matches.py` (solo setup iniziale)

- [ ] **Step 1: Scrivi il test che verifica la creazione del modello**

```python
# backend/tests/test_api_matches.py
from datetime import datetime
import json
from app.models.match_snapshot import MatchSnapshot


def _snap(db, date=datetime(2026, 5, 20), season=82, matchround=5,
          position=2, points=10, played=4, gf=8, ga=3,
          lineup=None, ratings=None):
    s = MatchSnapshot(
        snapshot_date=date,
        season=season,
        matchround=matchround,
        league_position=position,
        league_points=points,
        league_played=played,
        league_goals_for=gf,
        league_goals_against=ga,
        lineup_json=json.dumps(lineup or {}),
        ratings_json=json.dumps(ratings or {}),
    )
    db.add(s)
    db.commit()
    return s


def test_match_snapshot_model(db):
    s = _snap(db)
    fetched = db.query(MatchSnapshot).first()
    assert fetched.season == 82
    assert fetched.matchround == 5
    assert fetched.league_position == 2
    assert fetched.league_points == 10
```

- [ ] **Step 2: Esegui il test — deve fallire (ImportError)**

```bash
cd /media/michel/Lavoro/source/myhattrick/backend
python -m pytest tests/test_api_matches.py::test_match_snapshot_model -v
```

Expected: `ImportError: cannot import name 'MatchSnapshot'`

- [ ] **Step 3: Crea il modello**

```python
# backend/app/models/match_snapshot.py
from datetime import datetime
from sqlalchemy import Integer, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class MatchSnapshot(Base):
    __tablename__ = "match_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, unique=True)
    season: Mapped[int] = mapped_column(Integer, default=0)
    matchround: Mapped[int] = mapped_column(Integer, default=0)
    league_position: Mapped[int] = mapped_column(Integer, default=0)
    league_points: Mapped[int] = mapped_column(Integer, default=0)
    league_played: Mapped[int] = mapped_column(Integer, default=0)
    league_goals_for: Mapped[int] = mapped_column(Integer, default=0)
    league_goals_against: Mapped[int] = mapped_column(Integer, default=0)
    lineup_json: Mapped[str] = mapped_column(String, default="{}")
    ratings_json: Mapped[str] = mapped_column(String, default="{}")
```

- [ ] **Step 4: Aggiungi import in main.py**

Nel file `backend/app/main.py`, aggiungi questa riga subito dopo gli altri import di modelli (dopo la riga con `HRFSettings`):

```python
from app.models.match_snapshot import MatchSnapshot  # noqa: F401
```

La sezione import modelli in main.py diventa:

```python
from app.models.player import Player  # noqa: F401
from app.models.settings import CHPPSettings  # noqa: F401
from app.models.sync_log import SyncLog  # noqa: F401
from app.models.player_skill_history import PlayerSkillHistory  # noqa: F401
from app.models.hrf_settings import HRFSettings  # noqa: F401
from app.models.match_snapshot import MatchSnapshot  # noqa: F401
```

- [ ] **Step 5: Esegui il test — deve passare**

```bash
python -m pytest tests/test_api_matches.py::test_match_snapshot_model -v
```

Expected: PASSED

---

## Task 2: Estensioni HRF parser

**Files:**
- Create: `backend/tests/fixtures/549298-2026-05-21.hrf`
- Modify: `backend/app/hrf/models.py`
- Modify: `backend/app/hrf/parser.py`
- Modify: `backend/tests/test_hrf_parser.py`

- [ ] **Step 1: Crea il fixture HRF completo**

```ini
# backend/tests/fixtures/549298-2026-05-21.hrf
[basics]
application=HO
teamID=549298
teamName=Test FC
date=2026-05-21 10:00:00
season=82
matchround=5

[league]
serie=VII.935
spelade=4
gjorda=8
inslappta=3
poang=10
placering=2

[lastlineup]
trainer=295000001
installning=0
tactictype=0
keeper=100001
rightBack=100002
insideBack1=-1
insideBack2=0
insideBack3=0
leftBack=0
rightWinger=0
insideMid1=0
insideMid2=0
insideMid3=0
leftWinger=0
forward1=0
forward2=0
forward3=0
substBack=0
substInsideMid=0
substWinger=0
substKeeper=0
substForward=0
captain=100001
kicker1=100001

[player100001]
name=Mario Rossi
firstname=Mario
lastname=Rossi
ald=25
agedays=101
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
gev=16
loy=18
mkt=45000
sal=80000
speciality=0
specialityLabel=
TransferListed=False
CountryID=4
homegr=True
rating=7
PlayerNumber=1

[player100002]
name=Luca Bianchi
firstname=Luca
lastname=Bianchi
ald=30
agedays=51
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
gev=21
loy=15
mkt=30000
sal=60000
speciality=2
specialityLabel=Veloce
TransferListed=True
CountryID=7
homegr=False
rating=0
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

- [ ] **Step 2: Scrivi i test per le nuove funzioni parser**

Aggiungi alla fine di `backend/tests/test_hrf_parser.py`:

```python
import configparser as _cp
from app.hrf.parser import _parse_basics, _parse_lastlineup, _parse_league


def _make_cfg(text: str) -> _cp.ConfigParser:
    cfg = _cp.ConfigParser()
    cfg.optionxform = str
    cfg.read_string(text)
    return cfg


def test_parse_basics_extracts_season_and_matchround():
    cfg = _make_cfg("[basics]\nseason=82\nmatchround=5\n")
    season, matchround = _parse_basics(cfg)
    assert season == 82
    assert matchround == 5


def test_parse_basics_missing_fields_returns_zeros():
    cfg = _make_cfg("[basics]\napplication=HO\n")
    season, matchround = _parse_basics(cfg)
    assert season == 0
    assert matchround == 0


def test_parse_lastlineup_includes_valid_positions():
    cfg = _make_cfg(
        "[lastlineup]\nkeeper=100001\nrightBack=100002\n"
        "insideBack1=-1\ninsideBack2=0\n"
    )
    lineup = _parse_lastlineup(cfg)
    assert lineup == {"keeper": 100001, "rightBack": 100002}


def test_parse_lastlineup_excludes_zero_and_minus_one():
    cfg = _make_cfg("[lastlineup]\nkeeper=0\nrightBack=-1\nforward1=100003\n")
    lineup = _parse_lastlineup(cfg)
    assert "keeper" not in lineup
    assert "rightBack" not in lineup
    assert lineup["forward1"] == 100003


def test_parse_lastlineup_missing_section_returns_empty():
    cfg = _make_cfg("[basics]\nseason=1\n")
    assert _parse_lastlineup(cfg) == {}


def test_parse_league_extracts_all_fields():
    cfg = _make_cfg(
        "[league]\nspelade=4\ngjorda=8\ninslappta=3\npoang=10\nplacering=2\n"
    )
    league = _parse_league(cfg)
    assert league == {"position": 2, "points": 10, "played": 4, "goals_for": 8, "goals_against": 3}


def test_parse_league_missing_section_returns_empty():
    cfg = _make_cfg("[basics]\nseason=1\n")
    assert _parse_league(cfg) == {}


def test_parse_hrf_file_populates_match_data():
    snapshot = parse_hrf_file(str(FIXTURES / "549298-2026-05-21.hrf"))
    md = snapshot.match_data
    assert md is not None
    assert md.season == 82
    assert md.matchround == 5
    assert md.league_position == 2
    assert md.league_points == 10
    assert md.lineup == {"keeper": 100001, "rightBack": 100002}
    assert md.ratings[100001] == 7
    assert md.ratings[100002] == 0


def test_parse_hrf_file_match_data_excludes_empty_lineup_positions():
    snapshot = parse_hrf_file(str(FIXTURES / "549298-2026-05-21.hrf"))
    lineup = snapshot.match_data.lineup
    assert "insideBack1" not in lineup
    assert "insideBack2" not in lineup
```

- [ ] **Step 3: Esegui i test — devono fallire (ImportError)**

```bash
python -m pytest tests/test_hrf_parser.py::test_parse_basics_extracts_season_and_matchround -v
```

Expected: `ImportError: cannot import name '_parse_basics'`

- [ ] **Step 4: Aggiungi HRFMatchData e aggiorna HRFSnapshot in hrf/models.py**

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
class HRFMatchData:
    season: int
    matchround: int
    league_position: int
    league_points: int
    league_played: int
    league_goals_for: int
    league_goals_against: int
    lineup: dict[str, int]
    ratings: dict[int, int]


@dataclass
class HRFSnapshot:
    team_id: int
    snapshot_date: datetime
    file_path: str
    players: list[HRFPlayer] = field(default_factory=list)
    match_data: Optional[HRFMatchData] = None
```

- [ ] **Step 5: Aggiorna parser.py con le nuove funzioni e parse_hrf_file estesa**

```python
# backend/app/hrf/parser.py
import re
import configparser
from datetime import datetime
from pathlib import Path
from typing import Optional
from app.hrf.models import HRFPlayer, HRFMatchData, HRFSnapshot

_FILENAME_RE = re.compile(r'^(\d+)-(\d{4}-\d{2}-\d{2})\.hrf$')
_PLAYER_SECTION_RE = re.compile(r'^player(\d+)$')

_LINEUP_KEYS = [
    "keeper", "rightBack", "insideBack1", "insideBack2", "insideBack3", "leftBack",
    "rightWinger", "insideMid1", "insideMid2", "insideMid3", "leftWinger",
    "forward1", "forward2", "forward3",
    "substBack", "substInsideMid", "substWinger", "substKeeper", "substForward",
]


def _extract_filename_metadata(filename: str) -> tuple[int, datetime]:
    m = _FILENAME_RE.match(filename)
    if not m:
        raise ValueError(f"Invalid HRF filename: {filename}")
    return int(m.group(1)), datetime.strptime(m.group(2), "%Y-%m-%d")


def _parse_basics(cfg: configparser.ConfigParser) -> tuple[int, int]:
    if "basics" not in cfg:
        return 0, 0
    sec = cfg["basics"]
    try:
        season = int(sec.get("season", "0"))
    except (ValueError, TypeError):
        season = 0
    try:
        matchround = int(sec.get("matchround", "0"))
    except (ValueError, TypeError):
        matchround = 0
    return season, matchround


def _parse_lastlineup(cfg: configparser.ConfigParser) -> dict[str, int]:
    if "lastlineup" not in cfg:
        return {}
    sec = cfg["lastlineup"]
    lineup: dict[str, int] = {}
    for key in _LINEUP_KEYS:
        val_str = sec.get(key, "0").strip()
        try:
            val = int(val_str)
        except (ValueError, TypeError):
            continue
        if val > 0:
            lineup[key] = val
    return lineup


def _parse_league(cfg: configparser.ConfigParser) -> dict[str, int]:
    if "league" not in cfg:
        return {}
    sec = cfg["league"]

    def i(k: str) -> int:
        try:
            return int(sec.get(k, "0"))
        except (ValueError, TypeError):
            return 0

    return {
        "position": i("placering"),
        "points": i("poang"),
        "played": i("spelade"),
        "goals_for": i("gjorda"),
        "goals_against": i("inslappta"),
    }


def parse_hrf_file(file_path: str) -> HRFSnapshot:
    path = Path(file_path)
    team_id, snapshot_date = _extract_filename_metadata(path.name)

    cfg = configparser.ConfigParser()
    cfg.optionxform = str
    try:
        cfg.read(str(path), encoding="utf-8")
    except UnicodeDecodeError:
        cfg = configparser.ConfigParser()
        cfg.optionxform = str
        cfg.read(str(path), encoding="latin-1")

    players = []
    ratings: dict[int, int] = {}
    for section in cfg.sections():
        m = _PLAYER_SECTION_RE.match(section)
        if not m:
            continue
        pid = int(m.group(1))
        sec = cfg[section]
        try:
            ratings[pid] = int(sec.get("rating", "0").strip())
        except (ValueError, TypeError):
            ratings[pid] = 0
        if not sec.get("firstname", "").strip():
            continue
        players.append(_parse_player(pid, sec))

    season, matchround = _parse_basics(cfg)
    lineup = _parse_lastlineup(cfg)
    league = _parse_league(cfg)

    match_data = HRFMatchData(
        season=season,
        matchround=matchround,
        league_position=league.get("position", 0),
        league_points=league.get("points", 0),
        league_played=league.get("played", 0),
        league_goals_for=league.get("goals_for", 0),
        league_goals_against=league.get("goals_against", 0),
        lineup=lineup,
        ratings=ratings,
    )

    return HRFSnapshot(team_id=team_id, snapshot_date=snapshot_date,
                       file_path=str(path), players=players, match_data=match_data)


def _parse_player(player_id: int, sec: configparser.SectionProxy) -> HRFPlayer:
    def i(key: str, default: int = 0) -> int:
        raw = sec.get(key, "").strip()
        if not raw:
            return default
        try:
            return int(raw)
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

- [ ] **Step 6: Esegui tutti i nuovi test parser — devono passare**

```bash
python -m pytest tests/test_hrf_parser.py -v
```

Expected: tutti PASSED (i test esistenti + i nuovi 9)

---

## Task 3: HRF scan salva MatchSnapshot

**Files:**
- Modify: `backend/app/api/hrf.py`
- Modify: `backend/tests/test_api_hrf.py`

- [ ] **Step 1: Scrivi i test per l'upsert MatchSnapshot**

Aggiungi alla fine di `backend/tests/test_api_hrf.py`:

```python
def test_scan_creates_match_snapshot(client_with_hrf_db, tmp_path):
    import shutil
    from app.models.match_snapshot import MatchSnapshot
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
    import json
    lineup = json.loads(ms.lineup_json)
    assert lineup["keeper"] == 100001
    assert "insideBack1" not in lineup


def test_scan_match_snapshot_is_idempotent(client_with_hrf_db, tmp_path):
    import shutil
    from app.models.match_snapshot import MatchSnapshot
    client, db, _tmp = client_with_hrf_db
    shutil.copy(FIXTURES / "549298-2026-05-21.hrf", tmp_path)
    client.post("/api/hrf/settings", json={"hrf_folder_path": str(tmp_path)})

    client.post("/api/hrf/scan")
    client.post("/api/hrf/scan")  # secondo scan

    assert db.query(MatchSnapshot).count() == 1
```

- [ ] **Step 2: Esegui i test — devono fallire**

```bash
python -m pytest tests/test_api_hrf.py::test_scan_creates_match_snapshot -v
```

Expected: FAILED — il scan non crea ancora MatchSnapshot

- [ ] **Step 3: Estendi scan_and_import in hrf.py**

Sostituisci il contenuto di `backend/app/api/hrf.py` con:

```python
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.hrf_settings import HRFSettings
from app.models.match_snapshot import MatchSnapshot
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

        if snapshot.match_data:
            md = snapshot.match_data
            ms_data = {
                "season": md.season,
                "matchround": md.matchround,
                "league_position": md.league_position,
                "league_points": md.league_points,
                "league_played": md.league_played,
                "league_goals_for": md.league_goals_for,
                "league_goals_against": md.league_goals_against,
                "lineup_json": json.dumps(md.lineup),
                "ratings_json": json.dumps({str(k): v for k, v in md.ratings.items()}),
            }
            existing_ms = db.query(MatchSnapshot).filter_by(
                snapshot_date=snapshot.snapshot_date
            ).first()
            if existing_ms:
                for k, v in ms_data.items():
                    setattr(existing_ms, k, v)
            else:
                db.add(MatchSnapshot(snapshot_date=snapshot.snapshot_date, **ms_data))

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

    imported_dates = {
        row.snapshot_date.date()
        for row in db.query(PlayerSkillHistory.snapshot_date).distinct()
    }

    files = []
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

- [ ] **Step 4: Esegui tutti i test HRF — devono passare**

```bash
python -m pytest tests/test_api_hrf.py -v
```

Expected: tutti PASSED (test esistenti + 2 nuovi)

---

## Task 4: Endpoint GET /api/matches

**Files:**
- Create: `backend/app/api/matches.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_api_matches.py`

- [ ] **Step 1: Aggiungi i test dell'endpoint in test_api_matches.py**

Sostituisci `backend/tests/test_api_matches.py` con il contenuto completo:

```python
from datetime import datetime
import json
from app.models.match_snapshot import MatchSnapshot
from app.models.player import Player


def _snap(db, date=datetime(2026, 5, 20), season=82, matchround=5,
          position=2, points=10, played=4, gf=8, ga=3,
          lineup=None, ratings=None):
    s = MatchSnapshot(
        snapshot_date=date,
        season=season,
        matchround=matchround,
        league_position=position,
        league_points=points,
        league_played=played,
        league_goals_for=gf,
        league_goals_against=ga,
        lineup_json=json.dumps(lineup or {}),
        ratings_json=json.dumps(ratings or {}),
    )
    db.add(s)
    db.commit()
    return s


def test_match_snapshot_model(db):
    s = _snap(db)
    fetched = db.query(MatchSnapshot).first()
    assert fetched.season == 82
    assert fetched.matchround == 5
    assert fetched.league_position == 2
    assert fetched.league_points == 10


def test_get_matches_empty(client):
    r = client.get("/api/matches")
    assert r.status_code == 200
    assert r.json() == []


def test_get_matches_returns_league_data(client, db):
    _snap(db, position=2, points=10, played=4, gf=8, ga=3)
    data = client.get("/api/matches").json()
    assert len(data) == 1
    league = data[0]["league"]
    assert league["position"] == 2
    assert league["points"] == 10
    assert league["played"] == 4
    assert league["goals_for"] == 8
    assert league["goals_against"] == 3


def test_get_matches_lineup_enriched_with_player_name(client, db):
    db.add(Player(id=100001, first_name="Mario", last_name="Rossi"))
    _snap(db, lineup={"keeper": 100001}, ratings={"100001": 7})
    data = client.get("/api/matches").json()
    lineup = data[0]["lineup"]
    assert len(lineup) == 1
    assert lineup[0]["name"] == "Mario Rossi"
    assert lineup[0]["rating"] == 7
    assert lineup[0]["line"] == "GK"
    assert lineup[0]["position"] == "Portiere"


def test_get_matches_unknown_player_shows_id(client, db):
    _snap(db, lineup={"keeper": 999999}, ratings={"999999": 5})
    data = client.get("/api/matches").json()
    assert data[0]["lineup"][0]["name"] == "#999999"


def test_get_matches_rating_zero_becomes_null(client, db):
    db.add(Player(id=100001, first_name="Mario", last_name="Rossi"))
    _snap(db, lineup={"keeper": 100001}, ratings={"100001": 0})
    data = client.get("/api/matches").json()
    assert data[0]["lineup"][0]["rating"] is None


def test_get_matches_empty_positions_excluded(client, db):
    db.add(Player(id=100001, first_name="Mario", last_name="Rossi"))
    # rightBack è 0 (posizione vuota) → non deve comparire nel lineup
    _snap(db, lineup={"keeper": 100001, "rightBack": 0}, ratings={"100001": 7})
    data = client.get("/api/matches").json()
    assert len(data[0]["lineup"]) == 1
    assert data[0]["lineup"][0]["position"] == "Portiere"


def test_get_matches_ordered_most_recent_first(client, db):
    _snap(db, date=datetime(2026, 5, 13), season=82, matchround=4, position=3, points=7,
          played=3, gf=5, ga=2)
    _snap(db, date=datetime(2026, 5, 20), season=82, matchround=5, position=2, points=10,
          played=4, gf=8, ga=3)
    data = client.get("/api/matches").json()
    assert data[0]["matchround"] == 5
    assert data[1]["matchround"] == 4


def test_get_matches_season_and_matchround(client, db):
    _snap(db, season=82, matchround=5)
    data = client.get("/api/matches").json()
    assert data[0]["season"] == 82
    assert data[0]["matchround"] == 5
    assert data[0]["snapshot_date"] == "2026-05-20"
```

- [ ] **Step 2: Esegui i test nuovi — devono fallire (404)**

```bash
python -m pytest tests/test_api_matches.py::test_get_matches_empty -v
```

Expected: FAILED — endpoint non esiste ancora

- [ ] **Step 3: Crea matches.py**

```python
# backend/app/api/matches.py
import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.match_snapshot import MatchSnapshot
from app.models.player import Player

router = APIRouter()

_LINEUP_MAP = [
    ("keeper",        "GK",          "Portiere"),
    ("rightBack",     "Difesa",      "Terzino Dx"),
    ("insideBack1",   "Difesa",      "Difensore Cen"),
    ("insideBack2",   "Difesa",      "Difensore Cen"),
    ("insideBack3",   "Difesa",      "Difensore Cen"),
    ("leftBack",      "Difesa",      "Terzino Sx"),
    ("rightWinger",   "Centrocampo", "Ala Dx"),
    ("insideMid1",    "Centrocampo", "Centrocampista"),
    ("insideMid2",    "Centrocampo", "Centrocampista"),
    ("insideMid3",    "Centrocampo", "Centrocampista"),
    ("leftWinger",    "Centrocampo", "Ala Sx"),
    ("forward1",      "Attacco",     "Attaccante"),
    ("forward2",      "Attacco",     "Attaccante"),
    ("forward3",      "Attacco",     "Attaccante"),
    ("substBack",     "Panchina",    "Riserva Dif"),
    ("substInsideMid","Panchina",    "Riserva Cen"),
    ("substWinger",   "Panchina",    "Riserva Ala"),
    ("substKeeper",   "Panchina",    "Riserva Por"),
    ("substForward",  "Panchina",    "Riserva Att"),
]


@router.get("/matches")
def get_matches(db: Session = Depends(get_db)):
    snapshots = (
        db.query(MatchSnapshot)
        .order_by(MatchSnapshot.snapshot_date.desc())
        .all()
    )

    result = []
    for s in snapshots:
        lineup_map: dict[str, int] = json.loads(s.lineup_json)
        ratings_map: dict[str, int] = json.loads(s.ratings_json)

        player_ids = list(lineup_map.values())
        players = {
            p.id: p
            for p in db.query(Player).filter(Player.id.in_(player_ids)).all()
        }

        lineup = []
        for position_key, line, label in _LINEUP_MAP:
            player_id = lineup_map.get(position_key)
            if not player_id:
                continue
            p = players.get(player_id)
            name = f"{p.first_name} {p.last_name}" if p else f"#{player_id}"
            raw_rating = ratings_map.get(str(player_id), 0)
            lineup.append({
                "line": line,
                "position": label,
                "player_id": player_id,
                "name": name,
                "rating": raw_rating if raw_rating != 0 else None,
            })

        result.append({
            "snapshot_date": s.snapshot_date.strftime("%Y-%m-%d"),
            "season": s.season,
            "matchround": s.matchround,
            "lineup": lineup,
            "league": {
                "position": s.league_position,
                "points": s.league_points,
                "played": s.league_played,
                "goals_for": s.league_goals_for,
                "goals_against": s.league_goals_against,
            },
        })

    return result
```

- [ ] **Step 4: Registra il router in main.py**

Aggiungi import e include_router in `backend/app/main.py`:

```python
# Aggiungi dopo gli altri import di router (dopo training_router):
from app.api import matches as matches_router

# Aggiungi dopo app.include_router(training_router.router, prefix="/api"):
app.include_router(matches_router.router, prefix="/api")
```

La sezione finale di main.py diventa:

```python
from app.api import auth as auth_router
from app.api import demo as demo_router
from app.api import settings as settings_router
from app.api import squad as squad_router
from app.api import sync as sync_router
from app.api import hrf as hrf_router
from app.api import players as players_router
from app.api import training as training_router
from app.api import matches as matches_router

app.include_router(auth_router.router, prefix="/api")
app.include_router(demo_router.router, prefix="/api")
app.include_router(settings_router.router, prefix="/api")
app.include_router(squad_router.router, prefix="/api")
app.include_router(sync_router.router, prefix="/api")
app.include_router(hrf_router.router, prefix="/api")
app.include_router(players_router.router, prefix="/api")
app.include_router(training_router.router, prefix="/api")
app.include_router(matches_router.router, prefix="/api")
```

- [ ] **Step 5: Esegui tutti i test matches — devono passare**

```bash
python -m pytest tests/test_api_matches.py -v
```

Expected: tutti PASSED (9 test)

- [ ] **Step 6: Esegui la suite completa per verificare nessuna regressione**

```bash
python -m pytest -v
```

Expected: tutti PASSED

---

## Task 5: Frontend — pagina Matches

**Files:**
- Create: `frontend/src/api/matches.ts`
- Create: `frontend/src/pages/Matches.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Crea matches.ts**

```typescript
// frontend/src/api/matches.ts
import { apiFetch } from './client'

export interface LineupEntry {
  line: string
  position: string
  player_id: number
  name: string
  rating: number | null
}

export interface LeagueData {
  position: number
  points: number
  played: number
  goals_for: number
  goals_against: number
}

export interface Match {
  snapshot_date: string
  season: number
  matchround: number
  lineup: LineupEntry[]
  league: LeagueData
}

export function getMatches(): Promise<Match[]> {
  return apiFetch<Match[]>('/api/matches')
}
```

- [ ] **Step 2: Crea Matches.tsx**

```tsx
// frontend/src/pages/Matches.tsx
import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import { getMatches } from '../api/matches'
import { HrfScanButton } from '../components/HrfScanButton'
import type { LineupEntry } from '../api/matches'

const card: React.CSSProperties = {
  background: '#fff',
  borderRadius: 8,
  border: '1px solid #e5e7eb',
  padding: '16px 20px',
  marginBottom: 24,
}

const LINE_ORDER = ['GK', 'Difesa', 'Centrocampo', 'Attacco', 'Panchina']

function groupByLine(lineup: LineupEntry[]): [string, LineupEntry[]][] {
  const groups: Record<string, LineupEntry[]> = {}
  for (const entry of lineup) {
    if (!groups[entry.line]) groups[entry.line] = []
    groups[entry.line].push(entry)
  }
  return LINE_ORDER.filter(l => groups[l]).map(l => [l, groups[l]])
}

export function Matches() {
  const qc = useQueryClient()
  const [selectedIdx, setSelectedIdx] = useState(0)

  const { data: matches = [], isLoading, error } = useQuery({
    queryKey: ['matches'],
    queryFn: getMatches,
  })

  const match = matches[selectedIdx]

  const chartData = [...matches].reverse().map(m => ({
    label: `S${m.season} T${m.matchround}`,
    Punti: m.league.points,
    Posizione: m.league.position,
  }))

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h1 style={{ margin: 0 }}>Partite</h1>
        <HrfScanButton onScanned={() => {
          qc.invalidateQueries({ queryKey: ['matches'] })
        }} />
      </div>

      {isLoading && <p>Caricamento…</p>}
      {error && <p style={{ color: '#ef4444' }}>Errore: {(error as Error).message}</p>}

      {!isLoading && matches.length === 0 && (
        <p style={{ color: '#6b7280' }}>
          Nessuna partita trovata. Importa i file HRF per vedere le formazioni.
        </p>
      )}

      {match && (
        <div style={card}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 16 }}>
            <button
              onClick={() => setSelectedIdx(i => i + 1)}
              disabled={selectedIdx >= matches.length - 1}
              style={{
                padding: '4px 12px', borderRadius: 6, border: '1px solid #d1d5db',
                background: '#fff', cursor: selectedIdx >= matches.length - 1 ? 'not-allowed' : 'pointer',
                color: selectedIdx >= matches.length - 1 ? '#d1d5db' : '#374151',
              }}
            >←</button>

            <span style={{ fontWeight: 600, fontSize: 15 }}>
              Stagione {match.season} — Turno {match.matchround}
            </span>
            <span style={{ color: '#9ca3af', fontSize: 13 }}>{match.snapshot_date}</span>

            <button
              onClick={() => setSelectedIdx(i => i - 1)}
              disabled={selectedIdx === 0}
              style={{
                padding: '4px 12px', borderRadius: 6, border: '1px solid #d1d5db',
                background: '#fff', cursor: selectedIdx === 0 ? 'not-allowed' : 'pointer',
                color: selectedIdx === 0 ? '#d1d5db' : '#374151',
              }}
            >→</button>
          </div>

          {match.lineup.length === 0 ? (
            <p style={{ color: '#9ca3af', fontSize: 13 }}>Formazione non disponibile.</p>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #e5e7eb', color: '#9ca3af', textAlign: 'left' }}>
                  <th style={{ padding: '4px 8px', fontWeight: 500 }}>Reparto</th>
                  <th style={{ padding: '4px 8px', fontWeight: 500 }}>Posizione</th>
                  <th style={{ padding: '4px 8px', fontWeight: 500 }}>Giocatore</th>
                  <th style={{ padding: '4px 8px', fontWeight: 500, textAlign: 'right' }}>Voto</th>
                </tr>
              </thead>
              <tbody>
                {groupByLine(match.lineup).map(([line, entries]) =>
                  entries.map((e, i) => (
                    <tr key={`${e.position}-${e.player_id}`}
                        style={{ borderBottom: '1px solid #f3f4f6' }}>
                      <td style={{ padding: '5px 8px', color: '#6b7280' }}>
                        {i === 0 ? line : ''}
                      </td>
                      <td style={{ padding: '5px 8px', color: '#6b7280' }}>{e.position}</td>
                      <td style={{ padding: '5px 8px', fontWeight: 500 }}>{e.name}</td>
                      <td style={{ padding: '5px 8px', textAlign: 'right', color: e.rating ? '#374151' : '#d1d5db' }}>
                        {e.rating ?? '—'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          )}
        </div>
      )}

      {chartData.length > 0 && (
        <div style={card}>
          <h2 style={{ margin: '0 0 16px', fontSize: 16 }}>Classifica nel tempo</h2>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={chartData} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} />
              <YAxis yAxisId="left" tick={{ fontSize: 11 }} />
              <YAxis yAxisId="right" orientation="right" reversed tick={{ fontSize: 11 }} />
              <Tooltip />
              <Legend />
              <Line yAxisId="left" type="monotone" dataKey="Punti"
                    stroke="#3b82f6" dot={{ r: 3 }} activeDot={{ r: 5 }} />
              <Line yAxisId="right" type="monotone" dataKey="Posizione"
                    stroke="#f59e0b" dot={{ r: 3 }} activeDot={{ r: 5 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 3: Aggiorna App.tsx con route e link nav**

```tsx
// frontend/src/App.tsx
import { createBrowserRouter, RouterProvider, NavLink, Outlet } from 'react-router-dom'
import { Dashboard } from './pages/Dashboard'
import { Squad } from './pages/Squad'
import { Settings } from './pages/Settings'
import { PlayerDetail } from './pages/PlayerDetail'
import { Training } from './pages/Training'
import { Matches } from './pages/Matches'

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
        <NavLink to="/training" style={navStyle}>Allenamento</NavLink>
        <NavLink to="/matches" style={navStyle}>Partite</NavLink>
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
      { path: 'players/:id', element: <PlayerDetail /> },
      { path: 'training', element: <Training /> },
      { path: 'matches', element: <Matches /> },
      { path: 'settings', element: <Settings /> },
    ],
  },
])

export default function App() {
  return <RouterProvider router={router} />
}
```

- [ ] **Step 4: Verifica TypeScript — nessun errore di tipo**

```bash
cd /media/michel/Lavoro/source/myhattrick/frontend
npx tsc --noEmit
```

Expected: nessun errore

- [ ] **Step 5: Esegui la suite backend completa — nessuna regressione**

```bash
cd /media/michel/Lavoro/source/myhattrick/backend
python -m pytest -v
```

Expected: tutti PASSED
