# Piano C — Partite: Formazioni e Classifica

## Obiettivo

Aggiungere una pagina `/matches` che mostra, per ogni HRF importato, la formazione dell'ultima partita giocata e l'andamento della classifica nel tempo.

## Contesto

I file HRF contengono:
- `[basics]`: `season`, `matchround`
- `[lastlineup]`: mappa posizione → player_id dell'ultima partita giocata
- `[league]`: `spelade` (played), `gjorda` (goals_for), `inslappta` (goals_against), `poang` (points), `placering` (position)
- `[player*]`: campo `rating` = voto nell'ultima partita (0 = non disponibile)

Non sono disponibili: punteggi delle partite, nome dell'avversario.

---

## Data Model

### Nuova tabella `match_snapshots`

| Campo | Tipo | Note |
|---|---|---|
| `id` | Integer PK | |
| `snapshot_date` | DateTime unique | dalla data nel nome file HRF |
| `season` | Integer | da `[basics]` |
| `matchround` | Integer | da `[basics]` |
| `league_position` | Integer | da `[league].placering` |
| `league_points` | Integer | da `[league].poang` |
| `league_played` | Integer | da `[league].spelade` |
| `league_goals_for` | Integer | da `[league].gjorda` |
| `league_goals_against` | Integer | da `[league].inslappta` |
| `lineup_json` | String | JSON `{position: player_id}` da `[lastlineup]` |
| `ratings_json` | String | JSON `{str(player_id): rating}` da `[player*]` |

`snapshot_date` è univoco: se si reimporta lo stesso HRF, la riga viene aggiornata (upsert).

---

## Backend

### HRF Parser — estensioni

File: `backend/app/hrf/parser.py`

Tre nuove funzioni:

**`parse_basics(config) → dict`**
```python
{"season": int, "matchround": int}
```
Legge `[basics]`: `season`, `matchround`.

**`parse_lastlineup(config) → dict[str, int]`**
```python
{"keeper": 376216478, "rightBack": 391771603, ...}
```
Posizioni da estrarre (solo starting + subs, esclusi `beh*`, `penalty*`, `captain`, `kicker1`):
```
keeper, rightBack, insideBack1, insideBack2, insideBack3, leftBack,
rightWinger, insideMid1, insideMid2, insideMid3, leftWinger,
forward1, forward2, forward3,
substBack, substInsideMid, substWinger, substKeeper, substForward
```
Valore `-1` o `0` = posizione vuota (non includere nel JSON).

**`parse_league(config) → dict`**
```python
{"position": 4, "points": 23, "played": 13, "goals_for": 28, "goals_against": 19}
```
Legge `[league]`: `placering`, `poang`, `spelade`, `gjorda`, `inslappta`.

### HRF Scanner — estensione

File: `backend/app/hrf/scanner.py`

Dopo l'import dei giocatori, per ogni HRF:
1. Chiama `parse_basics`, `parse_lastlineup`, `parse_league`
2. Costruisce `ratings_json` raccogliendo `rating` da ogni sezione `[player*]` già parsata
3. Upserta `MatchSnapshot` (insert se non esiste per `snapshot_date`, update altrimenti)

### Nuovo modello

File: `backend/app/models/match_snapshot.py`

SQLAlchemy model con i campi della tabella sopra.

### Nuova API

File: `backend/app/api/matches.py`

**`GET /api/matches`**

Restituisce lista di match ordered by `snapshot_date` desc.

Per ogni match, arricchisce il lineup con nomi giocatori (join con tabella `Player`).

Struttura risposta:
```json
[
  {
    "snapshot_date": "2026-05-20",
    "season": 62,
    "matchround": 14,
    "lineup": [
      {"line": "GK", "position": "keeper", "player_id": 376216478, "name": "Damazy Janczak", "rating": 0},
      {"line": "Difesa", "position": "rightBack", "player_id": 391771603, "name": "Cesare Marianelli", "rating": 7},
      {"line": "Difesa", "position": "insideBack1", "player_id": 356445295, "name": "Ettore Mencattini", "rating": 6},
      ...
    ],
    "league": {
      "position": 4, "points": 23, "played": 13,
      "goals_for": 28, "goals_against": 19
    }
  }
]
```

**Mapping posizioni → riga (`line`) e label (`position_label`):**

| position | line | label |
|---|---|---|
| keeper | GK | Portiere |
| rightBack | Difesa | Terzino Dx |
| insideBack1 | Difesa | Difensore Cen |
| insideBack2 | Difesa | Difensore Cen |
| insideBack3 | Difesa | Difensore Cen |
| leftBack | Difesa | Terzino Sx |
| rightWinger | Centrocampo | Ala Dx |
| insideMid1 | Centrocampo | Centrocampista |
| insideMid2 | Centrocampo | Centrocampista |
| insideMid3 | Centrocampo | Centrocampista |
| leftWinger | Centrocampo | Ala Sx |
| forward1 | Attacco | Attaccante |
| forward2 | Attacco | Attaccante |
| forward3 | Attacco | Attaccante |
| substBack | Panchina | Riserva Dif |
| substInsideMid | Panchina | Riserva Cen |
| substWinger | Panchina | Riserva Ala |
| substKeeper | Panchina | Riserva Por |
| substForward | Panchina | Riserva Att |

Posizioni vuote (player_id assente nel lineup_json) non compaiono nella risposta.

**Rating:** `0` viene restituito come `null` nel JSON (il frontend mostra "—").

### Registrazione router

File: `backend/app/main.py` — aggiungere `include_router` per `matches`.

---

## Frontend

### Nuovi file

- `frontend/src/api/matches.ts` — tipi e funzione `getMatches()`
- `frontend/src/pages/Matches.tsx` — pagina principale
- Route `/matches` in `App.tsx`
- Link "Partite" in `Navbar`

### Tipi TypeScript

```typescript
interface LineupEntry {
  line: string
  position: string
  player_id: number
  name: string
  rating: number | null
}

interface LeagueData {
  position: number
  points: number
  played: number
  goals_for: number
  goals_against: number
}

interface Match {
  snapshot_date: string
  season: number
  matchround: number
  lineup: LineupEntry[]
  league: LeagueData
}
```

### Pagina `/matches`

**Layout:**

```
[ Formazione ]

  ← | Stagione 62 — Turno 14 | →

  Reparto        Posizione       Giocatore              Voto
  GK             Portiere        Damazy Janczak           —
  Difesa         Terzino Dx      Cesare Marianelli        7
  ...
  Panchina       Riserva Por     Gian Franco Formichi     —

[ Classifica nel tempo ]

  LineChart: Punti (linea blu) + Posizione (linea arancio, asse Y invertito)
  X axis: "S{season} T{matchround}"
  Tooltip: Stagione, Turno, Punti, Posizione, GF/GA
```

**Stato:** `selectedIndex: number` (0 = partita più recente).
Pulsante `←` disabilitato se `selectedIndex === matches.length - 1`, `→` se `selectedIndex === 0`.

**Voto:** `null` mostrato come `—`.

**Classifica:** tutti i match vengono usati per il chart, ordinati per data crescente sull'asse X.

---

## Testing

### Backend

- `test_parse_basics`: verifica estrazione season e matchround
- `test_parse_lastlineup`: verifica mapping posizione→player_id, esclude posizioni vuote (-1/0)
- `test_parse_league`: verifica tutti i campi league
- `test_scanner_creates_match_snapshot`: dopo import HRF, verifica riga in `match_snapshots`
- `test_scanner_upserts_match_snapshot`: doppio import stesso HRF → ancora 1 riga
- `test_api_matches_empty`: nessun snapshot → `[]`
- `test_api_matches_lineup_enriched`: snapshot con player in DB → lineup con nomi
- `test_api_matches_empty_positions_excluded`: posizioni con player_id 0/-1 → non nel lineup
- `test_api_matches_ordered_desc`: più snapshot → più recente per primo

### Frontend

Nessun test automatico — verificare manualmente: navigazione prev/next, voti null mostrati come "—", chart con dati reali dopo import HRF.
