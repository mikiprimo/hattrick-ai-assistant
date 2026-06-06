# Design: Stagione (dashboard stagionale) + Girone (rivali)

**Data:** 2026-06-07  
**Stato:** Approvato

---

## Contesto

La pagina Stagione attuale è un form statico con campi manuali e una raccomandazione generica. L'obiettivo è trasformarla in una **dashboard stagionale viva** che segue l'andamento della squadra giornata per giornata e adatta i suggerimenti in tempo reale.

Parallelamente si aggiunge una nuova pagina **Girone** per la gestione delle squadre rivali, il cui dato è condiviso con Pre-Partita.

Il campionato HT è composto da **8 squadre** e **14 giornate** (girone all'italiana, andata e ritorno). Max punti stagionali: 42. Promozione: top 2. Retrocessione: bottom 2.

---

## Pagina: Stagione

### Zona 1 — Selezione obiettivo (top)

Tre card affiancate: **Promozione / Mantenimento / Sviluppo Giovani**.

- L'utente sceglie l'obiettivo una volta a inizio stagione (salvato in `seasonal_objective`)
- La card attiva è evidenziata con bordo colorato
- Ogni card mostra: nome, stato corrente (`In linea ✓` / `A rischio ⚠` / `Fuori strada ✗`), metrica chiave (es. "2° posto · 18 pt")
- L'obiettivo può essere cambiato, ma il sistema registra il cambio con data

### Zona 2 — Grafico di andamento (middle)

Sparkline (Recharts) con i punti accumulati per giornata, costruita dai record `MatchSnapshot` ordinati per `snapshot_date`.

Sovrapposta: la **traiettoria obiettivo** come linea tratteggiata calcolata automaticamente.

**Formula proiezione:** `proiezione_finale = (punti_attuali / giornate_giocate) × 14`

**Soglie automatiche:**

| Obiettivo | On track | A rischio | Fuori strada |
|---|---|---|---|
| Promozione | Pos. ≤ 2 AND proiezione ≥ 26 pt | Pos. 3-4 OR proiezione 20-25 | Pos. ≥ 5 OR proiezione < 20 |
| Mantenimento | Pos. ≤ 6 AND proiezione ≥ 16 pt | Pos. 6-7, margine < 4 pt dal 7° | Pos. 7-8 OR proiezione < 12 |
| Sviluppo giovani | ≥ 3 under-24 in ultima formazione AND ≥ 1 skill-up vs HRF inizio stagione | < 3 giovani in campo | Nessun progresso rilevabile |

Se la situazione diverge dall'obiettivo, compare un **banner contestuale** che suggerisce un cambio strategia (es. *"Sei 5° con 9 punti a 6 giornate dalla fine — valuta di passare a Mantenimento"*). Il banner include un pulsante per applicare il cambio.

### Zona 3 — Analisi e suggerimenti (bottom)

Il contenuto cambia in base all'obiettivo attivo.

#### Promozione
- Confronto rating reparti (difesa / centrocampo / attacco) tuoi vs media rivali del girone (dati da pagina Girone)
- Gap per reparto evidenziato con ∆ colorato (rosso se negativo, verde se positivo)
- Giocatori da cedere: basso contributo sui rating + alto stipendio
- Profilo minimo richiesto per colmare i gap (es. "serve difensore almeno buono/7")
- Schema più efficace con la rosa attuale (da `strategy.py`)

#### Mantenimento
- Reparto più debole calcolato da `strategy.py` con la rosa attuale
- Schema consigliato per compensare il punto debole
- Giocatori fuori ruolo o con forma bassa da ottimizzare

#### Sviluppo Giovani
- Lista under-24 ordinata per **score di potenziale** = `skill_principale × (24 − età) / 24`
- Per ogni giocatore: età, skill principale (label IT), delta skill vs prima HRF della stagione, specialità
- Formazione suggerita per massimizzare il minutaggio dei giovani prioritari

---

## Pagina: Girone (nuova voce nav)

Gestione squadre rivali della stessa serie. I dati sono condivisi con Pre-Partita.

### Contenuto

- **Header**: nome girone auto-rilevato dall'ultimo HRF (`league_series`, es. "VII.935") + stagione
- **Lista rivali**: tabella con nome squadra, data importazione, nr. giocatori, rating medi difesa/centrocampo/attacco
- **Per ogni rivale**:
  - Pulsante "Importa XML" → textarea per incollare il CHPP XML → parsing con `opponent_parser.py` esistente → salva in `rival_player`
  - Campi facoltativi: rating manuali difesa / centrocampo / attacco (da sito HT)
  - Badge "Usato in Pre-Partita" se il `team_id` corrisponde a un'analisi pre-partita recente
- **Aggiungi squadra**: form con solo nome + team_id (XML e rating opzionali, aggiungibili dopo)

---

## Schema DB

```sql
rival_team (
  id            INTEGER PK AUTOINCREMENT,
  team_id       INTEGER UNIQUE,
  team_name     TEXT,
  league_series TEXT,
  season        INTEGER,
  updated_at    DATETIME
)

rival_player (
  id          INTEGER PK AUTOINCREMENT,
  team_id     INTEGER FK → rival_team.team_id,
  player_id   INTEGER,
  first_name  TEXT,
  last_name   TEXT,
  goalkeeper  INTEGER DEFAULT 0,
  defending   INTEGER DEFAULT 0,
  playmaking  INTEGER DEFAULT 0,
  scoring     INTEGER DEFAULT 0,
  passing     INTEGER DEFAULT 0,
  winger      INTEGER DEFAULT 0,
  set_pieces  INTEGER DEFAULT 0,
  form        INTEGER DEFAULT 0,
  stamina     INTEGER DEFAULT 0,
  imported_at DATETIME
)

rival_ratings_manual (
  id         INTEGER PK AUTOINCREMENT,
  team_id    INTEGER FK → rival_team.team_id,
  defense    REAL,
  midfield   REAL,
  attack     REAL,
  updated_at DATETIME
)
```

`seasonal_objective` aggiunge colonna `strategy_changed_at DATETIME` per tracciare i cambi di obiettivo.

---

## API Backend

### Nuovi endpoint `/api/rivals`

| Metodo | Path | Descrizione |
|---|---|---|
| GET | `/api/rivals` | Lista squadre rivali per stagione/serie corrente |
| POST | `/api/rivals` | Crea squadra rivale (nome + team_id) |
| POST | `/api/rivals/{team_id}/import-xml` | Importa giocatori da XML CHPP |
| PUT | `/api/rivals/{team_id}/ratings` | Salva rating manuali |
| DELETE | `/api/rivals/{team_id}` | Rimuove squadra rivale |

### Nuovi endpoint `/api/seasonal/analysis`

| Metodo | Path | Descrizione |
|---|---|---|
| GET | `/api/seasonal/analysis/promote` | Gap analysis vs rivali + consigli |
| GET | `/api/seasonal/analysis/maintain` | Reparto debole + formazione |
| GET | `/api/seasonal/analysis/youth` | Under-24 ranked per potenziale |
| GET | `/api/seasonal/status` | Stato obiettivo corrente (on track / at risk / off track) + suggerimento cambio |

---

## Frontend

- `pages/Stagione.tsx` — completamente riscritto con le 3 zone
- `pages/Girone.tsx` — nuova pagina
- `api/rivals.ts` — client per i nuovi endpoint rivali
- `api/seasonal.ts` — aggiunge le chiamate agli endpoint analysis e status
- `App.tsx` — aggiunge route `/girone`

---

## Testing

- Backend: test per ogni endpoint analysis con rosa fixture + rivali fixture
- Soglie: test unitari per la logica `on_track / at_risk / off_track` con vari scenari (prima giornata, metà stagione, ultima giornata)
- Parser XML rivali: riuso dei test esistenti di `opponent_parser.py`
