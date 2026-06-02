# Piano B2: Player Analysis — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add PlayerDetail page (skill history line chart + role radar chart) and Training page (skill delta table between consecutive HRF snapshots) to the Hattrick Dashboard.

**Architecture:** Two new backend routers (`/api/players/{id}`, `/api/players/{id}/history`, `/api/training`) query the existing `players` and `player_skill_history` tables. Three new frontend pages (PlayerDetail, Training) consume these endpoints via TanStack Query. Squad player names become clickable links. Settings page gains an HRF section (folder path + scan button) and the CHPP section is hidden under a `<details>` toggle.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2.x, SQLite, pytest; React 19, Vite, TypeScript, TanStack Query v5, Recharts 3.8.1, React Router v7; inline CSS throughout (no Tailwind).

**Important:** No git in this project — skip all commit steps. Backend tests use `conftest.py` fixtures `db` + `client` (already in `backend/tests/conftest.py`). Frontend has no test files.

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `backend/app/api/players.py` | Create | GET /api/players/{id} + GET /api/players/{id}/history |
| `backend/app/api/training.py` | Create | GET /api/training (skill deltas) |
| `backend/tests/test_api_players.py` | Create | Tests for players endpoints |
| `backend/tests/test_api_training.py` | Create | Tests for training endpoint |
| `backend/app/main.py` | Modify | Register players + training routers |
| `backend/app/api/squad.py` | Modify | Extend PLAYER_FIELDS with HRF fields |
| `frontend/src/api/squad.ts` | Modify | Extend Player interface with HRF fields |
| `frontend/src/api/players.ts` | Create | getPlayer(), getPlayerHistory() |
| `frontend/src/api/hrf.ts` | Create | getHrfSettings(), saveHrfSettings(), scanHrf() |
| `frontend/src/api/training.ts` | Create | getTraining() |
| `frontend/src/components/HrfScanButton.tsx` | Create | Scan HRF files button (SyncButton pattern) |
| `frontend/src/components/DeltaBadge.tsx` | Create | +N / −N / — skill delta display |
| `frontend/src/components/SkillLineChart.tsx` | Create | Recharts LineChart for skill history |
| `frontend/src/components/RoleRadarChart.tsx` | Create | Recharts RadarChart for 6 Hattrick roles |
| `frontend/src/pages/PlayerDetail.tsx` | Create | Player detail page |
| `frontend/src/pages/Training.tsx` | Create | Training delta page |
| `frontend/src/App.tsx` | Modify | Add /players/:id and /training routes + nav |
| `frontend/src/pages/Squad.tsx` | Modify | Player names → links, add HrfScanButton |
| `frontend/src/pages/Settings.tsx` | Modify | Add HRF section, collapse CHPP to <details> |

---

### Task 1: Backend — `app/api/players.py`

**Files:**
- Create: `backend/app/api/players.py`
- Create: `backend/tests/test_api_players.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_api_players.py`:

```python
from datetime import datetime
from app.models.player import Player
from app.models.player_skill_history import PlayerSkillHistory


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
    assert data["playmaking"] == 9
    assert data["speed"] == 6
    assert data["leadership"] == 5
    assert data["market_value"] == 500000
    assert "data_source" in data


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
    assert "snapshot_date" in data[0]
    assert "form" in data[0]
    assert "leadership" in data[0]
```

- [ ] **Step 2: Run tests — expect FAIL (module not found)**

```bash
cd /media/michel/Lavoro/source/myhattrick/backend
python -m pytest tests/test_api_players.py -v 2>&1 | head -30
```

Expected: ImportError or 404 responses.

- [ ] **Step 3: Create `backend/app/api/players.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.player import Player
from app.models.player_skill_history import PlayerSkillHistory

router = APIRouter()

PLAYER_DETAIL_FIELDS = [
    "id", "first_name", "last_name", "age", "age_days", "tsi", "form",
    "stamina", "speed", "injury_days", "salary",
    "goalkeeper", "defending", "playmaking", "winger", "passing", "scoring", "set_pieces",
    "leadership", "experience", "loyalty", "market_value", "speciality",
    "last_match_rating", "transfer_listed", "country_id", "homegrown", "data_source",
]

HISTORY_SKILL_FIELDS = [
    "form", "stamina", "speed", "goalkeeper", "defending", "playmaking",
    "winger", "passing", "scoring", "set_pieces", "leadership", "experience", "loyalty",
]


@router.get("/players/{player_id}")
def get_player(player_id: int, db: Session = Depends(get_db)):
    p = db.get(Player, player_id)
    if not p:
        raise HTTPException(status_code=404, detail="Player not found")
    return {field: getattr(p, field, None) for field in PLAYER_DETAIL_FIELDS}


@router.get("/players/{player_id}/history")
def get_player_history(player_id: int, db: Session = Depends(get_db)):
    p = db.get(Player, player_id)
    if not p:
        raise HTTPException(status_code=404, detail="Player not found")
    rows = (
        db.query(PlayerSkillHistory)
        .filter_by(player_id=player_id)
        .order_by(PlayerSkillHistory.snapshot_date)
        .all()
    )
    return [
        {"snapshot_date": r.snapshot_date.isoformat(),
         **{f: getattr(r, f) for f in HISTORY_SKILL_FIELDS}}
        for r in rows
    ]
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
cd /media/michel/Lavoro/source/myhattrick/backend
python -m pytest tests/test_api_players.py -v
```

Expected: 5/5 passing.

---

### Task 2: Backend — `app/api/training.py`

**Files:**
- Create: `backend/app/api/training.py`
- Create: `backend/tests/test_api_training.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_api_training.py`:

```python
from datetime import datetime
from app.models.player import Player
from app.models.player_skill_history import PlayerSkillHistory


def _p(id: int, first: str, last: str) -> Player:
    return Player(
        id=id, first_name=first, last_name=last, age=24, age_days=0,
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


def test_training_empty(client):
    resp = client.get("/api/training")
    assert resp.status_code == 200
    assert resp.json() == []


def test_training_player_no_history(client, db):
    db.add(_p(1, "A", "B"))
    db.commit()
    resp = client.get("/api/training")
    assert resp.status_code == 200
    assert resp.json() == []


def test_training_player_one_snapshot(client, db):
    db.add(_p(2, "C", "D"))
    db.add(_snap(2, datetime(2026, 5, 20)))
    db.commit()
    resp = client.get("/api/training")
    assert resp.status_code == 200
    assert resp.json() == []


def test_training_two_snapshots(client, db):
    db.add(_p(3, "Mario", "Rossi"))
    db.add(_snap(3, datetime(2026, 5, 13), playmaking=8, stamina=7, speed=5, experience=5))
    db.add(_snap(3, datetime(2026, 5, 20), playmaking=9, stamina=8, speed=6, experience=6))
    db.commit()
    resp = client.get("/api/training")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    row = data[0]
    assert row["player_id"] == 3
    assert row["first_name"] == "Mario"
    assert row["last_name"] == "Rossi"
    assert row["deltas"]["playmaking"] == 1
    assert row["deltas"]["stamina"] == 1
    assert row["deltas"]["speed"] == 1
    assert row["deltas"]["experience"] == 1
    assert row["deltas"]["goalkeeper"] == 0
    assert "from_date" in row
    assert "to_date" in row


def test_training_multiple_players(client, db):
    db.add(_p(4, "A", "A"))
    db.add(_p(5, "B", "B"))
    db.add(_snap(4, datetime(2026, 5, 13), scoring=9))
    db.add(_snap(4, datetime(2026, 5, 20), scoring=10))
    db.add(_snap(5, datetime(2026, 5, 13), scoring=8))
    db.add(_snap(5, datetime(2026, 5, 20), scoring=8))
    db.commit()
    resp = client.get("/api/training")
    data = resp.json()
    assert len(data) == 2
    player_ids = {r["player_id"] for r in data}
    assert 4 in player_ids
    assert 5 in player_ids


def test_training_uses_last_two_snapshots(client, db):
    db.add(_p(6, "X", "Y"))
    db.add(_snap(6, datetime(2026, 5, 6), playmaking=7))
    db.add(_snap(6, datetime(2026, 5, 13), playmaking=8))
    db.add(_snap(6, datetime(2026, 5, 20), playmaking=9))
    db.commit()
    resp = client.get("/api/training")
    data = resp.json()
    assert len(data) == 1
    assert data[0]["deltas"]["playmaking"] == 1
    assert data[0]["from_date"].startswith("2026-05-13")
    assert data[0]["to_date"].startswith("2026-05-20")
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
cd /media/michel/Lavoro/source/myhattrick/backend
python -m pytest tests/test_api_training.py -v 2>&1 | head -30
```

Expected: ImportError or 404s.

- [ ] **Step 3: Create `backend/app/api/training.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.player import Player
from app.models.player_skill_history import PlayerSkillHistory

router = APIRouter()

SKILL_FIELDS = [
    "form", "stamina", "speed", "goalkeeper", "defending", "playmaking",
    "winger", "passing", "scoring", "set_pieces", "leadership", "experience", "loyalty",
]


@router.get("/training")
def get_training(db: Session = Depends(get_db)):
    players = db.query(Player).all()
    result = []
    for player in players:
        history = (
            db.query(PlayerSkillHistory)
            .filter_by(player_id=player.id)
            .order_by(PlayerSkillHistory.snapshot_date.desc())
            .limit(2)
            .all()
        )
        if len(history) < 2:
            continue
        newer, older = history[0], history[1]
        result.append({
            "player_id": player.id,
            "first_name": player.first_name,
            "last_name": player.last_name,
            "from_date": older.snapshot_date.isoformat(),
            "to_date": newer.snapshot_date.isoformat(),
            "deltas": {f: getattr(newer, f) - getattr(older, f) for f in SKILL_FIELDS},
        })
    result.sort(key=lambda x: (x["last_name"], x["first_name"]))
    return result
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
cd /media/michel/Lavoro/source/myhattrick/backend
python -m pytest tests/test_api_training.py -v
```

Expected: 6/6 passing.

---

### Task 3: Backend wiring + squad extension

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/api/squad.py`
- Modify: `frontend/src/api/squad.ts`

- [ ] **Step 1: Register new routers in `backend/app/main.py`**

Add after the existing `from app.api import hrf as hrf_router` line:

```python
from app.api import players as players_router
from app.api import training as training_router
```

Add after `app.include_router(hrf_router.router, prefix="/api")`:

```python
app.include_router(players_router.router, prefix="/api")
app.include_router(training_router.router, prefix="/api")
```

The complete updated section at the bottom of `backend/app/main.py`:

```python
from app.api import auth as auth_router
from app.api import demo as demo_router
from app.api import settings as settings_router
from app.api import squad as squad_router
from app.api import sync as sync_router
from app.api import hrf as hrf_router
from app.api import players as players_router
from app.api import training as training_router

app.include_router(auth_router.router, prefix="/api")
app.include_router(demo_router.router, prefix="/api")
app.include_router(settings_router.router, prefix="/api")
app.include_router(squad_router.router, prefix="/api")
app.include_router(sync_router.router, prefix="/api")
app.include_router(hrf_router.router, prefix="/api")
app.include_router(players_router.router, prefix="/api")
app.include_router(training_router.router, prefix="/api")
```

- [ ] **Step 2: Extend PLAYER_FIELDS in `backend/app/api/squad.py`**

Replace the `PLAYER_FIELDS` list:

```python
PLAYER_FIELDS = [
    "id", "first_name", "last_name", "age", "age_days", "tsi", "form",
    "stamina", "injury_days", "salary", "goalkeeper", "defending",
    "playmaking", "winger", "passing", "scoring", "set_pieces",
    "speed", "leadership", "experience", "loyalty",
    "market_value", "speciality", "last_match_rating",
    "transfer_listed", "data_source",
]
```

- [ ] **Step 3: Extend Player interface in `frontend/src/api/squad.ts`**

Replace the entire file:

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
  speed: number
  leadership: number
  experience: number
  loyalty: number
  market_value: number
  speciality: string | null
  last_match_rating: number | null
  transfer_listed: boolean
  data_source: string
}

export function getSquad(): Promise<Player[]> {
  return apiFetch<Player[]>('/api/squad')
}
```

- [ ] **Step 4: Run the full backend test suite to ensure nothing is broken**

```bash
cd /media/michel/Lavoro/source/myhattrick/backend
python -m pytest -v
```

Expected: all existing tests pass (35+) plus the 5 + 6 new ones (46+ total).

---

### Task 4: Frontend API clients

**Files:**
- Create: `frontend/src/api/players.ts`
- Create: `frontend/src/api/hrf.ts`
- Create: `frontend/src/api/training.ts`

- [ ] **Step 1: Create `frontend/src/api/players.ts`**

```typescript
import { apiFetch } from './client'

export interface PlayerDetail {
  id: number
  first_name: string
  last_name: string
  age: number
  age_days: number
  tsi: number
  form: number
  stamina: number
  speed: number
  injury_days: number
  salary: number
  goalkeeper: number
  defending: number
  playmaking: number
  winger: number
  passing: number
  scoring: number
  set_pieces: number
  leadership: number
  experience: number
  loyalty: number
  market_value: number
  speciality: string | null
  last_match_rating: number | null
  transfer_listed: boolean
  country_id: number | null
  homegrown: boolean
  data_source: string
}

export interface SkillSnapshot {
  snapshot_date: string
  form: number
  stamina: number
  speed: number
  goalkeeper: number
  defending: number
  playmaking: number
  winger: number
  passing: number
  scoring: number
  set_pieces: number
  leadership: number
  experience: number
  loyalty: number
}

export function getPlayer(id: number): Promise<PlayerDetail> {
  return apiFetch<PlayerDetail>(`/api/players/${id}`)
}

export function getPlayerHistory(id: number): Promise<SkillSnapshot[]> {
  return apiFetch<SkillSnapshot[]>(`/api/players/${id}/history`)
}
```

- [ ] **Step 2: Create `frontend/src/api/hrf.ts`**

```typescript
import { apiFetch } from './client'

export interface HrfSettings {
  hrf_folder_path: string
  team_id: number | null
  enabled: boolean
}

export interface HrfScanResult {
  status: string
  scanned_at: string
  files_imported: number
  players_upserted: number
}

export function getHrfSettings(): Promise<HrfSettings> {
  return apiFetch<HrfSettings>('/api/hrf/settings')
}

export function saveHrfSettings(settings: HrfSettings): Promise<{ status: string }> {
  return apiFetch<{ status: string }>('/api/hrf/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  })
}

export function scanHrf(): Promise<HrfScanResult> {
  return apiFetch<HrfScanResult>('/api/hrf/scan', { method: 'POST' })
}
```

- [ ] **Step 3: Create `frontend/src/api/training.ts`**

```typescript
import { apiFetch } from './client'

export type SkillKey =
  | 'form' | 'stamina' | 'speed' | 'goalkeeper' | 'defending' | 'playmaking'
  | 'winger' | 'passing' | 'scoring' | 'set_pieces' | 'leadership' | 'experience' | 'loyalty'

export interface TrainingDelta {
  player_id: number
  first_name: string
  last_name: string
  from_date: string
  to_date: string
  deltas: Record<SkillKey, number>
}

export function getTraining(): Promise<TrainingDelta[]> {
  return apiFetch<TrainingDelta[]>('/api/training')
}
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd /media/michel/Lavoro/source/myhattrick/frontend
npx tsc --noEmit 2>&1 | head -30
```

Expected: no errors (or only pre-existing errors unrelated to the new files).

---

### Task 5: Frontend components — `HrfScanButton` and `DeltaBadge`

**Files:**
- Create: `frontend/src/components/HrfScanButton.tsx`
- Create: `frontend/src/components/DeltaBadge.tsx`

- [ ] **Step 1: Create `frontend/src/components/HrfScanButton.tsx`**

Pattern mirrors `SyncButton.tsx` — same loading/error/result state pattern.

```tsx
import { useState } from 'react'
import { scanHrf } from '../api/hrf'

interface Props {
  onScanned?: () => void
}

export function HrfScanButton({ onScanned }: Props) {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<{ scanned_at: string; files_imported: number } | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function handleScan() {
    setLoading(true)
    setError(null)
    try {
      const r = await scanHrf()
      setResult({ scanned_at: r.scanned_at, files_imported: r.files_imported })
      onScanned?.()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Errore')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <button
        onClick={handleScan}
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
        {loading ? 'Importazione…' : 'Importa HRF'}
      </button>
      {result && (
        <span style={{ fontSize: 12, color: '#6b7280' }}>
          {result.files_imported} file — {new Date(result.scanned_at).toLocaleString('it-IT')}
        </span>
      )}
      {error && <span style={{ fontSize: 12, color: '#ef4444' }}>{error}</span>}
    </div>
  )
}
```

- [ ] **Step 2: Create `frontend/src/components/DeltaBadge.tsx`**

```tsx
interface Props {
  value: number
}

export function DeltaBadge({ value }: Props) {
  if (value === 0) return <span style={{ color: '#9ca3af', fontSize: 12 }}>—</span>
  const color = value > 0 ? '#16a34a' : '#dc2626'
  return (
    <span style={{ color, fontWeight: 600, fontSize: 13 }}>
      {value > 0 ? '+' : ''}{value}
    </span>
  )
}
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd /media/michel/Lavoro/source/myhattrick/frontend
npx tsc --noEmit 2>&1 | head -30
```

Expected: no new errors.

---

### Task 6: Frontend chart components

**Files:**
- Create: `frontend/src/components/SkillLineChart.tsx`
- Create: `frontend/src/components/RoleRadarChart.tsx`

- [ ] **Step 1: Create `frontend/src/components/SkillLineChart.tsx`**

```tsx
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import type { SkillSnapshot } from '../api/players'

const SKILL_COLORS: Record<string, string> = {
  goalkeeper: '#ef4444',
  defending: '#f97316',
  playmaking: '#eab308',
  winger: '#22c55e',
  passing: '#06b6d4',
  scoring: '#3b82f6',
  set_pieces: '#8b5cf6',
  stamina: '#ec4899',
  speed: '#14b8a6',
  leadership: '#a855f7',
  experience: '#f59e0b',
  loyalty: '#84cc16',
  form: '#6b7280',
}

const SKILL_LABELS: Record<string, string> = {
  goalkeeper: 'Portiere', defending: 'Difesa', playmaking: 'Centrocampo',
  winger: 'Ala', passing: 'Passaggi', scoring: 'Attacco',
  set_pieces: 'Cal. piazzati', stamina: 'Resistenza', speed: 'Velocità',
  leadership: 'Leadership', experience: 'Esperienza', loyalty: 'Fedeltà', form: 'Forma',
}

interface Props {
  history: SkillSnapshot[]
  skills: string[]
}

export function SkillLineChart({ history, skills }: Props) {
  const data = history.map((s) => ({
    date: s.snapshot_date.slice(0, 10),
    ...Object.fromEntries(skills.map((sk) => [sk, (s as Record<string, unknown>)[sk]])),
  }))

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey="date" tick={{ fontSize: 11 }} />
        <YAxis domain={[0, 20]} tick={{ fontSize: 11 }} width={24} />
        <Tooltip />
        <Legend formatter={(value) => SKILL_LABELS[value] ?? value} />
        {skills.map((sk) => (
          <Line
            key={sk}
            type="monotone"
            dataKey={sk}
            name={sk}
            stroke={SKILL_COLORS[sk] ?? '#6b7280'}
            strokeWidth={2}
            dot={{ r: 3 }}
            activeDot={{ r: 5 }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}
```

- [ ] **Step 2: Create `frontend/src/components/RoleRadarChart.tsx`**

Role scores use weighted sums of the six main Hattrick skills (scale 0–20, same as individual skills). Formulas approximate the HO role model for visualization.

```tsx
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
  PolarRadiusAxis, ResponsiveContainer, Tooltip,
} from 'recharts'
import type { PlayerDetail } from '../api/players'

interface RoleScore {
  role: string
  score: number
}

function computeRoles(p: PlayerDetail): RoleScore[] {
  return [
    {
      role: 'Portiere',
      score: Math.round((p.goalkeeper * 0.7 + p.defending * 0.3) * 10) / 10,
    },
    {
      role: 'Difensore',
      score: Math.round((p.defending * 0.5 + p.playmaking * 0.25 + p.set_pieces * 0.25) * 10) / 10,
    },
    {
      role: 'Terzino',
      score: Math.round((p.defending * 0.4 + p.winger * 0.3 + p.playmaking * 0.2 + p.set_pieces * 0.1) * 10) / 10,
    },
    {
      role: 'Centrocampista',
      score: Math.round((p.playmaking * 0.5 + p.passing * 0.25 + p.defending * 0.25) * 10) / 10,
    },
    {
      role: 'Ala',
      score: Math.round((p.winger * 0.45 + p.passing * 0.35 + p.scoring * 0.2) * 10) / 10,
    },
    {
      role: 'Attaccante',
      score: Math.round((p.scoring * 0.55 + p.passing * 0.3 + p.set_pieces * 0.15) * 10) / 10,
    },
  ]
}

interface Props {
  player: PlayerDetail
}

export function RoleRadarChart({ player }: Props) {
  const data = computeRoles(player)

  return (
    <ResponsiveContainer width="100%" height={300}>
      <RadarChart data={data} margin={{ top: 10, right: 30, bottom: 10, left: 30 }}>
        <PolarGrid />
        <PolarAngleAxis dataKey="role" tick={{ fontSize: 11 }} />
        <PolarRadiusAxis domain={[0, 20]} tickCount={5} tick={{ fontSize: 9 }} />
        <Tooltip formatter={(value) => [value, 'Punteggio']} />
        <Radar
          dataKey="score"
          stroke="#3b82f6"
          fill="#3b82f6"
          fillOpacity={0.25}
        />
      </RadarChart>
    </ResponsiveContainer>
  )
}
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd /media/michel/Lavoro/source/myhattrick/frontend
npx tsc --noEmit 2>&1 | head -30
```

Expected: no new errors.

---

### Task 7: Frontend `PlayerDetail.tsx` page

**Files:**
- Create: `frontend/src/pages/PlayerDetail.tsx`

Note: this task depends on Tasks 4 and 6 completing first (api/players.ts, SkillLineChart, RoleRadarChart must exist).

- [ ] **Step 1: Create `frontend/src/pages/PlayerDetail.tsx`**

```tsx
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getPlayer, getPlayerHistory } from '../api/players'
import { SkillLineChart } from '../components/SkillLineChart'
import { RoleRadarChart } from '../components/RoleRadarChart'

const MAIN_SKILLS = ['goalkeeper', 'defending', 'playmaking', 'winger', 'passing', 'scoring']

const SKILL_LABELS: Record<string, string> = {
  goalkeeper: 'Portiere', defending: 'Difesa', playmaking: 'Centrocampo',
  winger: 'Ala', passing: 'Passaggi', scoring: 'Attacco',
  stamina: 'Resistenza', speed: 'Velocità', set_pieces: 'Cal. piazzati',
  form: 'Forma', leadership: 'Leadership', experience: 'Esperienza', loyalty: 'Fedeltà',
}

const ALL_SKILLS = [...MAIN_SKILLS, 'stamina', 'speed', 'set_pieces', 'form', 'leadership', 'experience', 'loyalty']

const cardStyle: React.CSSProperties = {
  background: '#fff',
  borderRadius: 8,
  padding: 20,
  border: '1px solid #e5e7eb',
}

export function PlayerDetail() {
  const { id } = useParams<{ id: string }>()
  const playerId = Number(id)

  const { data: player, isLoading, error } = useQuery({
    queryKey: ['player', playerId],
    queryFn: () => getPlayer(playerId),
    enabled: !isNaN(playerId),
  })

  const { data: history = [], isLoading: loadingHistory } = useQuery({
    queryKey: ['player-history', playerId],
    queryFn: () => getPlayerHistory(playerId),
    enabled: !isNaN(playerId),
  })

  if (isNaN(playerId)) return <p style={{ color: '#ef4444' }}>ID giocatore non valido.</p>
  if (isLoading) return <p>Caricamento…</p>
  if (error) return <p style={{ color: '#ef4444' }}>Errore: {(error as Error).message}</p>
  if (!player) return null

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <Link to="/squad" style={{ color: '#6b7280', fontSize: 13, textDecoration: 'none' }}>
          ← Rosa
        </Link>
      </div>

      <h1 style={{ marginTop: 0, marginBottom: 24 }}>
        {player.first_name} {player.last_name}
      </h1>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 24 }}>
        <div style={cardStyle}>
          <h2 style={{ marginTop: 0, fontSize: 15, marginBottom: 12 }}>Dati</h2>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <tbody>
              {([
                ['Età', `${player.age} anni (${player.age_days} giorni)`],
                ['TSI', player.tsi?.toLocaleString('it-IT') ?? '—'],
                ['Forma', player.form],
                ['Resistenza', player.stamina],
                ['Stipendio', player.salary ? `€${player.salary.toLocaleString('it-IT')}` : '—'],
                ['Valore di mercato', player.market_value ? `€${player.market_value.toLocaleString('it-IT')}` : '—'],
                ['Infortuni', player.injury_days === -1 ? 'Sano' : `${player.injury_days} settimane`],
                ['Fonte dati', player.data_source ?? '—'],
              ] as [string, string | number][]).map(([label, value]) => (
                <tr key={label}>
                  <td style={{ padding: '4px 0', color: '#6b7280', width: '55%' }}>{label}</td>
                  <td style={{ padding: '4px 0', fontWeight: 500 }}>{value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div style={cardStyle}>
          <h2 style={{ marginTop: 0, fontSize: 15, marginBottom: 12 }}>Skill</h2>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <tbody>
              {ALL_SKILLS.map((sk) => (
                <tr key={sk}>
                  <td style={{ padding: '3px 0', color: '#6b7280', width: '55%' }}>
                    {SKILL_LABELS[sk] ?? sk}
                  </td>
                  <td style={{ padding: '3px 0', fontWeight: 500 }}>
                    {(player as Record<string, unknown>)[sk] as number ?? '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
        <div style={cardStyle}>
          <h2 style={{ marginTop: 0, fontSize: 15, marginBottom: 12 }}>Andamento skill</h2>
          {loadingHistory ? (
            <p style={{ fontSize: 13, color: '#6b7280' }}>Caricamento…</p>
          ) : history.length < 2 ? (
            <p style={{ fontSize: 13, color: '#6b7280' }}>
              Servono almeno 2 snapshot HRF per visualizzare l&apos;andamento.
            </p>
          ) : (
            <SkillLineChart history={history} skills={MAIN_SKILLS} />
          )}
        </div>

        <div style={cardStyle}>
          <h2 style={{ marginTop: 0, fontSize: 15, marginBottom: 12 }}>Radar ruoli</h2>
          <RoleRadarChart player={player} />
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd /media/michel/Lavoro/source/myhattrick/frontend
npx tsc --noEmit 2>&1 | head -30
```

Expected: no new errors.

---

### Task 8: Frontend `Training.tsx` page

**Files:**
- Create: `frontend/src/pages/Training.tsx`

Note: depends on Tasks 4 and 5 (api/training.ts, HrfScanButton, DeltaBadge must exist).

- [ ] **Step 1: Create `frontend/src/pages/Training.tsx`**

```tsx
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { getTraining, type SkillKey } from '../api/training'
import { DeltaBadge } from '../components/DeltaBadge'
import { HrfScanButton } from '../components/HrfScanButton'

const SKILL_COLS: Array<{ key: SkillKey; label: string }> = [
  { key: 'goalkeeper', label: 'Por.' },
  { key: 'defending', label: 'Dif.' },
  { key: 'playmaking', label: 'Cen.' },
  { key: 'winger', label: 'Ala' },
  { key: 'passing', label: 'Pas.' },
  { key: 'scoring', label: 'Att.' },
  { key: 'set_pieces', label: 'Cal.' },
  { key: 'stamina', label: 'Sta.' },
  { key: 'speed', label: 'Vel.' },
  { key: 'form', label: 'For.' },
  { key: 'leadership', label: 'Lea.' },
  { key: 'experience', label: 'Esp.' },
  { key: 'loyalty', label: 'Fed.' },
]

const thStyle: React.CSSProperties = {
  padding: '10px 12px',
  textAlign: 'left',
  borderBottom: '2px solid #e5e7eb',
  whiteSpace: 'nowrap',
  fontSize: 13,
  color: '#6b7280',
}

const tdStyle: React.CSSProperties = {
  padding: '8px 12px',
  fontSize: 13,
}

export function Training() {
  const qc = useQueryClient()
  const { data: rows = [], isLoading, error } = useQuery({
    queryKey: ['training'],
    queryFn: getTraining,
  })

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h1 style={{ margin: 0 }}>Allenamento</h1>
        <HrfScanButton onScanned={() => {
          qc.invalidateQueries({ queryKey: ['training'] })
          qc.invalidateQueries({ queryKey: ['squad'] })
        }} />
      </div>

      {rows.length > 0 && (
        <p style={{ margin: '0 0 16px', fontSize: 13, color: '#6b7280' }}>
          Delta: {rows[0].from_date.slice(0, 10)} → {rows[0].to_date.slice(0, 10)}
        </p>
      )}

      {isLoading && <p>Caricamento…</p>}
      {error && <p style={{ color: '#ef4444' }}>Errore: {(error as Error).message}</p>}

      {!isLoading && rows.length === 0 && (
        <p style={{ color: '#6b7280' }}>
          Servono almeno 2 file HRF importati per vedere i delta di allenamento.
        </p>
      )}

      {rows.length > 0 && (
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
              <tr>
                <th style={thStyle}>Giocatore</th>
                {SKILL_COLS.map(({ key, label }) => (
                  <th key={key} style={{ ...thStyle, textAlign: 'center' }}>{label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={row.player_id} style={{ background: i % 2 === 0 ? '#fff' : '#f9fafb' }}>
                  <td style={{ ...tdStyle, fontWeight: 500 }}>
                    {row.first_name} {row.last_name}
                  </td>
                  {SKILL_COLS.map(({ key }) => (
                    <td key={key} style={{ ...tdStyle, textAlign: 'center' }}>
                      <DeltaBadge value={row.deltas[key]} />
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

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd /media/michel/Lavoro/source/myhattrick/frontend
npx tsc --noEmit 2>&1 | head -30
```

Expected: no new errors.

---

### Task 9: Frontend wiring — App.tsx, Squad.tsx, Settings.tsx

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/pages/Squad.tsx`
- Modify: `frontend/src/pages/Settings.tsx`

Note: depends on Tasks 7 and 8 (PlayerDetail and Training pages must exist).

- [ ] **Step 1: Update `frontend/src/App.tsx`**

Replace the entire file:

```tsx
import { createBrowserRouter, RouterProvider, NavLink, Outlet } from 'react-router-dom'
import { Dashboard } from './pages/Dashboard'
import { Squad } from './pages/Squad'
import { Settings } from './pages/Settings'
import { PlayerDetail } from './pages/PlayerDetail'
import { Training } from './pages/Training'

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
      { path: 'settings', element: <Settings /> },
    ],
  },
])

export default function App() {
  return <RouterProvider router={router} />
}
```

- [ ] **Step 2: Update `frontend/src/pages/Squad.tsx`**

Two changes: (1) player name column becomes a clickable link, (2) add HrfScanButton next to SyncButton.

Replace the entire file:

```tsx
import { useState } from 'react'
import { Link } from 'react-router-dom'
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
import { HrfScanButton } from '../components/HrfScanButton'

const col = createColumnHelper<Player>()

const columns = [
  col.accessor((p) => `${p.first_name} ${p.last_name}`, {
    id: 'name',
    header: 'Nome',
    cell: (info) => {
      const player = info.row.original
      return (
        <Link
          to={`/players/${player.id}`}
          style={{ color: '#3b82f6', textDecoration: 'none', fontWeight: 500 }}
        >
          {player.first_name} {player.last_name}
        </Link>
      )
    },
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
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <HrfScanButton onScanned={() => qc.invalidateQueries({ queryKey: ['squad'] })} />
          <SyncButton entity="squad" onSynced={() => qc.invalidateQueries({ queryKey: ['squad'] })} />
        </div>
      </div>

      {isLoading && <p>Caricamento…</p>}
      {error && <p style={{ color: '#ef4444' }}>Errore: {(error as Error).message}</p>}

      {!isLoading && players.length === 0 && (
        <p style={{ color: '#6b7280' }}>
          Nessun giocatore. Importa un file HRF o configura CHPP e clicca Sincronizza.
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

- [ ] **Step 3: Update `frontend/src/pages/Settings.tsx`**

Replace the entire file. The CHPP section is preserved but collapsed under `<details>`. A new HRF section appears at the top.

```tsx
import { useState, useEffect, FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { getSettings } from '../api/settings'
import { initiateOAuth } from '../api/auth'
import { getHrfSettings, saveHrfSettings } from '../api/hrf'
import { HrfScanButton } from '../components/HrfScanButton'

export function Settings() {
  const [searchParams, setSearchParams] = useSearchParams()
  const justAuthorized = searchParams.get('authorized') === 'true'
  const qc = useQueryClient()

  const [consumerKey, setConsumerKey] = useState('')
  const [consumerSecret, setConsumerSecret] = useState('')
  const [oauthComplete, setOauthComplete] = useState(false)
  const [chppLoading, setChppLoading] = useState(false)
  const [chppError, setChppError] = useState<string | null>(null)

  const [hrfFolder, setHrfFolder] = useState('')
  const [hrfSaved, setHrfSaved] = useState(false)
  const [hrfError, setHrfError] = useState<string | null>(null)
  const [hrfLoading, setHrfLoading] = useState(false)

  useEffect(() => {
    getSettings().then((s) => {
      if (s.configured) {
        setConsumerKey(s.consumer_key ?? '')
        setOauthComplete(s.oauth_complete ?? false)
      }
    })
    if (justAuthorized) {
      setOauthComplete(true)
      setSearchParams({}, { replace: true })
    }
    getHrfSettings()
      .then((s) => setHrfFolder(s.hrf_folder_path))
      .catch(() => {})
  }, [])

  async function handleSaveHrf(e: FormEvent) {
    e.preventDefault()
    setHrfLoading(true)
    setHrfError(null)
    try {
      await saveHrfSettings({ hrf_folder_path: hrfFolder, team_id: null, enabled: true })
      setHrfSaved(true)
      setTimeout(() => setHrfSaved(false), 3000)
    } catch (err: unknown) {
      setHrfError(err instanceof Error ? err.message : 'Errore')
    } finally {
      setHrfLoading(false)
    }
  }

  async function handleAuthorize(e: FormEvent) {
    e.preventDefault()
    if (!consumerKey || !consumerSecret) {
      setChppError('Inserisci consumer key e consumer secret.')
      return
    }
    setChppLoading(true)
    setChppError(null)
    try {
      const { auth_url } = await initiateOAuth(consumerKey, consumerSecret)
      window.location.href = auth_url
    } catch (err: unknown) {
      setChppError(err instanceof Error ? err.message : 'Errore durante la richiesta token')
      setChppLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 520 }}>
      <h1 style={{ marginTop: 0 }}>Impostazioni</h1>

      <section style={{ marginBottom: 32 }}>
        <h2 style={{ fontSize: 18, marginTop: 0, marginBottom: 16 }}>Importazione HRF</h2>
        <form onSubmit={handleSaveHrf}>
          <div style={{ marginBottom: 14 }}>
            <label style={{ display: 'block', marginBottom: 4, fontWeight: 500, fontSize: 14 }}>
              Cartella file HRF
            </label>
            <input
              type="text"
              value={hrfFolder}
              onChange={(e) => setHrfFolder(e.target.value)}
              placeholder="/program/ho/"
              style={inputStyle}
            />
          </div>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 16 }}>
            <button type="submit" disabled={hrfLoading} style={buttonStyle(hrfLoading)}>
              {hrfLoading ? 'Salvataggio…' : 'Salva percorso'}
            </button>
            {hrfSaved && <span style={{ fontSize: 12, color: '#16a34a' }}>✓ Salvato</span>}
            {hrfError && <span style={{ fontSize: 12, color: '#ef4444' }}>{hrfError}</span>}
          </div>
        </form>
        <HrfScanButton onScanned={() => {
          qc.invalidateQueries({ queryKey: ['squad'] })
          qc.invalidateQueries({ queryKey: ['training'] })
        }} />
      </section>

      <details>
        <summary
          style={{ cursor: 'pointer', color: '#6b7280', fontSize: 14, userSelect: 'none', marginBottom: 4 }}
        >
          Configurazione CHPP (avanzata)
        </summary>
        <div style={{ marginTop: 16 }}>
          {oauthComplete ? (
            <div
              style={{
                padding: '16px 20px',
                background: '#f0fdf4',
                border: '1px solid #bbf7d0',
                borderRadius: 8,
                marginBottom: 24,
              }}
            >
              <div style={{ fontWeight: 600, color: '#15803d' }}>✓ Autorizzato con Hattrick</div>
              <div style={{ fontSize: 13, color: '#16a34a', marginTop: 4 }}>
                I token CHPP sono salvati.
              </div>
            </div>
          ) : (
            <div
              style={{
                padding: '16px 20px',
                background: '#fefce8',
                border: '1px solid #fde047',
                borderRadius: 8,
                marginBottom: 24,
              }}
            >
              <div style={{ fontWeight: 600, color: '#854d0e' }}>⏳ Non ancora autorizzato</div>
              <div style={{ fontSize: 13, color: '#92400e', marginTop: 4 }}>
                Richiedi l&apos;accesso CHPP su{' '}
                <a href="https://chpp.hattrick.org/" target="_blank" rel="noreferrer">
                  chpp.hattrick.org
                </a>
                , poi inserisci le credenziali qui sotto.
              </div>
            </div>
          )}

          <form onSubmit={handleAuthorize}>
            <h2 style={{ fontSize: 16, marginBottom: 16 }}>Credenziali applicazione</h2>
            <div style={{ marginBottom: 14 }}>
              <label style={{ display: 'block', marginBottom: 4, fontWeight: 500, fontSize: 14 }}>
                Consumer Key
              </label>
              <input
                type="text"
                value={consumerKey}
                onChange={(e) => setConsumerKey(e.target.value)}
                style={inputStyle}
              />
            </div>
            <div style={{ marginBottom: 20 }}>
              <label style={{ display: 'block', marginBottom: 4, fontWeight: 500, fontSize: 14 }}>
                Consumer Secret
              </label>
              <input
                type="password"
                value={consumerSecret}
                onChange={(e) => setConsumerSecret(e.target.value)}
                style={inputStyle}
              />
            </div>
            <button type="submit" disabled={chppLoading} style={buttonStyle(chppLoading)}>
              {chppLoading ? 'Connessione a Hattrick…' : 'Autorizza con Hattrick →'}
            </button>
            {chppError && (
              <p style={{ marginTop: 10, color: '#ef4444', fontSize: 13 }}>{chppError}</p>
            )}
          </form>

          <div
            style={{
              marginTop: 32,
              padding: '14px 16px',
              background: '#f8fafc',
              borderRadius: 6,
              fontSize: 12,
              color: '#64748b',
            }}
          >
            <strong>Come funziona:</strong> Cliccando il bottone, verrai reindirizzato su Hattrick
            per autorizzare l&apos;accesso. Dopo l&apos;autorizzazione tornerai automaticamente qui
            con i token salvati.
          </div>
        </div>
      </details>
    </div>
  )
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '8px 10px',
  border: '1px solid #d1d5db',
  borderRadius: 6,
  fontSize: 14,
  boxSizing: 'border-box',
}

function buttonStyle(disabled: boolean): React.CSSProperties {
  return {
    padding: '9px 20px',
    background: disabled ? '#93c5fd' : '#3b82f6',
    color: '#fff',
    border: 'none',
    borderRadius: 6,
    cursor: disabled ? 'not-allowed' : 'pointer',
    fontSize: 14,
    fontWeight: 500,
  }
}
```

- [ ] **Step 4: Verify TypeScript compiles and dev server starts**

```bash
cd /media/michel/Lavoro/source/myhattrick/frontend
npx tsc --noEmit 2>&1 | head -30
```

Expected: no errors.

```bash
cd /media/michel/Lavoro/source/myhattrick
make dev &
sleep 5 && curl -s http://localhost:5173 | head -5
```

Expected: HTML response (Vite dev server running).

- [ ] **Step 5: Run full backend test suite one final time**

```bash
cd /media/michel/Lavoro/source/myhattrick/backend
python -m pytest -v
```

Expected: all tests pass (46+ total).
