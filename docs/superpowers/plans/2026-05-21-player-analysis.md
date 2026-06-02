# Player Analysis & Training Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Aggiungere la pagina `/players/:id` con LineChart + RadarChart e ridisegnare `/training` con selector sessioni e card before→after.

**Architecture:** Il modello `PlayerSkillHistory` e le sue scritture (HRF scan) esistono già. Il lavoro consiste in: (1) aggiornare le formule del RadarChart, (2) ridisegnare l'endpoint `GET /api/training` da flat-array a struttura sessions-based, (3) ridisegnare la pagina Training.tsx in layout ibrido, (4) aggiungere la scrittura degli snapshot anche al sync CHPP. La pagina `/players/:id` con i due grafici è già implementata.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2.x, SQLite, pytest 8.x; React 18, TypeScript, TanStack Query, Recharts

---

## Mappa file

| File | Azione | Cosa cambia |
|---|---|---|
| `frontend/src/components/RoleRadarChart.tsx` | Modifica | Formule spec-approved (aggiunge stamina, corregge pesi) |
| `backend/tests/test_api_training.py` | Riscrivi | Nuova response shape sessions-based (TDD) |
| `backend/app/api/training.py` | Riscrivi | Endpoint sessions-based con changed/unchanged players |
| `frontend/src/api/training.ts` | Riscrivi | Nuovi tipi TypeScript |
| `frontend/src/pages/Training.tsx` | Riscrivi | Layout ibrido: pill selector + card before→after |
| `backend/app/api/sync.py` | Modifica | Salva PlayerSkillHistory dopo upsert CHPP |
| `backend/tests/test_api_sync.py` | Modifica | Aggiunge test snapshot history |

---

## Task 1: Aggiorna formule RoleRadarChart

**File:**
- Modify: `frontend/src/components/RoleRadarChart.tsx`

- [ ] **Step 1: Aggiorna la funzione `computeRoles`**

Sostituisci l'intera funzione `computeRoles` in `frontend/src/components/RoleRadarChart.tsx`:

```typescript
function computeRoles(p: PlayerDetail): RoleScore[] {
  return [
    {
      role: 'Portiere',
      score: Math.round((p.goalkeeper * 0.85 + p.stamina * 0.10 + p.set_pieces * 0.05) * 10) / 10,
    },
    {
      role: 'Difensore',
      score: Math.round((p.defending * 0.50 + p.playmaking * 0.20 + p.passing * 0.15 + p.stamina * 0.15) * 10) / 10,
    },
    {
      role: 'Terzino',
      score: Math.round((p.defending * 0.35 + p.winger * 0.35 + p.passing * 0.15 + p.stamina * 0.15) * 10) / 10,
    },
    {
      role: 'Centrocampista',
      score: Math.round((p.playmaking * 0.50 + p.passing * 0.20 + p.defending * 0.15 + p.stamina * 0.15) * 10) / 10,
    },
    {
      role: 'Ala',
      score: Math.round((p.winger * 0.50 + p.passing * 0.20 + p.scoring * 0.15 + p.stamina * 0.15) * 10) / 10,
    },
    {
      role: 'Attaccante',
      score: Math.round((p.scoring * 0.55 + p.winger * 0.20 + p.passing * 0.10 + p.stamina * 0.15) * 10) / 10,
    },
  ]
}
```

- [ ] **Step 2: Verifica TypeScript**

```bash
cd frontend && npx tsc --noEmit
```

Expected: nessun errore.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/RoleRadarChart.tsx
git commit -m "feat: update RoleRadarChart with spec-approved role formulas"
```

---

## Task 2: Riscrivi test_api_training.py (TDD)

**File:**
- Test: `backend/tests/test_api_training.py`

- [ ] **Step 1: Riscrivi il file con i nuovi test**

Sostituisci l'intero contenuto di `backend/tests/test_api_training.py`:

```python
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
```

- [ ] **Step 2: Verifica che i nuovi test falliscano**

```bash
cd backend && pytest tests/test_api_training.py -v
```

Expected: tutti i test FAIL (la risposta attuale è una lista, non `{"sessions": ...}`).

---

## Task 3: Implementa il nuovo GET /api/training

**File:**
- Modify: `backend/app/api/training.py`

- [ ] **Step 1: Riscrivi l'endpoint**

Sostituisci l'intero contenuto di `backend/app/api/training.py`:

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
    dates = sorted({
        r.snapshot_date
        for r in db.query(PlayerSkillHistory.snapshot_date).distinct()
    })

    if len(dates) < 2:
        return {"sessions": []}

    sessions = []
    for i in range(len(dates) - 1, 0, -1):
        newer_date = dates[i]
        older_date = dates[i - 1]

        newer_map = {
            r.player_id: r
            for r in db.query(PlayerSkillHistory).filter(
                PlayerSkillHistory.snapshot_date == newer_date
            )
        }
        older_map = {
            r.player_id: r
            for r in db.query(PlayerSkillHistory).filter(
                PlayerSkillHistory.snapshot_date == older_date
            )
        }

        common_ids = set(newer_map) & set(older_map)
        players = {
            p.id: p
            for p in db.query(Player).filter(Player.id.in_(common_ids))
        }

        changed = []
        unchanged_count = 0

        for pid in common_ids:
            newer = newer_map[pid]
            older = older_map[pid]
            deltas = {f: getattr(newer, f) - getattr(older, f) for f in SKILL_FIELDS}
            changed_fields = [f for f, d in deltas.items() if d != 0]

            if not changed_fields:
                unchanged_count += 1
                continue

            p = players[pid]
            changed.append({
                "player_id": pid,
                "first_name": p.first_name,
                "last_name": p.last_name,
                "age": p.age,
                "deltas": deltas,
                "previous_values": {f: getattr(older, f) for f in changed_fields},
                "current_values": {f: getattr(newer, f) for f in changed_fields},
            })

        changed.sort(key=lambda x: -sum(1 for d in x["deltas"].values() if d != 0))

        sessions.append({
            "synced_at": newer_date.isoformat(),
            "previous_sync": older_date.isoformat(),
            "changed_players": changed,
            "unchanged_count": unchanged_count,
        })

    return {"sessions": sessions}
```

- [ ] **Step 2: Esegui i test**

```bash
cd backend && pytest tests/test_api_training.py -v
```

Expected: tutti i test PASS.

- [ ] **Step 3: Esegui la suite completa**

```bash
cd backend && pytest -v
```

Expected: tutti i test PASS (compresi quelli pre-esistenti che non abbiamo toccato).

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/training.py backend/tests/test_api_training.py
git commit -m "feat: redesign GET /api/training to sessions-based response with before/after values"
```

---

## Task 4: Aggiorna training.ts (tipi TypeScript)

**File:**
- Modify: `frontend/src/api/training.ts`

- [ ] **Step 1: Riscrivi il file**

Sostituisci l'intero contenuto di `frontend/src/api/training.ts`:

```typescript
import { apiFetch } from './client'

export type SkillKey =
  | 'form' | 'stamina' | 'speed' | 'goalkeeper' | 'defending' | 'playmaking'
  | 'winger' | 'passing' | 'scoring' | 'set_pieces' | 'leadership' | 'experience' | 'loyalty'

export interface TrainingPlayer {
  player_id: number
  first_name: string
  last_name: string
  age: number
  deltas: Record<SkillKey, number>
  previous_values: Partial<Record<SkillKey, number>>
  current_values: Partial<Record<SkillKey, number>>
}

export interface TrainingSession {
  synced_at: string
  previous_sync: string
  changed_players: TrainingPlayer[]
  unchanged_count: number
}

export interface TrainingResponse {
  sessions: TrainingSession[]
}

export function getTraining(): Promise<TrainingResponse> {
  return apiFetch<TrainingResponse>('/api/training')
}
```

- [ ] **Step 2: Verifica TypeScript**

```bash
cd frontend && npx tsc --noEmit
```

Expected: errori solo in `Training.tsx` (che riscriviamo nel task successivo), nessun errore altrove.

---

## Task 5: Riscrivi Training.tsx

**File:**
- Modify: `frontend/src/pages/Training.tsx`

- [ ] **Step 1: Riscrivi il file**

Sostituisci l'intero contenuto di `frontend/src/pages/Training.tsx`:

```tsx
import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { getTraining } from '../api/training'
import { DeltaBadge } from '../components/DeltaBadge'
import { HrfScanButton } from '../components/HrfScanButton'
import type { SkillKey } from '../api/training'

const SKILL_LABELS: Record<SkillKey, string> = {
  form: 'Forma', stamina: 'Resistenza', speed: 'Velocità',
  goalkeeper: 'Portiere', defending: 'Difesa', playmaking: 'Regia',
  winger: 'Ala', passing: 'Passaggi', scoring: 'Attacco',
  set_pieces: 'Cal. piazzati', leadership: 'Leadership',
  experience: 'Esperienza', loyalty: 'Fedeltà',
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('it-IT', { day: 'numeric', month: 'short' })
}

const cardStyle: React.CSSProperties = {
  background: '#fff',
  borderRadius: 8,
  border: '1px solid #e5e7eb',
  padding: '12px 16px',
}

export function Training() {
  const qc = useQueryClient()
  const [selectedIdx, setSelectedIdx] = useState(0)

  const { data, isLoading, error } = useQuery({
    queryKey: ['training'],
    queryFn: getTraining,
  })

  const sessions = data?.sessions ?? []
  const session = sessions[selectedIdx]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h1 style={{ margin: 0 }}>Allenamento</h1>
        <HrfScanButton onScanned={() => {
          qc.invalidateQueries({ queryKey: ['training'] })
          qc.invalidateQueries({ queryKey: ['squad'] })
        }} />
      </div>

      {isLoading && <p>Caricamento…</p>}
      {error && <p style={{ color: '#ef4444' }}>Errore: {(error as Error).message}</p>}

      {!isLoading && sessions.length === 0 && (
        <p style={{ color: '#6b7280' }}>
          Servono almeno 2 file HRF importati per vedere i delta di allenamento.
        </p>
      )}

      {sessions.length > 1 && (
        <div style={{ display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap' }}>
          {sessions.map((s, i) => (
            <button
              key={s.synced_at}
              onClick={() => setSelectedIdx(i)}
              style={{
                padding: '4px 14px',
                borderRadius: 20,
                border: 'none',
                cursor: 'pointer',
                fontSize: 13,
                background: i === selectedIdx ? '#3b82f6' : '#e5e7eb',
                color: i === selectedIdx ? '#fff' : '#374151',
                fontWeight: i === selectedIdx ? 600 : 400,
              }}
            >
              {formatDate(s.synced_at)}
            </button>
          ))}
        </div>
      )}

      {session && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {session.changed_players.length === 0 && session.unchanged_count > 0 && (
            <p style={{ color: '#6b7280', fontSize: 13 }}>
              Nessun giocatore ha variazioni di skill in questa sessione.
            </p>
          )}

          {session.changed_players.map((player) => {
            const changedSkills = (Object.keys(player.previous_values) as SkillKey[])
            return (
              <div key={player.player_id} style={cardStyle}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <span style={{ fontWeight: 600, fontSize: 14 }}>
                      {player.first_name} {player.last_name}
                    </span>
                    <span style={{ color: '#9ca3af', fontSize: 12, marginLeft: 8 }}>{player.age} anni</span>
                  </div>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                    {changedSkills.map((skill) => (
                      <span key={skill} style={{ fontSize: 12, color: '#6b7280' }}>
                        {SKILL_LABELS[skill]}{' '}
                        <DeltaBadge value={player.deltas[skill]} />
                      </span>
                    ))}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 20, marginTop: 8, flexWrap: 'wrap' }}>
                  {changedSkills.map((skill) => (
                    <div key={skill} style={{ fontSize: 12 }}>
                      <span style={{ color: '#9ca3af' }}>{SKILL_LABELS[skill]}: </span>
                      <span style={{ color: '#6b7280' }}>{player.previous_values[skill]}</span>
                      <span style={{ color: '#9ca3af' }}> → </span>
                      <span style={{ color: '#16a34a', fontWeight: 600 }}>{player.current_values[skill]}</span>
                    </div>
                  ))}
                </div>
              </div>
            )
          })}

          {session.unchanged_count > 0 && (
            <p style={{ fontSize: 13, color: '#9ca3af', textAlign: 'center', margin: '4px 0 0' }}>
              {session.unchanged_count} giocator{session.unchanged_count === 1 ? 'e' : 'i'} senza variazioni
            </p>
          )}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Verifica TypeScript**

```bash
cd frontend && npx tsc --noEmit
```

Expected: nessun errore.

- [ ] **Step 3: Avvia l'app e verifica manualmente**

```bash
make dev
```

Apri `http://localhost:5173/training`. Verifica:
- Con dati demo: se ci sono almeno 2 snapshot HRF, mostra le sessioni con pill selector
- Il pill più recente è preselezionato
- I giocatori con skill cambiate mostrano badge + valori before→after
- Il conteggio "N giocatori senza variazioni" appare sotto

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/training.ts frontend/src/pages/Training.tsx
git commit -m "feat: redesign Training page with session selector and before/after cards"
```

---

## Task 6: Estendi CHPP sync per salvare PlayerSkillHistory

**File:**
- Modify: `backend/app/api/sync.py`
- Modify: `backend/tests/test_api_sync.py`

- [ ] **Step 1: Scrivi il test che deve fallire**

Aggiungi alla fine di `backend/tests/test_api_sync.py`:

```python
def test_sync_squad_saves_skill_history(client, db):
    from app.models.player_skill_history import PlayerSkillHistory
    _seed_settings(db)
    with patch("app.api.sync.CHPPClient") as MockClient:
        MockClient.return_value.fetch.return_value = SQUAD_XML
        client.post("/api/sync/squad")
    history = db.query(PlayerSkillHistory).all()
    assert len(history) == 2  # 2 players in squad.xml
    assert all(h.source == "CHPP" for h in history)


def test_sync_squad_history_is_idempotent(client, db):
    from app.models.player_skill_history import PlayerSkillHistory
    _seed_settings(db)
    with patch("app.api.sync.CHPPClient") as MockClient:
        MockClient.return_value.fetch.return_value = SQUAD_XML
        client.post("/api/sync/squad")
        client.post("/api/sync/squad")
    history = db.query(PlayerSkillHistory).all()
    assert len(history) == 2  # secondo sync stesso giorno: nessun duplicato
```

- [ ] **Step 2: Verifica che i test falliscano**

```bash
cd backend && pytest tests/test_api_sync.py::test_sync_squad_saves_skill_history tests/test_api_sync.py::test_sync_squad_history_is_idempotent -v
```

Expected: FAIL (history vuota dopo sync).

- [ ] **Step 3: Aggiorna sync.py**

Nel file `backend/app/api/sync.py`, aggiungi `PlayerSkillHistory` agli import e modifica il blocco `if entity == "squad":` per salvare uno snapshot dopo ogni upsert:

```python
from datetime import datetime, timezone, date as date_type
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.settings import CHPPSettings
from app.models.player import Player
from app.models.player_skill_history import PlayerSkillHistory
from app.models.sync_log import SyncLog
from app.chpp.client import CHPPClient
from app.chpp.parsers.squad import parse_squad

router = APIRouter()

SUPPORTED_ENTITIES = {"squad"}

CHPP_SKILL_FIELDS = [
    "form", "stamina", "goalkeeper", "defending", "playmaking",
    "winger", "passing", "scoring", "set_pieces",
]


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
        try:
            xml_bytes = client.fetch("players")
        except Exception as exc:
            now = datetime.now(timezone.utc)
            log = db.query(SyncLog).filter_by(entity=entity).first()
            if log:
                log.last_sync_at = now
                log.status = "error"
            else:
                db.add(SyncLog(entity=entity, last_sync_at=now, status="error"))
            db.commit()
            raise HTTPException(status_code=502, detail=f"CHPP fetch failed: {exc}")

        now = datetime.now(timezone.utc)
        snapshot_date = datetime(now.year, now.month, now.day)  # midnight — un snapshot al giorno

        for pd in parse_squad(xml_bytes):
            existing = db.get(Player, pd["id"])
            if existing:
                for k, v in pd.items():
                    setattr(existing, k, v)
            else:
                db.add(Player(**pd))

            already = db.query(PlayerSkillHistory).filter_by(
                player_id=pd["id"], snapshot_date=snapshot_date
            ).first()
            if not already:
                db.add(PlayerSkillHistory(
                    player_id=pd["id"],
                    snapshot_date=snapshot_date,
                    source="CHPP",
                    **{f: pd.get(f, 0) for f in CHPP_SKILL_FIELDS},
                ))

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

- [ ] **Step 4: Esegui i nuovi test**

```bash
cd backend && pytest tests/test_api_sync.py -v
```

Expected: tutti e 7 i test PASS (inclusi i 2 nuovi).

- [ ] **Step 5: Esegui la suite completa**

```bash
cd backend && pytest -v
```

Expected: tutti i test PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/sync.py backend/tests/test_api_sync.py
git commit -m "feat: save PlayerSkillHistory snapshot on CHPP squad sync"
```

---

## Self-review

- **Spec coverage:** Sezione 1 (PlayerSkillHistory) già implementata ✅ — Sezione 2a (sync CHPP) → Task 6 ✅ — Sezione 2b (GET /players/{id}/history) già implementata ✅ — Sezione 2c (GET /training sessions) → Task 2+3 ✅ — Sezione 3 (formule ruoli) → Task 1 ✅ — Sezione 4 (layout PlayerDetail side-by-side) già implementata ✅ — Sezione 5 (layout Training ibrido) → Task 4+5 ✅
- **Placeholder scan:** nessun TBD, tutte le code box sono complete
- **Type consistency:** `SkillKey`, `TrainingPlayer`, `TrainingSession`, `TrainingResponse` definiti in Task 4 e usati in Task 5 — coerenti. `CHPP_SKILL_FIELDS` in Task 6 usa solo campi presenti sia in `parse_squad` sia in `PlayerSkillHistory`.
- **Nota:** `pd.get("form", 0)` funziona perché `parse_squad` restituisce dict. Verificare che `parse_squad` includa tutti i `CHPP_SKILL_FIELDS` dal file `squad.xml` del fixture.
