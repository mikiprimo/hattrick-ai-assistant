# Piano E — Pre-Partita: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Aggiungere pagina `/pre-partita` che riceve i file XML CHPP dell'avversario, calcola la formazione ottimale di entrambe le squadre e restituisce piano di gara con tattica e spiegazione testuale.

**Architecture:** Backend stateless con due endpoint (`GET /api/pre-partita/squad`, `POST /api/pre-partita/analyze`). Parsing XML con lxml, ottimizzazione formazione greedy su 5 moduli standard, tattica derivata da regole sui dati. Frontend split-layout: due textarea avversario a sinistra, piano di gara a destra.

**Tech Stack:** Python 3.11, FastAPI, lxml, SQLAlchemy 2.x (già installati); React 18, TypeScript, TanStack Query (già installati).

---

## File Map

**Nuovi backend:**
- `backend/tests/fixtures/players_sesto_san_juan.xml`
- `backend/tests/fixtures/matches_sesto_san_juan.xml`
- `backend/app/hrf/opponent_parser.py`
- `backend/app/hrf/strategy.py`
- `backend/app/api/pre_partita.py`
- `backend/tests/test_opponent_parser.py`
- `backend/tests/test_strategy.py`
- `backend/tests/test_api_pre_partita.py`

**Modificati backend:**
- `backend/app/main.py` — aggiunge import + include_router pre_partita

**Nuovi frontend:**
- `frontend/src/api/pre_partita.ts`
- `frontend/src/pages/PrePartita.tsx` (include sotto-componenti come funzioni locali)

**Modificati frontend:**
- `frontend/src/App.tsx` — aggiunge rotta `/pre-partita` e voce nav

---

### Task 1: Fixture XML Files

**Files:**
- Create: `backend/tests/fixtures/players_sesto_san_juan.xml`
- Create: `backend/tests/fixtures/matches_sesto_san_juan.xml`

- [ ] **Step 1: Salva players.xml**

Crea `backend/tests/fixtures/players_sesto_san_juan.xml` con il contenuto XML reale fornito nel brainstorming (il file con 24 giocatori di Sesto San Juan, TeamID=549298, tutti con InjuryLevel=-1).

- [ ] **Step 2: Salva matches.xml**

Crea `backend/tests/fixtures/matches_sesto_san_juan.xml` con il contenuto XML reale fornito nel brainstorming (TeamID=549298, 13 match di cui 4 di campionato finiti e altri upcoming).

- [ ] **Step 3: Verifica esistenza**

```bash
ls backend/tests/fixtures/
```
Expected output include: `players_sesto_san_juan.xml` e `matches_sesto_san_juan.xml`

- [ ] **Step 4: Commit**

```bash
git add backend/tests/fixtures/players_sesto_san_juan.xml backend/tests/fixtures/matches_sesto_san_juan.xml
git commit -m "test: add CHPP XML fixtures for pre-partita tests"
```

---

### Task 2: opponent_parser.py

**Files:**
- Create: `backend/app/hrf/opponent_parser.py`
- Create: `backend/tests/test_opponent_parser.py`

- [ ] **Step 1: Scrivi i test**

Crea `backend/tests/test_opponent_parser.py`:

```python
import pytest
from pathlib import Path
from app.hrf.opponent_parser import parse_opponent_players, parse_opponent_matches

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_players_returns_team_metadata():
    xml = (FIXTURES / "players_sesto_san_juan.xml").read_text()
    team_id, team_name, players = parse_opponent_players(xml)
    assert team_id == 549298
    assert team_name == "Sesto San Juan"


def test_parse_players_returns_all_healthy_players():
    xml = (FIXTURES / "players_sesto_san_juan.xml").read_text()
    _, _, players = parse_opponent_players(xml)
    assert len(players) == 24  # tutti sani nel fixture


def test_parse_players_janecki_skills():
    xml = (FIXTURES / "players_sesto_san_juan.xml").read_text()
    _, _, players = parse_opponent_players(xml)
    janecki = next(p for p in players if p.last_name == "Janecki")
    assert janecki.goalkeeper == 11
    assert janecki.set_pieces == 12
    assert janecki.stamina == 7
    assert janecki.injury_days == -1


def test_parse_players_excludes_injured():
    xml = """<HattrickData><Team><TeamID>1</TeamID><TeamName>T</TeamName><PlayerList>
      <Player><PlayerID>1</PlayerID><FirstName>Sano</FirstName><LastName>A</LastName>
        <InjuryLevel>-1</InjuryLevel><PlayerForm>5</PlayerForm><StaminaSkill>7</StaminaSkill>
        <KeeperSkill>0</KeeperSkill><DefenderSkill>10</DefenderSkill>
        <PlaymakerSkill>0</PlaymakerSkill><ScorerSkill>0</ScorerSkill>
        <PassingSkill>0</PassingSkill><WingerSkill>0</WingerSkill>
        <SetPiecesSkill>0</SetPiecesSkill></Player>
      <Player><PlayerID>2</PlayerID><FirstName>Infort</FirstName><LastName>B</LastName>
        <InjuryLevel>5</InjuryLevel><PlayerForm>5</PlayerForm><StaminaSkill>7</StaminaSkill>
        <KeeperSkill>0</KeeperSkill><DefenderSkill>10</DefenderSkill>
        <PlaymakerSkill>0</PlaymakerSkill><ScorerSkill>0</ScorerSkill>
        <PassingSkill>0</PassingSkill><WingerSkill>0</WingerSkill>
        <SetPiecesSkill>0</SetPiecesSkill></Player>
    </PlayerList></Team></HattrickData>"""
    _, _, players = parse_opponent_players(xml)
    assert len(players) == 1
    assert players[0].first_name == "Sano"


def test_parse_matches_returns_league_results_most_recent_first():
    xml = (FIXTURES / "matches_sesto_san_juan.xml").read_text()
    results = parse_opponent_matches(xml, 549298)
    # 4 campionato finiti: 2026-05-16 (D 3-3), 05-09 (D 0-0), 05-02 (D 2-2), 04-25 (L 1-4)
    assert len(results) == 4
    assert results[0].result == "D"
    assert results[0].goals_for == 3
    assert results[0].goals_against == 3


def test_parse_matches_excludes_cup_and_friendly():
    xml = (FIXTURES / "matches_sesto_san_juan.xml").read_text()
    results = parse_opponent_matches(xml, 549298)
    # solo MatchType=1, tutti i risultati devono essere W/D/L
    assert all(r.result in ("W", "D", "L") for r in results)


def test_parse_matches_win_draw_loss_logic():
    xml = """<HattrickData><Team><TeamID>100</TeamID><TeamName>X</TeamName><MatchList>
      <Match><HomeTeam><HomeTeamID>100</HomeTeamID><HomeTeamName>X</HomeTeamName></HomeTeam>
             <AwayTeam><AwayTeamID>200</AwayTeamID><AwayTeamName>Y</AwayTeamName></AwayTeam>
             <MatchType>1</MatchType><Status>FINISHED</Status>
             <HomeGoals>3</HomeGoals><AwayGoals>1</AwayGoals></Match>
      <Match><HomeTeam><HomeTeamID>200</HomeTeamID><HomeTeamName>Y</HomeTeamName></HomeTeam>
             <AwayTeam><AwayTeamID>100</AwayTeamID><AwayTeamName>X</AwayTeamName></AwayTeam>
             <MatchType>1</MatchType><Status>FINISHED</Status>
             <HomeGoals>2</HomeGoals><AwayGoals>0</AwayGoals></Match>
      <Match><HomeTeam><HomeTeamID>100</HomeTeamID><HomeTeamName>X</HomeTeamName></HomeTeam>
             <AwayTeam><AwayTeamID>200</AwayTeamID><AwayTeamName>Y</AwayTeamName></AwayTeam>
             <MatchType>1</MatchType><Status>FINISHED</Status>
             <HomeGoals>1</HomeGoals><AwayGoals>1</AwayGoals></Match>
    </MatchList></Team></HattrickData>"""
    results = parse_opponent_matches(xml, 100)
    # Most recent first (reversed): pareggio, sconfitta fuori, vittoria casa
    assert results[0].result == "D"
    assert results[1].result == "L"
    assert results[2].result == "W"


def test_parse_malformed_xml_raises():
    with pytest.raises(Exception):
        parse_opponent_players("<not valid xml")
```

- [ ] **Step 2: Esegui i test e verifica il fallimento**

```bash
cd backend && python -m pytest tests/test_opponent_parser.py -v 2>&1 | head -30
```
Expected: errori di import (`ModuleNotFoundError: app.hrf.opponent_parser`)

- [ ] **Step 3: Implementa opponent_parser.py**

Crea `backend/app/hrf/opponent_parser.py`:

```python
from dataclasses import dataclass
from lxml import etree


@dataclass
class OpponentPlayer:
    player_id: int
    first_name: str
    last_name: str
    form: int
    stamina: int
    injury_days: int
    goalkeeper: int
    defending: int
    playmaking: int
    scoring: int
    passing: int
    winger: int
    set_pieces: int


@dataclass
class MatchResult:
    result: str  # "W", "D", "L"
    goals_for: int
    goals_against: int


def parse_opponent_players(xml_str: str) -> tuple[int, str, list[OpponentPlayer]]:
    root = etree.fromstring(xml_str.encode())
    team = root.find(".//Team")
    team_id = int(team.findtext("TeamID", "0"))
    team_name = team.findtext("TeamName", "")

    players = []
    for el in team.findall(".//PlayerList/Player"):
        def i(tag: str, default: int = 0) -> int:
            try:
                return int(el.findtext(tag, str(default)))
            except (ValueError, TypeError):
                return default

        if i("InjuryLevel", -1) >= 0:
            continue

        players.append(OpponentPlayer(
            player_id=i("PlayerID"),
            first_name=el.findtext("FirstName", ""),
            last_name=el.findtext("LastName", ""),
            form=i("PlayerForm"),
            stamina=i("StaminaSkill"),
            injury_days=-1,
            goalkeeper=i("KeeperSkill"),
            defending=i("DefenderSkill"),
            playmaking=i("PlaymakerSkill"),
            scoring=i("ScorerSkill"),
            passing=i("PassingSkill"),
            winger=i("WingerSkill"),
            set_pieces=i("SetPiecesSkill"),
        ))
    return team_id, team_name, players


def parse_opponent_matches(xml_str: str, team_id: int) -> list[MatchResult]:
    root = etree.fromstring(xml_str.encode())
    results = []
    for match in root.findall(".//MatchList/Match"):
        if match.findtext("MatchType") != "1":
            continue
        if match.findtext("Status") != "FINISHED":
            continue
        home_id = int(match.findtext(".//HomeTeamID", "0"))
        home_goals = int(match.findtext("HomeGoals", "0"))
        away_goals = int(match.findtext("AwayGoals", "0"))
        if home_id == team_id:
            gf, ga = home_goals, away_goals
        else:
            gf, ga = away_goals, home_goals
        result = "W" if gf > ga else ("D" if gf == ga else "L")
        results.append(MatchResult(result=result, goals_for=gf, goals_against=ga))
    results.reverse()
    return results[:5]
```

- [ ] **Step 4: Esegui i test e verifica che passino**

```bash
cd backend && python -m pytest tests/test_opponent_parser.py -v
```
Expected: tutti PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/hrf/opponent_parser.py backend/tests/test_opponent_parser.py
git commit -m "feat: add opponent XML parser for players.xml and matches.xml"
```

---

### Task 3: strategy.py

**Files:**
- Create: `backend/app/hrf/strategy.py`
- Create: `backend/tests/test_strategy.py`

- [ ] **Step 1: Scrivi i test**

Crea `backend/tests/test_strategy.py`:

```python
import pytest
from dataclasses import dataclass
from app.hrf.strategy import role_rating, optimize_formation, compute_tactics, generate_explanation
from app.hrf.opponent_parser import MatchResult


@dataclass
class P:
    """Fake player per i test."""
    first_name: str = "X"
    last_name: str = "Y"
    injury_days: int = -1
    stamina: int = 7
    goalkeeper: int = 0
    defending: int = 0
    playmaking: int = 0
    scoring: int = 0
    passing: int = 0
    winger: int = 0
    set_pieces: int = 3


def squad(gk=10, df=10, mid=10, win=10, fwd=10):
    """11 giocatori con skill mirate per testare l'assegnazione."""
    return [
        P(first_name="GK", last_name="GK", goalkeeper=gk, set_pieces=8),
        P(first_name="D1", last_name="D1", defending=df),
        P(first_name="D2", last_name="D2", defending=df - 1),
        P(first_name="D3", last_name="D3", defending=df - 2),
        P(first_name="D4", last_name="D4", defending=df - 3),
        P(first_name="M1", last_name="M1", playmaking=mid),
        P(first_name="M2", last_name="M2", playmaking=mid - 1),
        P(first_name="W1", last_name="W1", winger=win),
        P(first_name="W2", last_name="W2", winger=win - 1),
        P(first_name="F1", last_name="F1", scoring=fwd),
        P(first_name="F2", last_name="F2", scoring=fwd - 1),
    ]


# --- role_rating ---

def test_role_rating_goalkeeper():
    assert role_rating(P(goalkeeper=11), "goalkeeper") == 11.0


def test_role_rating_center_defender():
    p = P(defending=10, playmaking=5)
    assert role_rating(p, "center_defender") == pytest.approx(10 * 0.8 + 5 * 0.2)


def test_role_rating_side_defender():
    p = P(defending=10, stamina=5)
    assert role_rating(p, "side_defender") == pytest.approx(10 * 0.7 + 5 * 0.3)


def test_role_rating_inside_mid():
    p = P(playmaking=10, passing=5)
    assert role_rating(p, "inside_mid") == pytest.approx(10 * 0.6 + 5 * 0.4)


def test_role_rating_winger():
    p = P(winger=10, passing=5)
    assert role_rating(p, "winger") == pytest.approx(10 * 0.7 + 5 * 0.3)


def test_role_rating_forward():
    p = P(scoring=10, passing=5)
    assert role_rating(p, "forward") == pytest.approx(10 * 0.7 + 5 * 0.3)


# --- optimize_formation ---

def test_optimize_formation_assigns_best_goalkeeper():
    players = squad(gk=15)
    _, data = optimize_formation(players, {"goalkeeper": 5, "defense": 5, "midfield": 5, "attack": 5})
    gk_entry = next(e for e in data["lineup"] if e["line"] == "goalkeeper")
    assert gk_entry["player"].first_name == "GK"


def test_optimize_formation_excludes_injured():
    players = squad()
    players[0].injury_days = 3  # GK infortunato
    _, data = optimize_formation(players, {})
    gk_entry = next(e for e in data["lineup"] if e["line"] == "goalkeeper")
    assert gk_entry["player"].first_name != "GK"


def test_optimize_formation_returns_valid_formation_name():
    valid = {"4-4-2", "4-5-1", "4-3-3", "3-5-2", "5-3-2"}
    name, _ = optimize_formation(squad(), {})
    assert name in valid


def test_optimize_formation_line_ratings_present():
    _, data = optimize_formation(squad(), {})
    for line in ("goalkeeper", "defense", "midfield", "attack"):
        assert line in data["line_ratings"]
        assert data["line_ratings"][line] >= 0


def test_optimize_formation_picks_formation_exploiting_opp_weakness():
    # Avversario debolissimo in attacco (5) — la mia difesa forte (15) dovrebbe portare
    # a scegliere un modulo che massimizza il vantaggio difensivo
    players = squad(df=15, mid=8, fwd=8)
    opp = {"goalkeeper": 10, "defense": 10, "midfield": 10, "attack": 5}
    name, _ = optimize_formation(players, opp)
    assert name in {"4-4-2", "4-5-1", "4-3-3", "3-5-2", "5-3-2"}


# --- compute_tactics ---

def _lineup_11(stamina=7, playmaking=8, winger=6, defending=10, sp_taker_sp=5):
    gk = P(first_name="GK", last_name="GK", goalkeeper=10, stamina=stamina, set_pieces=sp_taker_sp)
    return (
        [{"player": gk, "line": "goalkeeper", "role": "goalkeeper"}]
        + [{"player": P(stamina=stamina, defending=defending, set_pieces=1), "line": "defense", "role": "center_defender"} for _ in range(4)]
        + [{"player": P(stamina=stamina, playmaking=playmaking, set_pieces=1), "line": "midfield", "role": "inside_mid"} for _ in range(4)]
        + [{"player": P(stamina=stamina, scoring=8, winger=winger, set_pieces=1), "line": "attack", "role": "forward"} for _ in range(2)]
    )


def test_compute_tactics_pressing_on_when_stamina_ok_and_opp_weak():
    lineup = _lineup_11(stamina=8)
    recent = [MatchResult("L", 0, 1), MatchResult("D", 0, 0), MatchResult("L", 0, 2), MatchResult("D", 0, 0)]
    tactics = compute_tactics(lineup, {}, recent)
    assert tactics["pressing"] is True


def test_compute_tactics_pressing_off_when_opp_strong():
    lineup = _lineup_11(stamina=8)
    recent = [MatchResult("W", 2, 0), MatchResult("W", 3, 0), MatchResult("W", 1, 0), MatchResult("W", 2, 1)]
    tactics = compute_tactics(lineup, {}, recent)
    assert tactics["pressing"] is False


def test_compute_tactics_pressing_off_when_stamina_low():
    lineup = _lineup_11(stamina=4)
    recent = [MatchResult("L", 0, 1), MatchResult("L", 0, 2), MatchResult("L", 0, 3), MatchResult("L", 0, 1)]
    tactics = compute_tactics(lineup, {}, recent)
    assert tactics["pressing"] is False


def test_compute_tactics_attack_direction_center_when_playmaking_dominates():
    lineup = _lineup_11(playmaking=14, winger=4)
    tactics = compute_tactics(lineup, {}, [])
    assert tactics["attack_direction"] == "center"


def test_compute_tactics_attack_direction_wings_when_winger_dominates():
    lineup = _lineup_11(playmaking=4, winger=14)
    tactics = compute_tactics(lineup, {}, [])
    assert tactics["attack_direction"] == "wings"


def test_compute_tactics_set_pieces_taker_is_highest():
    lineup = _lineup_11(sp_taker_sp=12)
    tactics = compute_tactics(lineup, {}, [])
    assert tactics["set_pieces_taker"]["name"] == "GK GK"
    assert tactics["set_pieces_taker"]["set_pieces"] == 12


def test_compute_tactics_attitude_normal_when_defense_ok():
    lineup = _lineup_11(defending=12)
    opp = {"defense": 10}
    tactics = compute_tactics(lineup, opp, [])
    assert tactics["attitude"] == "normal"


def test_compute_tactics_attitude_defensive_when_defense_weak():
    lineup = _lineup_11(defending=5)
    opp = {"defense": 14}
    tactics = compute_tactics(lineup, opp, [])
    assert tactics["attitude"] == "defensive"


# --- generate_explanation ---

def test_generate_explanation_mentions_best_line():
    my = {"goalkeeper": 11.0, "defense": 13.0, "midfield": 15.0, "attack": 10.0}
    opp = {"goalkeeper": 9.0, "defense": 10.0, "midfield": 9.0, "attack": 8.0}
    tactics = {"pressing": True, "attack_direction": "center",
               "set_pieces_taker": {"name": "Mario Rossi", "set_pieces": 12}, "attitude": "normal"}
    text = generate_explanation(my, opp, "4-3-3", tactics)
    assert "centrocampo" in text.lower()
    assert "4-3-3" in text
    assert "pressing" in text.lower()
    assert "Mario Rossi" in text


def test_generate_explanation_returns_nonempty_string():
    my = {"goalkeeper": 8.0, "defense": 8.0, "midfield": 8.0, "attack": 8.0}
    opp = {"goalkeeper": 8.0, "defense": 8.0, "midfield": 8.0, "attack": 8.0}
    tactics = {"pressing": False, "attack_direction": "wings",
               "set_pieces_taker": None, "attitude": "normal"}
    text = generate_explanation(my, opp, "4-4-2", tactics)
    assert len(text) > 10
```

- [ ] **Step 2: Esegui i test e verifica il fallimento**

```bash
cd backend && python -m pytest tests/test_strategy.py -v 2>&1 | head -30
```
Expected: `ModuleNotFoundError: app.hrf.strategy`

- [ ] **Step 3: Implementa strategy.py**

Crea `backend/app/hrf/strategy.py`:

```python
FORMATIONS = {
    "4-4-2": {"side_defenders": 2, "center_defenders": 2, "inside_mids": 2, "wingers": 2, "forwards": 2},
    "4-5-1": {"side_defenders": 2, "center_defenders": 2, "inside_mids": 3, "wingers": 2, "forwards": 1},
    "4-3-3": {"side_defenders": 2, "center_defenders": 2, "inside_mids": 1, "wingers": 2, "forwards": 3},
    "3-5-2": {"side_defenders": 0, "center_defenders": 3, "inside_mids": 3, "wingers": 2, "forwards": 2},
    "5-3-2": {"side_defenders": 2, "center_defenders": 3, "inside_mids": 1, "wingers": 2, "forwards": 2},
}


def role_rating(p, role: str) -> float:
    if role == "goalkeeper":
        return float(p.goalkeeper)
    if role == "side_defender":
        return p.defending * 0.7 + p.stamina * 0.3
    if role == "center_defender":
        return p.defending * 0.8 + p.playmaking * 0.2
    if role == "inside_mid":
        return p.playmaking * 0.6 + p.passing * 0.4
    if role == "winger":
        return p.winger * 0.7 + p.passing * 0.3
    if role == "forward":
        return p.scoring * 0.7 + p.passing * 0.3
    return 0.0


def _assign(available: list, role: str, n: int) -> list:
    result = []
    for _ in range(n):
        if not available:
            break
        best = max(available, key=lambda p: role_rating(p, role))
        result.append(best)
        available.remove(best)
    return result


def _build_lineup(players: list, formation_name: str) -> dict:
    available = list(players)
    f = FORMATIONS[formation_name]

    gk = _assign(available, "goalkeeper", 1)
    side_defs = _assign(available, "side_defender", f["side_defenders"])
    center_defs = _assign(available, "center_defender", f["center_defenders"])
    wingers = _assign(available, "winger", f["wingers"])
    inside_mids = _assign(available, "inside_mid", f["inside_mids"])
    forwards = _assign(available, "forward", f["forwards"])

    all_defs = side_defs + center_defs
    all_mids = wingers + inside_mids

    def avg(lst, role):
        if not lst:
            return 0.0
        return sum(role_rating(p, role) for p in lst) / len(lst)

    line_ratings = {
        "goalkeeper": role_rating(gk[0], "goalkeeper") if gk else 0.0,
        "defense": (
            sum(role_rating(p, "side_defender") for p in side_defs) +
            sum(role_rating(p, "center_defender") for p in center_defs)
        ) / len(all_defs) if all_defs else 0.0,
        "midfield": (
            sum(role_rating(p, "winger") for p in wingers) +
            sum(role_rating(p, "inside_mid") for p in inside_mids)
        ) / len(all_mids) if all_mids else 0.0,
        "attack": avg(forwards, "forward"),
    }

    lineup = []
    if gk:
        lineup.append({"player": gk[0], "line": "goalkeeper", "role": "goalkeeper"})
    for p in side_defs:
        lineup.append({"player": p, "line": "defense", "role": "side_defender"})
    for p in center_defs:
        lineup.append({"player": p, "line": "defense", "role": "center_defender"})
    for p in wingers:
        lineup.append({"player": p, "line": "midfield", "role": "winger"})
    for p in inside_mids:
        lineup.append({"player": p, "line": "midfield", "role": "inside_mid"})
    for p in forwards:
        lineup.append({"player": p, "line": "attack", "role": "forward"})

    return {"lineup": lineup, "line_ratings": line_ratings}


def optimize_formation(players, opp_line_ratings: dict) -> tuple[str, dict]:
    healthy = [p for p in players if getattr(p, "injury_days", -1) < 0]
    best_name, best_score, best_data = None, float("-inf"), None
    for name in FORMATIONS:
        data = _build_lineup(healthy, name)
        score = sum(
            max(0.0, data["line_ratings"][line] - opp_line_ratings.get(line, 0.0))
            for line in ("goalkeeper", "defense", "midfield", "attack")
        )
        if score > best_score:
            best_score, best_name, best_data = score, name, data
    return best_name, best_data


def compute_tactics(lineup_data: list, opp_line_ratings: dict, recent_results: list) -> dict:
    titolari = [e["player"] for e in lineup_data]

    stamina_avg = sum(p.stamina for p in titolari) / len(titolari) if titolari else 0
    opp_wins = sum(1 for r in recent_results[:4] if r.result == "W")
    pressing = stamina_avg >= 6 and opp_wins <= 1

    outfield = [e["player"] for e in lineup_data if e["line"] != "goalkeeper"]
    avg_ply = sum(p.playmaking for p in outfield) / len(outfield) if outfield else 0
    avg_win = sum(p.winger for p in outfield) / len(outfield) if outfield else 0
    attack_direction = "center" if avg_ply >= avg_win else "wings"

    sp_player = max(titolari, key=lambda p: p.set_pieces) if titolari else None
    set_pieces_taker = (
        {"name": f"{sp_player.first_name} {sp_player.last_name}", "set_pieces": sp_player.set_pieces}
        if sp_player else None
    )

    def_players = [e["player"] for e in lineup_data if e["line"] == "defense"]
    my_def_avg = sum(p.defending for p in def_players) / len(def_players) if def_players else 0
    attitude = "normal" if my_def_avg >= opp_line_ratings.get("defense", 0) else "defensive"

    return {
        "pressing": pressing,
        "attack_direction": attack_direction,
        "set_pieces_taker": set_pieces_taker,
        "attitude": attitude,
    }


def generate_explanation(my_line_ratings: dict, opp_line_ratings: dict,
                         formation: str, tactics: dict) -> str:
    LINE_IT = {
        "goalkeeper": "portiere", "defense": "difesa",
        "midfield": "centrocampo", "attack": "attacco",
    }
    diffs = {k: my_line_ratings.get(k, 0) - opp_line_ratings.get(k, 0) for k in LINE_IT}
    best = max(diffs, key=lambda k: diffs[k])
    my_v, opp_v, diff = my_line_ratings.get(best, 0), opp_line_ratings.get(best, 0), diffs[best]

    parts = []
    if diff > 3:
        parts.append(f"il tuo {LINE_IT[best]} è nettamente superiore ({my_v:.1f} vs {opp_v:.1f})")
    elif diff > 0:
        parts.append(f"il tuo {LINE_IT[best]} è superiore ({my_v:.1f} vs {opp_v:.1f})")
    else:
        parts.append("la partita è equilibrata")

    parts.append(f"usa il {formation} per massimizzare questo vantaggio")

    if tactics.get("pressing"):
        parts.append("applica il pressing: la tua resistenza è maggiore")

    if tactics.get("attack_direction") == "center":
        parts.append("attacca al centro dove il tuo playmaking domina")
    else:
        parts.append("usa le fasce dove i tuoi ali fanno la differenza")

    sp = tactics.get("set_pieces_taker")
    if sp:
        parts.append(f"calci piazzati a {sp['name']} (SP {sp['set_pieces']})")

    return ". ".join(parts).capitalize() + "."
```

- [ ] **Step 4: Esegui i test e verifica che passino**

```bash
cd backend && python -m pytest tests/test_strategy.py -v
```
Expected: tutti PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/hrf/strategy.py backend/tests/test_strategy.py
git commit -m "feat: add formation optimizer and tactics engine for pre-partita"
```

---

### Task 4: pre_partita.py + main.py + test

**Files:**
- Create: `backend/app/api/pre_partita.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_api_pre_partita.py`

- [ ] **Step 1: Scrivi i test**

Crea `backend/tests/test_api_pre_partita.py`:

```python
from pathlib import Path
from app.models.player import Player

FIXTURES = Path(__file__).parent / "fixtures"


def _add_squad(db):
    """11 giocatori sani per testare gli endpoint."""
    players = [
        Player(id=1, first_name="GK", last_name="One", goalkeeper=11, stamina=7, set_pieces=8),
        Player(id=2, first_name="D", last_name="Two", defending=13, stamina=7),
        Player(id=3, first_name="D", last_name="Three", defending=12, stamina=7),
        Player(id=4, first_name="D", last_name="Four", defending=11, stamina=7),
        Player(id=5, first_name="D", last_name="Five", defending=10, stamina=7),
        Player(id=6, first_name="M", last_name="Six", playmaking=14, stamina=7),
        Player(id=7, first_name="M", last_name="Seven", playmaking=12, stamina=7),
        Player(id=8, first_name="W", last_name="Eight", winger=12, stamina=7),
        Player(id=9, first_name="W", last_name="Nine", winger=10, stamina=7),
        Player(id=10, first_name="F", last_name="Ten", scoring=11, stamina=7),
        Player(id=11, first_name="F", last_name="Eleven", scoring=9, stamina=7),
    ]
    for p in players:
        db.add(p)
    db.commit()


def test_get_squad_empty(client):
    r = client.get("/api/pre-partita/squad")
    assert r.status_code == 200
    assert r.json()["players"] == []


def test_get_squad_returns_players_with_skills(client, db):
    _add_squad(db)
    r = client.get("/api/pre-partita/squad")
    assert r.status_code == 200
    data = r.json()
    assert len(data["players"]) == 11
    p = data["players"][0]
    assert "name" in p
    assert "best_role" in p
    assert "role_rating" in p
    assert "skills" in p
    assert "form" in p
    assert "stamina" in p
    assert "injury_days" in p


def test_analyze_returns_complete_structure(client, db):
    _add_squad(db)
    players_xml = (FIXTURES / "players_sesto_san_juan.xml").read_text()
    r = client.post("/api/pre-partita/analyze", json={
        "players_xml": players_xml,
        "matches_xml": "",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["opponent"]["team_name"] == "Sesto San Juan"
    assert data["opponent"]["best_formation"] in {"4-4-2", "4-5-1", "4-3-3", "3-5-2", "5-3-2"}
    assert set(data["opponent"]["line_ratings"]) == {"goalkeeper", "defense", "midfield", "attack"}
    assert data["opponent"]["recent_results"] == []
    assert data["my_team"]["best_formation"] in {"4-4-2", "4-5-1", "4-3-3", "3-5-2", "5-3-2"}
    assert set(data["my_team"]["lineup"]) == {"goalkeeper", "defense", "midfield", "attack"}
    assert set(data["tactics"]) == {"pressing", "attack_direction", "set_pieces_taker", "attitude"}
    assert isinstance(data["explanation"], str) and len(data["explanation"]) > 10


def test_analyze_with_matches_xml_returns_recent_results(client, db):
    _add_squad(db)
    players_xml = (FIXTURES / "players_sesto_san_juan.xml").read_text()
    matches_xml = (FIXTURES / "matches_sesto_san_juan.xml").read_text()
    r = client.post("/api/pre-partita/analyze", json={
        "players_xml": players_xml,
        "matches_xml": matches_xml,
    })
    assert r.status_code == 200
    results = r.json()["opponent"]["recent_results"]
    assert len(results) == 4
    assert results[0]["result"] in ("W", "D", "L")
    assert "goals_for" in results[0]


def test_analyze_malformed_players_xml_returns_422(client, db):
    _add_squad(db)
    r = client.post("/api/pre-partita/analyze", json={
        "players_xml": "<invalid",
        "matches_xml": "",
    })
    assert r.status_code == 422
    assert "players_xml" in r.json()["detail"].lower()


def test_analyze_malformed_matches_xml_returns_422(client, db):
    _add_squad(db)
    players_xml = (FIXTURES / "players_sesto_san_juan.xml").read_text()
    r = client.post("/api/pre-partita/analyze", json={
        "players_xml": players_xml,
        "matches_xml": "<invalid",
    })
    assert r.status_code == 422
    assert "matches_xml" in r.json()["detail"].lower()


def test_analyze_tactics_direction_is_valid(client, db):
    _add_squad(db)
    players_xml = (FIXTURES / "players_sesto_san_juan.xml").read_text()
    r = client.post("/api/pre-partita/analyze", json={"players_xml": players_xml, "matches_xml": ""})
    assert r.json()["tactics"]["attack_direction"] in ("center", "wings")


def test_analyze_set_pieces_taker_present(client, db):
    _add_squad(db)
    players_xml = (FIXTURES / "players_sesto_san_juan.xml").read_text()
    r = client.post("/api/pre-partita/analyze", json={"players_xml": players_xml, "matches_xml": ""})
    sp = r.json()["tactics"]["set_pieces_taker"]
    assert sp is not None
    assert "name" in sp
    assert "set_pieces" in sp
```

- [ ] **Step 2: Esegui i test e verifica il fallimento**

```bash
cd backend && python -m pytest tests/test_api_pre_partita.py -v 2>&1 | head -30
```
Expected: `404 Not Found` su tutti gli endpoint (router non registrato)

- [ ] **Step 3: Implementa pre_partita.py**

Crea `backend/app/api/pre_partita.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.player import Player
from app.hrf.opponent_parser import parse_opponent_players, parse_opponent_matches
from app.hrf.strategy import role_rating, optimize_formation, compute_tactics, generate_explanation

router = APIRouter()

ROLES = [
    ("goalkeeper", "Portiere"),
    ("side_defender", "Terzino"),
    ("center_defender", "Difensore"),
    ("inside_mid", "Centrocampista"),
    ("winger", "Ala"),
    ("forward", "Attaccante"),
]


@router.get("/pre-partita/squad")
def get_squad(db: Session = Depends(get_db)):
    players = db.query(Player).all()
    result = []
    for p in players:
        best_role_key, best_role_label = max(ROLES, key=lambda r: role_rating(p, r[0]))
        result.append({
            "id": p.id,
            "name": f"{p.first_name} {p.last_name}",
            "form": p.form,
            "stamina": p.stamina,
            "injury_days": p.injury_days,
            "best_role": best_role_label,
            "role_rating": round(role_rating(p, best_role_key), 1),
            "skills": {
                "goalkeeper": p.goalkeeper,
                "defending": p.defending,
                "playmaking": p.playmaking,
                "scoring": p.scoring,
                "passing": p.passing,
                "winger": p.winger,
                "set_pieces": p.set_pieces,
            },
        })
    return {"players": result}


class AnalyzeRequest(BaseModel):
    players_xml: str
    matches_xml: str = ""


@router.post("/pre-partita/analyze")
def analyze(body: AnalyzeRequest, db: Session = Depends(get_db)):
    try:
        opp_team_id, opp_team_name, opp_players = parse_opponent_players(body.players_xml)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"players_xml non valido: {e}")

    opp_recent = []
    if body.matches_xml.strip():
        try:
            opp_recent = parse_opponent_matches(body.matches_xml, opp_team_id)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"matches_xml non valido: {e}")

    opp_formation, opp_data = optimize_formation(opp_players, {})
    opp_ratings = opp_data["line_ratings"]

    my_players = db.query(Player).all()
    my_formation, my_data = optimize_formation(my_players, opp_ratings)
    my_ratings = my_data["line_ratings"]

    tactics = compute_tactics(my_data["lineup"], opp_ratings, opp_recent)
    explanation = generate_explanation(my_ratings, opp_ratings, my_formation, tactics)

    def fmt_lineup(lineup_data):
        by_line: dict[str, list] = {"goalkeeper": [], "defense": [], "midfield": [], "attack": []}
        for entry in lineup_data:
            p = entry["player"]
            line = entry["line"]
            by_line[line].append({
                "id": p.id,
                "name": f"{p.first_name} {p.last_name}",
                "rating": round(role_rating(p, entry["role"]), 1),
            })
        return by_line

    return {
        "opponent": {
            "team_name": opp_team_name,
            "best_formation": opp_formation,
            "line_ratings": {k: round(v, 1) for k, v in opp_ratings.items()},
            "recent_results": [
                {"result": r.result, "goals_for": r.goals_for, "goals_against": r.goals_against}
                for r in opp_recent
            ],
        },
        "my_team": {
            "best_formation": my_formation,
            "lineup": fmt_lineup(my_data["lineup"]),
            "line_ratings": {k: round(v, 1) for k, v in my_ratings.items()},
        },
        "tactics": tactics,
        "explanation": explanation,
    }
```

- [ ] **Step 4: Registra il router in main.py**

In `backend/app/main.py` aggiungi dopo gli import esistenti:

```python
from app.api import pre_partita as pre_partita_router
```

E dopo l'ultimo `app.include_router`:

```python
app.include_router(pre_partita_router.router, prefix="/api")
```

- [ ] **Step 5: Esegui tutti i test**

```bash
cd backend && python -m pytest tests/test_api_pre_partita.py tests/test_strategy.py tests/test_opponent_parser.py -v
```
Expected: tutti PASS

- [ ] **Step 6: Esegui la suite completa**

```bash
cd backend && python -m pytest -v
```
Expected: tutti i test esistenti continuano a passare + nuovi PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/pre_partita.py backend/app/main.py backend/tests/test_api_pre_partita.py
git commit -m "feat: add pre-partita API endpoints (squad + analyze)"
```

---

### Task 5: Frontend

**Files:**
- Create: `frontend/src/api/pre_partita.ts`
- Create: `frontend/src/pages/PrePartita.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Crea il client API**

Crea `frontend/src/api/pre_partita.ts`:

```typescript
import { apiFetch } from './client'

export interface PlayerSkills {
  goalkeeper: number
  defending: number
  playmaking: number
  scoring: number
  passing: number
  winger: number
  set_pieces: number
}

export interface SquadPlayer {
  id: number
  name: string
  form: number
  stamina: number
  injury_days: number
  best_role: string
  role_rating: number
  skills: PlayerSkills
}

export interface SquadResponse {
  players: SquadPlayer[]
}

export interface LineupEntry {
  id: number
  name: string
  rating: number
}

export interface MatchResult {
  result: 'W' | 'D' | 'L'
  goals_for: number
  goals_against: number
}

export interface AnalysisResult {
  opponent: {
    team_name: string
    best_formation: string
    line_ratings: Record<string, number>
    recent_results: MatchResult[]
  }
  my_team: {
    best_formation: string
    lineup: Record<string, LineupEntry[]>
    line_ratings: Record<string, number>
  }
  tactics: {
    pressing: boolean
    attack_direction: 'center' | 'wings'
    set_pieces_taker: { name: string; set_pieces: number } | null
    attitude: 'normal' | 'defensive'
  }
  explanation: string
}

export function getPrePartitaSquad(): Promise<SquadResponse> {
  return apiFetch<SquadResponse>('/api/pre-partita/squad')
}

export function analyzeOpponent(
  players_xml: string,
  matches_xml: string,
): Promise<AnalysisResult> {
  return apiFetch<AnalysisResult>('/api/pre-partita/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ players_xml, matches_xml }),
  })
}
```

- [ ] **Step 2: Crea la pagina PrePartita.tsx**

Crea `frontend/src/pages/PrePartita.tsx`:

```typescript
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getPrePartitaSquad, analyzeOpponent } from '../api/pre_partita'
import type { AnalysisResult, SquadPlayer } from '../api/pre_partita'

const card: React.CSSProperties = {
  background: '#fff',
  borderRadius: 8,
  border: '1px solid #e5e7eb',
  padding: '12px 16px',
  marginBottom: 12,
}

const LINE_LABELS: Record<string, string> = {
  goalkeeper: 'Portiere',
  defense: 'Difesa',
  midfield: 'Centrocampo',
  attack: 'Attacco',
}

const RESULT_STYLE: Record<string, React.CSSProperties> = {
  W: { background: '#dcfce7', color: '#16a34a' },
  D: { background: '#fef9c3', color: '#854d0e' },
  L: { background: '#fee2e2', color: '#dc2626' },
}

function LineBars({
  myRatings,
  oppRatings,
}: {
  myRatings: Record<string, number>
  oppRatings: Record<string, number>
}) {
  const lines = ['goalkeeper', 'defense', 'midfield', 'attack']
  const max = 20
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      {lines.map(line => {
        const my = myRatings[line] ?? 0
        const opp = oppRatings[line] ?? 0
        return (
          <div key={line}>
            <div style={{ fontSize: 10, color: '#6b7280', marginBottom: 2 }}>
              {LINE_LABELS[line]} {my > opp ? '✅' : ''}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ width: 36, textAlign: 'right', fontSize: 11, color: '#1d4ed8', fontWeight: my > opp ? 600 : 400 }}>
                {my.toFixed(1)}
              </span>
              <div style={{ flex: 1, height: 12, background: '#e5e7eb', borderRadius: 6, position: 'relative', overflow: 'hidden' }}>
                <div style={{ position: 'absolute', left: 0, top: 0, width: `${(my / max) * 100}%`, height: '100%', background: '#3b82f6', borderRadius: '6px 0 0 6px', opacity: 0.8 }} />
                <div style={{ position: 'absolute', right: 0, top: 0, width: `${(opp / max) * 100}%`, height: '100%', background: '#ef4444', borderRadius: '0 6px 6px 0', opacity: 0.5 }} />
              </div>
              <span style={{ width: 36, fontSize: 11, color: '#dc2626' }}>{opp.toFixed(1)}</span>
            </div>
          </div>
        )
      })}
      <div style={{ display: 'flex', gap: 10, marginTop: 2, fontSize: 9, color: '#6b7280' }}>
        <span><span style={{ color: '#3b82f6' }}>■</span> Tu</span>
        <span><span style={{ color: '#ef4444' }}>■</span> Avversario</span>
      </div>
    </div>
  )
}

function TacticBadge({ label, value }: { label: string; value: string }) {
  return (
    <span style={{
      fontSize: 10, padding: '3px 8px', borderRadius: 12,
      background: '#eff6ff', color: '#1d4ed8',
    }}>
      {label}: <strong>{value}</strong>
    </span>
  )
}

export function PrePartita() {
  const [playersXml, setPlayersXml] = useState('')
  const [matchesXml, setMatchesXml] = useState('')
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const { data: squadData } = useQuery({
    queryKey: ['pre-partita-squad'],
    queryFn: getPrePartitaSquad,
  })

  async function handleAnalyze() {
    if (!playersXml.trim()) return
    setLoading(true)
    setError(null)
    try {
      const res = await analyzeOpponent(playersXml, matchesXml)
      setResult(res)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }

  const myByLine = result
    ? (['goalkeeper', 'defense', 'midfield', 'attack'] as const).reduce(
        (acc, line) => {
          const entries = result.my_team.lineup[line] ?? []
          if (entries.length) acc[line] = entries.map(e => e.name).join(', ')
          return acc
        },
        {} as Record<string, string>,
      )
    : {}

  const squadByRole = (squadData?.players ?? []).reduce(
    (acc: Record<string, SquadPlayer[]>, p) => {
      const role = p.injury_days >= 0 ? 'Infortunati' : p.best_role
      if (!acc[role]) acc[role] = []
      acc[role].push(p)
      return acc
    },
    {},
  )

  return (
    <div>
      <h1 style={{ margin: '0 0 20px' }}>Pre-Partita</h1>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, alignItems: 'start' }}>

        {/* LEFT */}
        <div>
          {/* Opponent input */}
          <div style={card}>
            <div style={{ fontWeight: 600, marginBottom: 10 }}>⚔️ Dati avversario</div>

            <div style={{ marginBottom: 8 }}>
              <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 4 }}>players.xml</div>
              <textarea
                value={playersXml}
                onChange={e => setPlayersXml(e.target.value)}
                placeholder="Incolla qui il players.xml dell'avversario..."
                rows={5}
                style={{ width: '100%', fontFamily: 'monospace', fontSize: 11, border: '1px solid #e5e7eb', borderRadius: 4, padding: 8, resize: 'vertical', boxSizing: 'border-box' }}
              />
            </div>

            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 4 }}>matches.xml (opzionale)</div>
              <textarea
                value={matchesXml}
                onChange={e => setMatchesXml(e.target.value)}
                placeholder="Incolla qui il matches.xml dell'avversario (opzionale)..."
                rows={5}
                style={{ width: '100%', fontFamily: 'monospace', fontSize: 11, border: '1px solid #e5e7eb', borderRadius: 4, padding: 8, resize: 'vertical', boxSizing: 'border-box' }}
              />
            </div>

            <button
              onClick={handleAnalyze}
              disabled={loading || !playersXml.trim()}
              style={{
                width: '100%', padding: '8px 0', background: loading ? '#93c5fd' : '#3b82f6',
                color: '#fff', border: 'none', borderRadius: 6, cursor: loading ? 'not-allowed' : 'pointer',
                fontWeight: 600, fontSize: 14,
              }}
            >
              {loading ? 'Analisi in corso…' : 'Analizza avversario'}
            </button>

            {error && <p style={{ color: '#ef4444', fontSize: 12, marginTop: 8 }}>{error}</p>}
          </div>

          {/* Opponent card */}
          {result && (
            <div style={card}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <strong>{result.opponent.team_name}</strong>
                <span style={{ fontSize: 11, color: '#6b7280' }}>
                  Formazione ottimale: <strong>{result.opponent.best_formation}</strong>
                </span>
              </div>

              {(['goalkeeper', 'defense', 'midfield', 'attack'] as const).map(line => {
                const rating = result.opponent.line_ratings[line]
                const pct = (rating / 20) * 100
                return (
                  <div key={line} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ width: 90, fontSize: 11, color: '#6b7280' }}>{LINE_LABELS[line]}</span>
                    <div style={{ flex: 1, height: 8, background: '#e5e7eb', borderRadius: 4 }}>
                      <div style={{ width: `${pct}%`, height: '100%', background: '#ef4444', borderRadius: 4 }} />
                    </div>
                    <span style={{ width: 28, fontSize: 11, textAlign: 'right', color: '#374151' }}>{rating.toFixed(1)}</span>
                  </div>
                )
              })}

              {result.opponent.recent_results.length > 0 && (
                <div style={{ marginTop: 8 }}>
                  <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 4 }}>Forma recente:</div>
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    {result.opponent.recent_results.map((r, i) => (
                      <span key={i} style={{ ...RESULT_STYLE[r.result], fontSize: 10, padding: '2px 6px', borderRadius: 4 }}>
                        {r.result} {r.goals_for}-{r.goals_against}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* My squad */}
          {squadData && squadData.players.length > 0 && (
            <div style={card}>
              <div style={{ fontWeight: 600, marginBottom: 8 }}>👥 Mia rosa</div>
              {Object.entries(squadByRole).map(([role, players]) => (
                <div key={role} style={{ marginBottom: 6 }}>
                  <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 2 }}>{role}</div>
                  {players.map(p => (
                    <div key={p.id} style={{
                      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                      fontSize: 11, padding: '2px 6px', borderRadius: 3,
                      background: p.injury_days >= 0 ? '#fef2f2' : '#eff6ff',
                      marginBottom: 2, opacity: p.injury_days >= 0 ? 0.5 : 1,
                    }}>
                      <span>{p.name} {p.injury_days >= 0 ? '🤕' : ''}</span>
                      <span style={{ color: '#6b7280' }}>Form {p.form} · Stam {p.stamina}</span>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* RIGHT: Piano di gara */}
        <div style={{ ...card, border: result ? '2px solid #3b82f6' : '1px solid #e5e7eb' }}>
          {!result ? (
            <div style={{ textAlign: 'center', padding: '40px 0', color: '#9ca3af' }}>
              <div style={{ fontSize: 32, marginBottom: 8 }}>🎯</div>
              <div>Incolla i dati dell'avversario e clicca "Analizza"</div>
            </div>
          ) : (
            <>
              <div style={{ color: '#1d4ed8', fontWeight: 700, marginBottom: 12 }}>🎯 Piano di Gara</div>

              {/* Formazione */}
              <div style={{ background: '#eff6ff', borderRadius: 6, padding: 10, marginBottom: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#1d4ed8', marginBottom: 6 }}>
                  Formazione: {result.my_team.best_formation}
                </div>
                {(['goalkeeper', 'defense', 'midfield', 'attack'] as const).map(line =>
                  myByLine[line] ? (
                    <div key={line} style={{ fontSize: 11, color: '#1e40af', marginBottom: 2, textAlign: 'center' }}>
                      {myByLine[line]}
                    </div>
                  ) : null,
                )}
              </div>

              {/* Confronto reparti */}
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8 }}>Confronto reparti</div>
                <LineBars myRatings={result.my_team.line_ratings} oppRatings={result.opponent.line_ratings} />
              </div>

              {/* Tattica */}
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Impostazioni tattiche</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  <TacticBadge label="Pressing" value={result.tactics.pressing ? 'Sì' : 'No'} />
                  <TacticBadge label="Attacco" value={result.tactics.attack_direction === 'center' ? 'Centro' : 'Fasce'} />
                  {result.tactics.set_pieces_taker && (
                    <TacticBadge
                      label="CP"
                      value={`${result.tactics.set_pieces_taker.name} (SP ${result.tactics.set_pieces_taker.set_pieces})`}
                    />
                  )}
                  <TacticBadge label="Att." value={result.tactics.attitude === 'normal' ? 'Normale' : 'Difensivo'} />
                </div>
              </div>

              {/* Spiegazione */}
              <div style={{ background: '#f8fafc', borderLeft: '3px solid #3b82f6', padding: 10, borderRadius: '0 6px 6px 0' }}>
                <div style={{ fontSize: 11, fontWeight: 600, marginBottom: 4 }}>💡 Analisi</div>
                <div style={{ fontSize: 11, color: '#4b5563', lineHeight: 1.6 }}>{result.explanation}</div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Aggiungi rotta e voce nav in App.tsx**

In `frontend/src/App.tsx` aggiungi l'import:

```typescript
import { PrePartita } from './pages/PrePartita'
```

Aggiungi il `NavLink` nella nav (dopo `Partite`, prima di `Impostazioni`):

```typescript
<NavLink to="/pre-partita" style={navStyle}>Pre-Partita</NavLink>
```

Aggiungi la rotta nell'array `children`:

```typescript
{ path: 'pre-partita', element: <PrePartita /> },
```

- [ ] **Step 4: Controlla il TypeScript**

```bash
cd frontend && npx tsc --noEmit
```
Expected: 0 errori

- [ ] **Step 5: Verifica i test backend**

```bash
cd backend && python -m pytest -v
```
Expected: tutti i test passano (numero precedente + nuovi)

- [ ] **Step 6: Commit finale**

```bash
git add frontend/src/api/pre_partita.ts frontend/src/pages/PrePartita.tsx frontend/src/App.tsx
git commit -m "feat: add Pre-Partita page with opponent XML analysis and game plan"
```
