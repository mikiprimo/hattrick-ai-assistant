# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Hattrick AI Assistant — a dashboard for the [Hattrick](https://www.hattrick.org) browser football manager game that tracks player skill evolution and recommends optimal training and pre-match tactics. Italian is used in UI labels and some code strings (the game is popular in Italy).

## Commands

```bash
# Install all dependencies
make install           # pip install -r backend/requirements.txt && npm install in frontend

# Run both servers concurrently (backend :8765, frontend :5173)
make dev

# Run only backend or frontend
make backend           # uvicorn app.main:app --reload --port 8765
make frontend          # npm run dev (Vite, port 5173)

# Backend tests (run from repo root)
make test              # cd backend && pytest -v

# Run a single test file
cd backend && pytest tests/test_hrf_parser.py -v

# Frontend type-check + lint
cd frontend && npm run build   # tsc -b && vite build
cd frontend && npm run lint
```

## Documentation
the files of hattrick's rules and engine are inside in .claude/docs/


## Architecture

Two-tier app: a **FastAPI** backend (Python, SQLAlchemy, SQLite) and a **React 19 + TypeScript + Vite** frontend.

### Data Sources

The backend ingests player data from two independent sources:

1. **CHPP** (`backend/app/chpp/`) — Hattrick's official XML API, accessed via OAuth1 (`requests-oauthlib`). Credentials are stored in the `CHPPSettings` SQLAlchemy model. `CHPPClient.fetch()` hits `https://chpp.hattrick.org/chppxml.ashx`. The sync flow is triggered via `POST /api/sync/{entity}` and writes to `Player` and `PlayerSkillHistory`.

2. **HRF files** (`backend/app/hrf/`) — Hattrick Reference Files exported by the HRF desktop tool. Files are named `TEAMID-YYYY-MM-DD.hrf` (INI format). `scanner.py` discovers files in a configured folder; `parser.py` parses each file into `HRFSnapshot` objects (dataclasses defined in `hrf/models.py`). HRF data is stored in `PlayerSkillHistory` with `source="HRF"`.

### Backend Structure

```
backend/app/
  main.py          — FastAPI app setup; loads all models before create_all; runs migrations
  database.py      — SQLAlchemy engine + get_db() dependency; DB path: backend/data/hattrick.db
  migrations.py    — Ad-hoc migration runner (called at startup)
  models/          — SQLAlchemy ORM models (Player, CHPPSettings, SyncLog, PlayerSkillHistory, HRFSettings, MatchSnapshot)
  api/             — One router module per domain area, all mounted at /api
  chpp/            — CHPP HTTP client + XML parsers (lxml)
  hrf/             — HRF file scanner, parser, strategy optimizer, and opponent parser
```

**All models must be imported in `main.py` before `Base.metadata.create_all()`** — the comment there is intentional.

### Pre-Match Strategy (`hrf/strategy.py`)

`optimize_formation()` tries all five formations (4-4-2, 4-5-1, 4-3-3, 3-5-2, 5-3-2) against the opponent's line ratings and picks the best score. `compute_tactics()` derives pressing, attack direction, set-pieces taker, and attitude. `generate_explanation()` returns an Italian-language summary string.

### Frontend Structure

React Router v7 with a single `Layout` shell. State fetching uses **TanStack Query** (`@tanstack/react-query`). Charts use **Recharts**. Tables use **TanStack Table**.

```
frontend/src/
  App.tsx          — Router definition
  api/             — One TS module per backend endpoint group (mirrors backend api/)
  pages/           — Full page components (Dashboard, Squad, PlayerDetail, Training, Matches, PrePartita, Settings)
  components/      — Reusable pieces (SkillBar, SkillLineChart, RoleRadarChart, DeltaBadge, etc.)
```

### Testing

Tests live in `backend/tests/`. The `conftest.py` fixtures create an **in-memory SQLite database** and a `TestClient` wrapping the FastAPI app — no real CHPP calls, no filesystem DB. HRF parser tests use fixture `.hrf` files in `tests/fixtures/`. Run a single test: `cd backend && pytest tests/test_<name>.py -v`.
