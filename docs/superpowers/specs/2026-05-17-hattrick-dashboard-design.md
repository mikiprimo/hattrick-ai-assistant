# Hattrick Dashboard — Design Spec
**Data:** 2026-05-17
**Autore:** Michel Benedetti

---

## Panoramica

Tool personale per la gestione e l'analisi della propria squadra Hattrick.org. Comprende dashboard dati, analisi giocatori, mercato, partite, finanze e un modulo di preparazione pre-partita con confronto avversario e suggerimento formazione.

---

## Architettura generale

```
hattrick-dashboard/
├── backend/
│   ├── app/
│   │   ├── api/          # route FastAPI
│   │   ├── chpp/         # client CHPP + OAuth 1.0a
│   │   ├── models/       # modelli SQLAlchemy
│   │   └── main.py
│   ├── data/             # SQLite database file
│   ├── tests/
│   │   └── fixtures/     # XML reali per test parsing
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── components/
    │   ├── pages/
    │   ├── api/          # client HTTP verso FastAPI
    │   └── main.tsx
    └── package.json
```

**Stack:**
- Backend: FastAPI + SQLAlchemy + SQLite
- Frontend: React + Vite + TypeScript
- Grafici: Recharts
- Tabelle: TanStack Table
- Fetching/cache: TanStack Query
- Navigazione: React Router
- Auth CHPP: requests-oauthlib
- Parsing XML: lxml

**Fasi di sviluppo:**
1. Core: autenticazione CHPP, sync base, vista squadra
2. Analisi giocatori e allenamento
3. Analisi mercato
4. Analisi partite, finanze e pre-partita

---

## Backend

### Modelli dati (SQLAlchemy + SQLite)

| Modello | Campi chiave |
|---|---|
| `Player` | id, name, age, goalkeeping, defending, playmaking, winger, passing, scoring, set_pieces, form, stamina, injury_days, tsi, salary |
| `Match` | id, date, opponent, home/away, score, possession, ratings per ruolo |
| `Training` | week, type, intensity, players_trained |
| `Transfer` | player_id, date, price, type (buy/sell) |
| `TeamFinance` | week, balance, income, expenses, arena_revenue |
| `SyncLog` | entity, last_sync_at, status |

### Endpoint FastAPI

```
GET  /api/squad              # rosa completa con skills
GET  /api/players/{id}       # dettaglio + storico skill
GET  /api/matches            # lista partite + statistiche
GET  /api/training           # storico allenamenti
GET  /api/finances           # andamento economico
GET  /api/market/search      # ricerca giocatori sul mercato
GET  /api/next-match         # prossima partita + rosa avversario
POST /api/sync/{entity}      # trigger manuale sync (chiamato dal frontend)
GET  /api/sync/status        # stato e timestamp ultimi sync
GET  /api/settings           # configurazione corrente
POST /api/settings           # salvataggio token CHPP
```

### Client CHPP

- Autenticazione OAuth 1.0a via `requests-oauthlib`
- Token (consumer key/secret + access token/secret) salvati in SQLite
- Parsing risposte XML con `lxml`, trasformazione in dict Python prima di persistere
- Gestione rate limit: risposta 429 con messaggio esplicito al frontend

---

## Frontend

### Pagine

| Percorso | Contenuto |
|---|---|
| `/` | Dashboard: KPI squadra, forma giocatori, prossima partita, bilancio |
| `/squad` | Tabella rosa con skills, filtri e ordinamento |
| `/players/:id` | Dettaglio giocatore + grafici evoluzione skills nel tempo |
| `/matches` | Lista risultati + statistiche per partita |
| `/training` | Storico allenamenti, progressi per skill |
| `/finances` | Grafici entrate/uscite, andamento bilancio |
| `/market` | Ricerca e valutazione giocatori in vendita |
| `/next-match` | Confronto pre-partita: mia squadra vs avversario |
| `/settings` | Inserimento token CHPP, sync manuale per entità |

### Pagina `/next-match`

- Fetch automatico avversario dal calendario CHPP
- **Pannello mia squadra:** selezione formazione (4-4-2, 4-5-1, ecc.), drag & drop giocatori in campo, rating stimato per ruolo
- **Pannello avversario:** rosa con skills (se disponibili via CHPP), ultima formazione usata, risultati recenti
- **Confronto per reparto:** attacco vs difesa avversaria, centrocampo vs centrocampo (grafici a barre comparative)
- **Suggerimento formazione:** logica locale che calcola la combinazione giocatori/ruoli che massimizza i rating medi per reparto

### Componenti chiave

| Componente | Scopo |
|---|---|
| `SyncButton` | Pulsante con stato loading + timestamp ultimo sync |
| `SkillBar` | Barra visuale per i 7 skill Hattrick |
| `PlayerCard` | Card compatta per liste e dashboard |
| `SkillChart` | Grafico lineare evoluzione skill (Recharts) |
| `FinanceChart` | Grafico area per bilancio nel tempo |
| `FormationPitch` | Campo da calcio SVG con slot giocatori, drag & drop |

---

## Flusso dati

### Autenticazione

Al primo avvio l'utente inserisce le credenziali CHPP in `/settings`. I token vengono salvati in SQLite e riutilizzati per ogni richiesta firmata OAuth 1.0a.

### Sync manuale

```
[Frontend] Clicca "Sincronizza Rosa"
    → POST /api/sync/squad
    → FastAPI chiama CHPP XML API
    → Parsing XML con lxml
    → Upsert su SQLite
    → Aggiorna SyncLog con timestamp
    → Risposta { status: "ok", synced_at: "..." }
[Frontend] TanStack Query invalida cache → ri-fetch dati aggiornati
```

### Gestione errori

- Rate limit CHPP → HTTP 429 con messaggio leggibile nel frontend
- Token assenti o invalidi → redirect automatico a `/settings`
- Dati avversario non disponibili → fallback graceful in `/next-match` (mostra solo la propria squadra)

---

## Testing

**Backend (pytest):**
- Test unitari sul parsing XML CHPP — fixture reali in `backend/tests/fixtures/`
- Test sugli endpoint FastAPI — verifica formato risposta JSON
- Test sulla logica di suggerimento formazione in `/next-match`

**Frontend:**
- Verifica manuale nel browser nella fase iniziale
- Test con Vitest + React Testing Library per `FormationPitch` quando la logica cresce

---

## Avvio del progetto

```bash
# Backend (porta 8765)
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8765

# Frontend
cd frontend
npm install
npm run dev        # Vite su http://localhost:5173
```

**Con Makefile:**
```bash
make install    # installa dipendenze backend + frontend
make dev        # avvia entrambi in parallelo
```

**Al primo avvio:**
1. `make dev`
2. Apri `http://localhost:5173`
3. Vai in `/settings`, inserisci i token CHPP
4. Clicca "Sincronizza" per caricare i dati iniziali

Il frontend chiama il backend su `http://localhost:8765` — configurabile via variabile d'ambiente `VITE_API_URL`.
