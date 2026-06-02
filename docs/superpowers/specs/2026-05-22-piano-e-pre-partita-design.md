# Piano E — Pre-Partita: Design Spec
**Data:** 2026-05-22
**Autore:** Michel Benedetti

---

## Panoramica

Nuova pagina `/pre-partita` per analizzare la partita imminente e ricevere un piano di gara ottimale. L'utente incolla i file XML pubblici dell'avversario (players.xml e matches.xml in formato CHPP); il sistema calcola la formazione ottimale di entrambe le squadre, confronta i reparti e suggerisce formazione, tattica e impostazioni con spiegazione testuale.

**Fonte dati:**
- Mia squadra: dati già in DB dalla scansione HRF (Player, MatchSnapshot)
- Avversario: due textarea dove l'utente incolla `players.xml` e `matches.xml` dell'avversario (formato CHPP standard, scaricabili dalla pagina pubblica Hattrick)

---

## Architettura

### Frontend

Nuova pagina `frontend/src/pages/PrePartita.tsx` — layout split a due colonne.

**Colonna sinistra (analisi):**
1. Card "Dati avversario" con due `<textarea>` (players.xml, matches.xml) e bottone "Analizza"
2. Card "Avversario" — risultato parsing: nome squadra, formazione ottimale calcolata con rating medio per reparto, forma recente (campionato)
3. Card "Mia rosa" — dati dal DB: giocatori titolari ottimali per reparto con skill, form, stamina

**Colonna destra (piano):**
4. Card "Piano di Gara" (bordo blu) — aggiornata dopo ogni analisi:
   - Formazione consigliata con nomi giocatori
   - Confronto reparti: barre orizzontali blu/rosso con valori numerici
   - Badge impostazioni tattiche
   - Spiegazione testuale in italiano

**Nuovi componenti:**
- `OpponentInput.tsx` — due textarea con stato + bottone analizza
- `OpponentCard.tsx` — card avversario con formazione e forma recente
- `SquadOverview.tsx` — lista mia rosa ottimale per reparto (dal DB)
- `PianoGara.tsx` — confronto reparti + tattica + spiegazione

**Nuova rotta in `App.tsx`:** `/pre-partita`
**Nuova voce nav** in tutte le pagine.

**API client:** `frontend/src/api/pre_partita.ts`
- `analyzeOpponent(playersXml: string, matchesXml: string): Promise<AnalysisResult>`
- `getMySquad(): Promise<SquadOverview>`

### Backend

Nuovo router `backend/app/api/pre_partita.py` registrato in `main.py`.

**Nuovi moduli:**
- `backend/app/hrf/opponent_parser.py` — parsing players.xml e matches.xml avversario
- `backend/app/hrf/strategy.py` — logica formazione ottimale e tattica

---

## Formato XML avversario

Entrambi i file usano il formato CHPP standard di Hattrick. Nessun tag custom richiesto.

**players.xml** — struttura attesa:
```xml
<HattrickData>
  <Team>
    <TeamID>...</TeamID>
    <TeamName>...</TeamName>
    <PlayerList>
      <Player>
        <PlayerID>...</PlayerID>
        <FirstName>...</FirstName>
        <LastName>...</LastName>
        <PlayerForm>...</PlayerForm>
        <InjuryLevel>...</InjuryLevel>
        <StaminaSkill>...</StaminaSkill>
        <KeeperSkill>...</KeeperSkill>
        <DefenderSkill>...</DefenderSkill>
        <PlaymakerSkill>...</PlaymakerSkill>
        <ScorerSkill>...</ScorerSkill>
        <PassingSkill>...</PassingSkill>
        <WingerSkill>...</WingerSkill>
        <SetPiecesSkill>...</SetPiecesSkill>
      </Player>
      ...
    </PlayerList>
  </Team>
</HattrickData>
```

**matches.xml** — struttura attesa:
```xml
<HattrickData>
  <Team>
    <TeamID>...</TeamID>
    <TeamName>...</TeamName>
    <MatchList>
      <Match>
        <HomeTeam><HomeTeamID>...</HomeTeamID><HomeTeamName>...</HomeTeamName></HomeTeam>
        <AwayTeam><AwayTeamID>...</AwayTeamID><AwayTeamName>...</AwayTeamName></AwayTeam>
        <MatchDate>...</MatchDate>
        <MatchType>1</MatchType>
        <HomeGoals>...</HomeGoals>
        <AwayGoals>...</AwayGoals>
        <Status>FINISHED</Status>
      </Match>
    </MatchList>
  </Team>
</HattrickData>
```

`InjuryLevel = -1` significa giocatore sano. Valori ≥ 0 indicano giorni di infortunio — quei giocatori vengono esclusi dalla formazione ottimale.

---

## Endpoint Backend

### `GET /api/pre-partita/squad`

Restituisce la mia rosa dal DB, ordinata per ruolo migliore.

**Response:**
```json
{
  "team_name": "Sesto San Juan",
  "players": [
    {
      "id": 477889660,
      "name": "Damian Janecki",
      "form": 5,
      "stamina": 7,
      "injury_days": -1,
      "best_role": "Portiere",
      "role_rating": 11.0,
      "skills": {
        "goalkeeper": 11, "defending": 6, "playmaking": 4,
        "scoring": 5, "passing": 1, "winger": 1, "set_pieces": 12
      }
    }
  ]
}
```

### `POST /api/pre-partita/analyze`

Riceve i due XML dell'avversario, calcola formazione ottimale per entrambe le squadre, restituisce il piano di gara.

**Request body:**
```json
{
  "players_xml": "<HattrickData>...</HattrickData>",
  "matches_xml": "<HattrickData>...</HattrickData>"
}
```

**Response:**
```json
{
  "opponent": {
    "team_name": "Pace-Mela",
    "best_formation": "4-4-2",
    "line_ratings": {
      "goalkeeper": 10.5,
      "defense": 11.8,
      "midfield": 9.2,
      "attack": 8.8
    },
    "recent_results": [
      {"result": "W", "goals_for": 2, "goals_against": 0},
      {"result": "D", "goals_for": 1, "goals_against": 1}
    ]
  },
  "my_team": {
    "best_formation": "4-3-3",
    "lineup": {
      "goalkeeper": {"id": 477889660, "name": "Damian Janecki", "rating": 11.0},
      "defense": [...],
      "midfield": [...],
      "attack": [...]
    },
    "line_ratings": {
      "goalkeeper": 11.0,
      "defense": 12.8,
      "midfield": 13.1,
      "attack": 10.5
    }
  },
  "tactics": {
    "pressing": true,
    "attack_direction": "center",
    "set_pieces_taker": {"name": "Damian Janecki", "set_pieces": 12},
    "attitude": "normal"
  },
  "explanation": "Il tuo centrocampo è nettamente superiore (13.1 vs 9.2)..."
}
```

L'analisi è **stateless**: nessun dato viene salvato in DB.

---

## Logica di Calcolo

### Rating per Ruolo

Per ogni giocatore, il rating nel ruolo è calcolato usando le stesse formule già presenti in `RoleRadarChart.tsx`. Le stesse formule vengono replicate nel nuovo `strategy.py` lato backend:

| Ruolo | Formula |
|---|---|
| Portiere | `goalkeeper` |
| Terzino | `defending * 0.7 + speed * 0.3` (speed non in DB → usa stamina come proxy) |
| Difensore centrale | `defending * 0.8 + playmaking * 0.2` |
| Centrocampista | `playmaking * 0.6 + passing * 0.4` |
| Ala | `winger * 0.7 + passing * 0.3` |
| Attaccante | `scoring * 0.7 + passing * 0.3` |

Nota: `speed` non è presente nel modello `Player` del DB né nel players.xml CHPP. Si usa `stamina` come proxy per il ruolo terzino.

### Ottimizzazione Formazione

Moduli testati: `4-4-2`, `4-5-1`, `4-3-3`, `3-5-2`, `5-3-2`.

Per ogni modulo:
1. Esclude i giocatori infortunati (`injury_days >= 0`)
2. Assegna i giocatori disponibili ai ruoli con algoritmo greedy (miglior giocatore per il ruolo più vincolato prima — portiere, poi difensori, ecc.)
3. Calcola rating medio per reparto (portiere, difesa, centrocampo, attacco)
4. Confronta con i rating dell'avversario

Il modulo scelto è quello che massimizza la somma dei **vantaggi** sui reparti dell'avversario (non il totale assoluto).

### Logica Tattica

| Impostazione | Regola |
|---|---|
| Pressing | `True` se stamina media titolari ≥ 6 AND avversario ha ≤ 1 vittoria negli ultimi 4 |
| Direzione attacco | `center` se `avg(playmaking_titolari) > avg(winger_titolari)`; `wings` altrimenti |
| Calcio piazzato | Giocatore titolare con `set_pieces` massimo |
| Atteggiamento | `normal` se difesa mia ≥ difesa avversario; `defensive` altrimenti |

### Generazione Testo Spiegazione

Frasi template in italiano composte dinamicamente dai numeri calcolati. Struttura fissa:
1. Reparto di forza principale (il più vantaggioso)
2. Motivazione modulo scelto
3. Motivazione tattica (pressing, direzione)
4. Nota sul tiratore da calcio piazzato

---

## Parsing XML Avversario

`opponent_parser.py` usa `lxml` (già dipendenza del progetto).

**`parse_opponent_players(xml_str: str) -> list[OpponentPlayer]`**
- Estrae TeamID, TeamName, lista giocatori
- Ignora giocatori con InjuryLevel ≥ 0
- Mappa i tag CHPP agli stessi campi del modello Player interno

**`parse_opponent_matches(xml_str: str, team_id: int) -> list[MatchResult]`**
- `team_id` è estratto dal parsing del players.xml (`<TeamID>`) prima di chiamare questa funzione
- Filtra MatchType=1 (campionato) e Status=FINISHED
- Calcola risultato (W/D/L) in base a HomeTeamID vs team_id e goals
- Restituisce lista ordinata dalla più recente, max 5 risultati

---

## Testing

**`backend/tests/test_opponent_parser.py`**
- Parsing players.xml con dati reali (Sesto San Juan come fixture)
- Parsing matches.xml con dati reali
- Esclusione giocatori infortunati (InjuryLevel ≥ 0)
- Gestione XML malformato → eccezione con messaggio chiaro

**`backend/tests/test_strategy.py`**
- Formazione ottimale scelta correttamente dato un set noto di giocatori
- Pressing attivato/disattivato correttamente
- Direzione attacco centro vs ali
- Giocatore set pieces corretto

**`backend/tests/test_api_pre_partita.py`**
- `GET /api/pre-partita/squad` → 200 con lista giocatori
- `POST /api/pre-partita/analyze` → 200 con formazione e tattica
- `POST /api/pre-partita/analyze` con XML malformato → 422 con messaggio leggibile
- `POST /api/pre-partita/analyze` con matches_xml vuoto → 200 (matches opzionale)

---

## Fixture di Test

Usare i file XML reali forniti durante il brainstorming:
- `backend/tests/fixtures/players_sesto_san_juan.xml` — players.xml reale
- `backend/tests/fixtures/matches_sesto_san_juan.xml` — matches.xml reale

Questi file vengono usati sia come fixture "mia squadra" (per testare la logica di ottimizzazione) sia come fixture "avversario" (per testare il parsing opponent).

---

## Note Implementative

- `matches_xml` nel body della POST è **opzionale**: se assente o stringa vuota, la forma recente viene omessa e la tattica pressing si basa solo sulla stamina.
- Il DB non viene modificato da nessun endpoint di Piano E.
- La navigazione aggiunge "Pre-Partita" come voce di menu in tutte le pagine esistenti.
- Nessun drag-and-drop: la formazione è calcolata automaticamente, non modificabile dall'utente (YAGNI — eventuali override si valutano in Piano F).
