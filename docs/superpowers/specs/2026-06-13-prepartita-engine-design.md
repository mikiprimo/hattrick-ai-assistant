# Pre-Partita Engine — Enhanced Match Analysis

**Data**: 2026-06-13  
**Spec A di 2**: Enhanced Pre-Partita (questo spec). Spec B = Season Planner (futuro).

---

## Problema

Il motore Pre-Partita attuale costruisce la formazione ottimale a partire dalle skill dei giocatori, ma ignora tre variabili decisive:

1. **Casa o trasferta** — la stessa formazione ottimale cambia radicalmente (~12% home/away modifier sui rating)
2. **Tattiche avversarie reali** — senza TacticType/TacticSkill non si può rilevare il Pressing o la wing weakness
3. **XP tattica propria** — consigliare "Attacco sulle Fasce" senza sapere se il team lo sa eseguire è dannoso

Tutto questo emerge dall'analisi su Sesto San Juan vs i tarallos (sessione 2026-06-13): Pressing TacticSkill=18 + MidDef=46 + wing defense 24-25 → la tattica corretta era Attacco sulle Fasce, non Normal.

---

## Scope

**In scope (Spec A)**:
- Parsing `matchdetails.xml` avversario (1-3 partite di campionato)
- Flag casa/trasferta
- Modello `TacticXP` (nuovo)
- Estensione `strategy.py`: home/away modifier, wing weakness, pressing detection, tactic recommendation con XP, sub plan condizionale, attitude orders
- API `AnalyzeRequest` aggiornata
- Frontend: step 1 + step 2 + output step 3

**Fuori scope (Spec B — Season Planner)**:
- Raccomandazione pre-stagionale di formazioni/tattiche su cui investire XP
- Dashboard XP accumulato nel tempo

---

## Architettura

```
FRONTEND (wizard 3 step)
  Step 1: spirito, fiducia, match_type, is_home [NUOVO]
  Step 2: 3 tab matchdetails XML (tab1 obbligatorio, tab2/3 facoltativi)
          [SOSTITUISCE players_xml + matches_xml]
  Step 3: formazione + tattica consigliata + sub plan + attitude orders

      │  POST /api/pre-partita/analyze
      ▼

BACKEND
  opponent_parser.py
    parse_opponent_matchdetails(xml) → OppMatchData
    average_opponent_profiles([OppMatchData]) → OppProfile

  strategy.py
    apply_home_away_modifier(ratings, is_home) → ratings
    detect_wing_weakness(opp_ratings) → bool
    detect_pressing(opp_profile) → bool
    recommend_tactic(opp_profile, my_lineup, is_home, my_tactic_xp) → TacticRec
    generate_sub_plan(lineup, bench, is_home, spirit, confidence) → list[SubOrder]
    generate_attitude_orders(sub_plan, is_home, spirit, confidence) → list[AttitudeOrder]

  pre_partita.py
    AnalyzeRequest esteso
    Response estesa
```

---

## Modello dati

### TacticXP (nuovo)

```python
class TacticXP(Base):
    __tablename__ = "tactic_xp"
    id:           int (PK)
    tactic_name:  str   # uno dei 7 valori di TACTIC_NAMES in strategy.py
    xp_level:     int   # 0–20, stessa scala di FormationXP
    updated_at:   datetime
```

Valori validi per `tactic_name`: `"Normal"`, `"Pressing"`, `"Contropiede"`, `"Attacco al Centro"`, `"Attacco sulle Fasce"`, `"Tiri da Fuori"`, `"Libertà d'Inventiva"`.

Migrazione ad-hoc in `migrations.py` (stesso pattern delle migrazioni esistenti).

### Nuovi endpoint TacticXP

```
GET  /api/pre-partita/tactic-xp   → { tactic_xp: { "Pressing": 12, ... } }
PUT  /api/pre-partita/tactic-xp   → body: { tactic_name, xp_level }
```

Speculari agli endpoint `formation-xp` esistenti. Stessa validazione.

---

## Backend — opponent_parser.py

### `parse_opponent_matchdetails(xml: str) -> OppMatchData`

Legge un `matchdetails.xml` CHPP (MatchType=1, campionato). Estrae:

```python
@dataclass
class OppMatchData:
    team_id:      int
    team_name:    str
    match_date:   date
    formation:    str
    tactic_type:  int   # 0–6, mappa a TACTIC_NAMES
    tactic_skill: int   # 0–20
    line_ratings: dict  # chiavi: midfield, mid_def, mid_att,
                        #         right_def, left_def, right_att, left_att
    is_home:      bool  # se il team era in casa in quella partita
```

Se `MatchType != 1` solleva `ValueError("Solo partite di campionato accettate")`.

### `average_opponent_profiles(matches: list[OppMatchData]) -> OppProfile`

Media pesata (peso decrescente: tab 1 = peso 3, tab 2 = peso 2, tab 3 = peso 1). Tab 1 è la partita più recente — l'utente deve incollare le partite in ordine cronologico inverso (prima l'ultima giocata).

```python
@dataclass
class OppProfile:
    team_id:           int
    team_name:         str
    avg_line_ratings:  dict   # stesse chiavi di OppMatchData.line_ratings
    dominant_tactic:   int | None   # tactic_type usato in ≥2/3 partite, else None
    avg_tactic_skill:  float
    typical_formation: str    # formazione più frequente
    matches_used:      int    # 1, 2 o 3
```

I rating delle partite in cui l'avversario era in casa vengono deflazionati del 12% prima della media (normalizzazione al contesto neutro).

---

## Backend — strategy.py

### `apply_home_away_modifier(ratings: dict, is_home: bool) -> dict`

Applica il modificatore ai **rating avversari già mediati** prima che vengano usati come `opp_line_ratings` in `optimize_formation()`:
- `is_home=True` (noi in casa): moltiplica i rating avversari per `0.88` (loro senza vantaggio casalingo)
- `is_home=False` (noi in trasferta): moltiplica i rating avversari per `1.06` (loro con vantaggio casalingo)

Il vantaggio casalingo per **la nostra** squadra viene gestito aggiungendo `home_mod: float` a `optimize_formation()` — stesso schema di `spirit_mod` e `confidence_mod` già esistenti. Si applica ai `modified_ratings` dopo il calcolo:
- `is_home=True`: `home_mod = 1.06`
- `is_home=False`: `home_mod = 1.00`

I rating avversari dalla media sono già normalizzati a contesto neutro (deflazione 12% delle partite giocate in casa dall'avversario in `average_opponent_profiles()`).

### `detect_wing_weakness(opp_ratings: dict) -> bool`

```python
wing_avg = (opp_ratings["right_def"] + opp_ratings["left_def"]) / 2
return wing_avg < opp_ratings["mid_def"] * 0.70
```

### Mapping TacticType CHPP

| Valore | Tattica |
|--------|---------|
| 0 | Normal |
| 1 | Pressing |
| 2 | Contropiede |
| 3 | Attacco al Centro |
| 4 | Attacco sulle Fasce |
| 5 | Tiri da Fuori |
| 6 | Libertà d'Inventiva |

### `detect_pressing(opp_profile: OppProfile) -> bool`

```python
return opp_profile.dominant_tactic == 1  # TacticType 1 = Pressing
```

### `detect_center_attack(opp_profile: OppProfile) -> bool`

```python
return opp_profile.dominant_tactic == 3  # TacticType 3 = Attacco al Centro
```

Entrambi portano alla stessa raccomandazione (bonus Attacco sulle Fasce) ma per motivi diversi:
- Pressing (1): boosta il centrocampo avversario → le fasce lo bypassano
- Attacco al Centro (3): tutta la spinta va al centro → i fianchi sono esposti

### `recommend_tactic(opp_profile, my_lineup, is_home, my_tactic_xp) -> TacticRec`

```python
@dataclass
class TacticRec:
    name:        str
    score:       float
    explanation: str   # stringa italiana
    warnings:    list[str]   # es. "XP Pressing insufficiente (3/20)"
```

Logica:
1. Calcola score base per ogni tattica (refactor di `rank_tactics()` esistente)
2. Applica moltiplicatore `TacticXP` (stesso schema di `_apply_xp_modifier()`)
3. Bonus `+20%` ad "Attacco sulle Fasce" se `detect_wing_weakness()` è True
4. Bonus `+15%` ad "Attacco sulle Fasce" se `detect_pressing()` è True (bypassa il boost mid del Pressing avversario)
5. Bonus `+15%` ad "Attacco sulle Fasce" se `detect_center_attack()` è True (fianchi avversari esposti per concentrazione al centro)
5. Restituisce la tattica con score più alto; aggiunge warning se XP < 8

### `generate_sub_plan(lineup, bench, is_home, spirit, confidence) -> list[SubOrder]`

```python
@dataclass
class SubOrder:
    slot:      int         # 1, 2, 3
    minute:    int
    condition: str         # "fisso" | "se non in vantaggio" | "se in vantaggio" | "se in svantaggio"
    out_name:  str
    out_role:  str
    out_stam:  int
    in_name:   str | None  # None se non c'è sostituto adeguato in panchina
    in_role:   str | None
    in_stam:   int | None
    reason:    str         # stringa italiana
```

Algoritmo:
1. **Slot 1 — fisso per stamina critica**: giocatore con `stamina ≤ 5` tra i titolari non GK → minuto = `stamina * 12 - 3` (es. stam 5 → 57')
2. **Slot 2 — condizionale offensivo**: se non in vantaggio al 65-70', esce l'IM meno offensivo, entra il miglior scorer in panchina
3. **Slot 3**:
   - `is_home=True`: se in vantaggio al 75', difensore/IM difensivo — "blinda"
   - `is_home=False`: se in svantaggio di 1 gol all'80' — unico momento in cui rischi

Il sostituto è scelto con lo stesso filtro ruolo già corretto in questa sessione (etichette italiane: "Difensore", "Centrocampista", ecc.) e con `best_role != "Portiere"` nel fallback.

### `generate_attitude_orders(sub_plan, is_home, spirit, confidence) -> list[AttitudeOrder]`

```python
@dataclass
class AttitudeOrder:
    minute:    int
    condition: str
    attitude:  str   # "Offensivo" | "Difensivo (PIC)" | "Non cambiare"
    reason:    str
```

I minuti **non sono costanti**: vengono derivati dal `sub_plan` già generato, in modo che gli ordini di atteggiamento siano coerenti con i cambi programmati. La firma riceve `sub_plan: list[SubOrder]` come primo argomento.

**Vincolo Hattrick**: i minuti per gli ordini condizionali sono discreti — solo multipli di 5 nel range 60'–85'. Il sistema calcola il minuto ideale e lo arrotonda al multiplo di 5 più vicino con `_snap_to_hattrick_minute(m) = round(m / 5) * 5`, clampato a [60, 85].

**Logica di derivazione per ciascun ordine:**

**1. Offensivo se in svantaggio**
- Ancora: minuto del sub con `condition="se non in vantaggio"` (slot offensivo) + 2'
- Ragionamento: il sostituto offensivo entra, poi si alza l'atteggiamento per sfruttarlo subito
- Fallback se nessun sub offensivo: 70'

**2. Difensivo se in vantaggio**
- Ancora: minuto dell'ultimo slot di sub disponibile - 3'
- Ragionamento: si cambia atteggiamento poco prima di usare l'ultimo slot per "blindare"
- Fallback: 75'

**3. Gestione del pareggio**
- Ancora: `90 - (90 - minuto_ultimo_sub_disponibile) / 2` → punto medio tra l'ultimo cambio e il 90'
- `is_home=True`: Offensivo — in casa un pareggio non basta, si spinge
- `is_home=False`: Non cambiare — in trasferta un punto vale oro, non si rischia
- Fallback: 80'

**Esempio con sub plan [57' fisso, 65' condizionale, 80' condizionale]:**

| Ordine | Calcolo | Minuto snapped | Condizione | Atteggiamento |
|--------|---------|----------------|------------|---------------|
| Offensivo | 65 + 2 = 67 → snap | 65' | se in svantaggio | Offensivo |
| Difensivo | 80 - 3 = 77 → snap | 75' | se in vantaggio | Difensivo (PIC) |
| Pareggio  | (90+80)/2 = 85 → snap | 85' | se in pareggio | Non cambiare (trasferta) |

Atteggiamento iniziale calcolato da `recommend_attitude()` esistente (invariato).

---

## API — AnalyzeRequest e Response

### Request

```python
class AnalyzeRequest(BaseModel):
    match_type:           str = "league"
    spirit:               int = 10
    confidence:           int = 10
    formation_xp:         dict[str, int] = {}
    is_home:              bool = True           # NUOVO
    matchdetails_xml_1:   str                   # obbligatorio
    matchdetails_xml_2:   str = ""              # facoltativo
    matchdetails_xml_3:   str = ""              # facoltativo
    tactic_xp:            dict[str, int] = {}   # NUOVO
    # rimossi: players_xml, matches_xml
```

### Response — nuovi campi

```json
{
  "opponent": {
    "team_name": "...",
    "typical_formation": "2-5-3",
    "tactic_type": "Pressing",
    "tactic_skill": 18,
    "matches_used": 2,
    "wing_weakness": true,
    "line_ratings": { "mid_def": 41.8, "mid_att": 43.2, ... }
  },
  "my_team": {
    "best_formation": "4-4-2",
    "lineup": { ... },
    "tactic_recommendation": {
      "name": "Attacco sulle Fasce",
      "score": 9.1,
      "explanation": "La loro difesa laterale (media 22) è vulnerabile. Il Pressing avversario non impatta il gioco sulle fasce.",
      "warnings": []
    },
    "sub_plan": [
      {
        "slot": 1, "minute": 57, "condition": "fisso",
        "out_name": "Armando Forigüa", "out_role": "CD", "out_stam": 5,
        "in_name": "Daley Kruiskamp", "in_role": "Centrocampista", "in_stam": 7,
        "reason": "Stamina 5: calo rating garantito oltre il 60'."
      }
    ],
    "attitude_orders": [
      { "minute": 70, "condition": "se in svantaggio", "attitude": "Offensivo",
        "reason": "Spingi per il pareggio prima che calino le energie." },
      { "minute": 75, "condition": "se in vantaggio", "attitude": "Difensivo (PIC)",
        "reason": "Blinda il risultato." },
      { "minute": 80, "condition": "se in pareggio", "attitude": "Non cambiare",
        "reason": "In trasferta un punto vale oro." }
    ]
  }
}
```

`tactic_ranking` esistente rimane nella response per backward compatibility ma `tactic_recommendation` è il campo autorevole.

---

## Frontend

### Step 1

Aggiunta unica: dropdown `is_home` affiancato a `match_type` nella griglia esistente.

```
[Tipo partita ▼]  [Casa ▼ / Trasferta]
```

### Step 2

I due textarea (`players_xml`, `matches_xml`) sostituiti da 3 tab:

```
[ Partita 1 * ]  [ Partita 2 ]  [ Partita 3 ]
┌─────────────────────────────────────────────┐
│ Incolla matchdetails.xml (campionato)        │
│ <textarea>                                   │
└─────────────────────────────────────────────┘
```

- Tab 1: obbligatorio per abilitare "Analizza"
- Tab 2-3: facoltativi, asterisco (*) sul tab se compilato
- Label sotto: "Usa le ultime 2-3 partite di campionato per una media più stabile"

### Step 2 — TacticXP (nuovo blocco sotto i tab)

Stesso componente slider/input del FormationXP esistente, replicato per le 7 tattiche. Collassabile di default (la maggior parte delle volte l'utente non lo tocca).

### Step 3 — output

**Rimosso**: `tactic_ranking` (lista delle 7 tattiche con score).

**Nuovo blocco "Tattica consigliata"** (sopra la formazione, evidenziato):
```
┌─ Attacco sulle Fasce ──────────────────── score 9.1 ─┐
│ La loro difesa laterale (media 22) è vulnerabile.     │
│ Il Pressing avversario non impatta il gioco sulle     │
│ fasce. XP: Buono (12/20).                             │
│ ⚠ Wing weakness rilevata  ✓ Counter-pressing attivo   │
└───────────────────────────────────────────────────────┘
```

**Rimosso**: sub plan generato lato client (il piano fisso 60/70/80').

**Nuovo blocco "Piano sostituzioni"**:
```
~57' [FISSO]     Forigüa (CD, st.5) → Kruiskamp (Centrocampista, st.7)
                 Stamina 5: calo rating garantito oltre il 60'.

~65' [SE NON ↑]  Kruiskamp (IM) → Myrttinen (Attaccante, st.7)
                 Difensori avversari stanchi dal pressing — punta fresca.

~80' [SE ↓ 1]   Ala → secondo attaccante
                 Unico momento in cui rischi in trasferta.
```

**Nuovo blocco "Ordini atteggiamento"** (tabella compatta):
```
Minuto │ Condizione        │ Atteggiamento   │ Motivo
70'    │ Se in svantaggio  │ Offensivo       │ Spingi per il pareggio
75'    │ Se in vantaggio   │ Difensivo (PIC) │ Blinda il risultato
80'    │ Se in pareggio    │ Non cambiare    │ In trasferta 1 punto vale oro
```

---

## Testing

- `test_opponent_parser.py`: aggiungere fixture `matchdetails.xml` di campionato + test `parse_opponent_matchdetails()` e `average_opponent_profiles()` (1 e 3 partite)
- `test_strategy.py`: test per ogni nuova funzione (`apply_home_away_modifier`, `detect_wing_weakness`, `detect_pressing`, `recommend_tactic`, `generate_sub_plan`, `generate_attitude_orders`)
- `test_api_pre_partita.py`: aggiornare test esistenti per la nuova firma `AnalyzeRequest`; aggiungere test per `tactic-xp` endpoints
- `test_migrations.py`: verificare creazione tabella `tactic_xp`

---

## Decisioni prese

| Decisione | Motivazione |
|-----------|-------------|
| Peso 3-2-1 nella media rating avversario | La partita più recente è più predittiva |
| Deflazione 12% per partite giocate in casa dall'avversario | Normalizza al contesto neutro prima della media |
| `tactic_ranking` non rimosso dalla response | Backward compatibility — il frontend lo ignora ma non crasha |
| Minuto sub = `stamina * 12 - 3` | Empirico: stam 5 → 57', stam 6 → 69', si avvicina al crollo reale |
| `is_home=False @pareggio → Non cambiare` | In trasferta 1 punto è il risultato accettabile |
| Minuti attitude orders derivati dal sub plan | I minuti 70/75/80 di una singola analisi non sono costanti universali — il contesto tattico cambia a seconda di quando avvengono i cambi |
| Snap a multipli di 5 nel range [60,85] | Hattrick accetta solo minuti discreti per gli ordini condizionali |
