# Hattrick AI Assistant

> An open source web application for Hattrick managers — squad analysis, training planning, and match review, powered by the official CHPP API.

---

## Features

- **Squad analysis** — player skills, experience, and estimated market value; filtering and sorting for transfer and lineup decisions
- **Training management** — current training type, intensity, staff levels, and skill development projections
- **Match analysis** — statistics, lineups, and rating trends per 15-minute segment across recent matches

All data access is **strictly read-only**. No data is written back to Hattrick.

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Vue 3 + Vite |
| Backend | FastAPI (Python 3.12) |
| Database | PostgreSQL |
| Cache | Redis (CHPP responses, TTL 15 min) |
| Auth | OAuth2 via Hattrick CHPP |
| Deploy | Docker / Podman (compose) |

---

## CHPP feeds used

| Module | Feeds |
|---|---|
| Squad | `Players`, `PlayerDetails`, `TransfersTeam`, `Avatars`, `TeamDetails` |
| Training | `Training`, `TrainingEvents`, `Players`, `StaffList`, `Economy` |
| Matches | `Matches`, `MatchesArchive`, `MatchDetails`, `MatchLineup`, `Standings`, `Worlddetails` |

---

## Getting started

### Prerequisites

- Docker or Podman with compose support
- A Hattrick account with CHPP access

### Run locally

```bash
git clone https://github.com/mikiprimo/hattrick-ai-assistant.git
cd hattrick-ai-assistant
cp .env.example .env
# edit .env with your CHPP client_id and client_secret
docker compose up
```

The app will be available at `http://localhost:5173`.

---

## CHPP credentials

This application requires a CHPP product license issued by Hattrick.  
Apply at: [https://chpp.hattrick.org/chppform.aspx](https://chpp.hattrick.org/chppform.aspx)

Each user authenticates individually via OAuth2 — no data is shared between users.

---

## Contributing

Pull requests are welcome. Please open an issue first to discuss what you would like to change.

---

## License

[MIT](LICENSE)

---

---

# Hattrick AI Assistant *(italiano)*

> Applicazione web open source per i manager di Hattrick — analisi rosa, pianificazione allenamento e analisi partite, tramite le API CHPP ufficiali.

## Funzionalità

- **Analisi rosa** — skill, esperienza e valore di mercato stimato; filtri e ordinamenti per decisioni su trasferimenti e formazione
- **Gestione allenamento** — tipo di allenamento, intensità, livello staff e proiezioni di sviluppo delle skill
- **Analisi partite** — statistiche, formazioni e andamento dei rating per quarto d'ora sulle ultime partite

Tutti gli accessi ai dati sono **esclusivamente in lettura**. Nessun dato viene scritto su Hattrick.

## Avvio rapido

```bash
git clone https://github.com/mikiprimo/hattrick-ai-assistant.git
cd hattrick-ai-assistant
cp .env.example .env
# modifica .env con client_id e client_secret CHPP
docker compose up
```

L'app sarà disponibile su `http://localhost:5173`.

## Licenza

[MIT](LICENSE)
