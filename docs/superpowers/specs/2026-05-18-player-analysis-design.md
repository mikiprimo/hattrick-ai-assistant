# Player Analysis & Training — Design Spec
**Data:** 2026-05-18 (completata 2026-05-21)
**Stato:** Approvata

---

## Decisioni prese

### Approccio: C (Ibrido)
- Solo `PlayerSkillHistory` — nessun modello Training CHPP separato
- La pagina `/training` usa i delta skill come proxy del progresso
- Aggiungere tipo allenamento CHPP è rinviato a un piano futuro
- Funziona subito con i dati demo

### Frequenza snapshot
- Snapshot salvato ad ogni sync manuale (non automatico)

---

## Sezione 1 — Modello dati ✅

Nuova tabella `PlayerSkillHistory`:

| Campo | Tipo | Note |
|---|---|---|
| `id` | Integer PK autoincrement | |
| `player_id` | Integer FK → players.id | |
| `synced_at` | DateTime | timestamp del sync |
| `form` | Integer | |
| `tsi` | Integer | |
| `salary` | Integer | |
| `stamina` | Integer | |
| `goalkeeper` | Integer | |
| `defending` | Integer | |
| `playmaking` | Integer | |
| `winger` | Integer | |
| `passing` | Integer | |
| `scoring` | Integer | |
| `set_pieces` | Integer | |

Il sync squad esistente (`POST /api/sync/squad`) viene esteso per inserire uno snapshot per ogni giocatore dopo ogni upsert. I delta vengono calcolati lato backend al momento della query, non al momento del salvataggio.

---

## Sezione 2 — Backend API ✅

### 2a. Estensione sync esistente
`POST /api/sync/squad` viene esteso: dopo ogni upsert del giocatore, inserisce un record in `player_skill_history`.

### 2b. `GET /api/players/{id}/history`
Restituisce tutti gli snapshot del giocatore, ordinati per `synced_at` crescente. Include anche i punteggi di idoneità ruolo calcolati per l'ultimo snapshot.

```json
{
  "player_id": 123,
  "history": [
    {
      "synced_at": "2026-05-18T10:00:00",
      "form": 5,
      "tsi": 12500,
      "salary": 850,
      "stamina": 7,
      "goalkeeper": 1,
      "defending": 8,
      "playmaking": 6,
      "winger": 4,
      "passing": 5,
      "scoring": 3,
      "set_pieces": 4
    }
  ],
  "role_ratings": {
    "goalkeeper": 1.4,
    "defender": 7.1,
    "wingback": 6.0,
    "midfielder": 6.2,
    "winger": 5.2,
    "forward": 4.0
  }
}
```

### 2c. `GET /api/training`
Raggruppa gli snapshot per coppia di sync consecutive. Calcola i delta con window function `LAG` su `synced_at`. Solo i giocatori con almeno una skill cambiata compaiono in `changed_players`; gli altri in `unchanged_count`.

```json
{
  "sessions": [
    {
      "synced_at": "2026-05-21T09:00:00",
      "previous_sync": "2026-05-18T10:00:00",
      "changed_players": [
        {
          "player_id": 123,
          "player_name": "Mario Rossi",
          "age": 22,
          "deltas": {
            "defending": 1,
            "playmaking": 1,
            "winger": 0,
            "passing": 0,
            "scoring": 0,
            "set_pieces": 0,
            "stamina": 0,
            "goalkeeper": 0
          },
          "previous_values": {
            "defending": 7,
            "playmaking": 5
          },
          "current_values": {
            "defending": 8,
            "playmaking": 6
          }
        }
      ],
      "unchanged_count": 5
    }
  ]
}
```

---

## Sezione 3 — Formule idoneità ruolo ✅

Calcolate lato backend in un helper Python. Restituite nel campo `role_ratings` di `GET /api/players/{id}/history`. Scala 0–20 (stessa delle skill Hattrick).

| Ruolo | Formula |
|---|---|
| **Portiere** | goalkeeper×0.85 + stamina×0.10 + set_pieces×0.05 |
| **Difensore** | defending×0.50 + playmaking×0.20 + passing×0.15 + stamina×0.15 |
| **Terzino** | defending×0.35 + winger×0.35 + passing×0.15 + stamina×0.15 |
| **Centrocampista** | playmaking×0.50 + passing×0.20 + defending×0.15 + stamina×0.15 |
| **Ala** | winger×0.50 + passing×0.20 + scoring×0.15 + stamina×0.15 |
| **Attaccante** | scoring×0.55 + winger×0.20 + passing×0.10 + stamina×0.15 |

---

## Sezione 4 — Layout `/players/:id` ✅

**Layout: Side by side** (opzione B approvata)

```
┌─────────────────────────────────────────────────────┐
│  Mario Rossi · 22 anni · Italia                     │
├──────────────────────────────┬──────────────────────┤
│  EVOLUZIONE SKILL (LineChart)│  RUOLI (RadarChart)  │
│  flex: 2                     │  flex: 1             │
│                              │                      │
│  [Recharts LineChart]        │  [Recharts Radar]    │
│  una linea per skill         │  6 assi (POR/DIF/    │
│  tooltip al hover            │  TER/CEN/ALA/ATT)    │
│                              │                      │
│  legenda toggle skill        │                      │
└──────────────────────────────┴──────────────────────┘
```

- LineChart: asse X = `synced_at`, asse Y = valore skill 0–20. Una linea colorata per skill. Legenda cliccabile per mostrare/nascondere skill individuali.
- RadarChart: 6 assi con i punteggi `role_ratings` dell'ultimo snapshot. Tooltip con valore numerico al hover.
- Nessun scroll necessario su schermi larghi (≥1280px).

---

## Sezione 5 — Layout `/training` ✅

**Layout: Ibrido — selector sessione + card giocatore** (opzione C approvata)

```
┌─────────────────────────────────────────────────────┐
│  Allenamenti                                        │
│  [21 mag] [18 mag] [15 mag] ...  ← pill selector   │
├─────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────┐  │
│  │ Mario Rossi          Difesa +1  Regia +1      │  │
│  │   Difesa: 7 → 8   Regia: 5 → 6               │  │
│  └───────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────┐  │
│  │ Luca Bianchi                        Ala +1    │  │
│  └───────────────────────────────────────────────┘  │
│  Carlo Verdi · nessuna variazione (opacità ridotta) │
└─────────────────────────────────────────────────────┘
```

- **Pill selector** in cima: una pill per ogni sessione (coppia di sync). La sessione più recente è selezionata di default.
- **Card per giocatore**: mostra badge colorati per le skill cambiate e, espansa, i valori prima → dopo.
- I giocatori senza variazioni appaiono in fondo con opacità ridotta.
- I giocatori con variazioni sono ordinati per numero di skill cambiate (decrescente).
