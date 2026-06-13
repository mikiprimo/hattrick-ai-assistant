# Pre-Partita Engine — Enhanced Match Analysis

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade Pre-Partita to use real CHPP matchdetails ratings (1–3 matches), home/away context, TacticXP, stamina-aware substitution plan, and dynamically-derived conditional attitude orders.

**Architecture:** New functions in `opponent_parser.py` parse matchdetails XMLs and average ratings across 1–3 matches. `strategy.py` gains detection helpers (`detect_wing_weakness`, `detect_pressing`, `detect_center_attack`), generation functions (`generate_sub_plan`, `generate_attitude_orders`), and a new `recommend_tactic()`. The `analyze` endpoint receives a new request schema (matchdetails replaces players_xml/matches_xml); `TacticXP` follows the `FormationXP` pattern exactly. Frontend wizard gains an is_home toggle, 3-tab XML input, and new output blocks for sub plan and attitude orders.

**Tech Stack:** FastAPI, SQLAlchemy + SQLite, lxml (XML), Python dataclasses, React 19 + TypeScript, TanStack Query

---

## File Map

### Create
- `backend/app/models/tactic_xp.py`
- `backend/tests/fixtures/matchdetails_tarallos_1.xml`
- `backend/tests/fixtures/matchdetails_tarallos_2.xml`

### Modify
- `backend/app/main.py` — import TacticXP before create_all
- `backend/app/hrf/opponent_parser.py` — add TeamMatchData, OppMatchData, OppProfile dataclasses; parse_both_teams, detect_opponent_team_id, parse_opponent_matchdetails, average_opponent_profiles
- `backend/app/hrf/strategy.py` — add _chpp_to_app_scale, apply_home_away_modifier, detection functions, recommend_tactic, generate_sub_plan, generate_attitude_orders; extend optimize_formation with home_mod param
- `backend/app/api/pre_partita.py` — TacticXP endpoints (GET/PUT); replace AnalyzeRequest + analyze endpoint
- `backend/tests/test_api_pre_partita.py` — replace analyze tests for new API, keep squad/formation_xp/save/history tests

### Frontend (new)
- `frontend/src/api/pre_partita.ts` — update TypeScript types
- `frontend/src/pages/PrePartita.tsx` — is_home toggle, 3-tab XML input, TacticXP panel, sub plan + attitude orders output

---

## Task 1: TacticXP Model

**Files:**
- Create: `backend/app/models/tactic_xp.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Write the failing test**

In `backend/tests/test_api_pre_partita.py`, add at the top after the imports:

```python
def test_get_tactic_xp_empty(client):
    resp = client.get("/api/pre-partita/tactic-xp")
    assert resp.status_code == 200
    assert "tactic_xp" in resp.json()
    assert isinstance(resp.json()["tactic_xp"], dict)


def test_put_tactic_xp(client):
    resp = client.put("/api/pre-partita/tactic-xp", json={
        "tactic_name": "Pressing", "xp_level": 12,
    })
    assert resp.status_code == 200
    resp2 = client.get("/api/pre-partita/tactic-xp")
    assert resp2.json()["tactic_xp"]["Pressing"] == 12


def test_put_tactic_xp_invalid_name(client):
    resp = client.put("/api/pre-partita/tactic-xp", json={
        "tactic_name": "FakeRobotTactic", "xp_level": 5,
    })
    assert resp.status_code == 422
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && pytest tests/test_api_pre_partita.py::test_get_tactic_xp_empty tests/test_api_pre_partita.py::test_put_tactic_xp tests/test_api_pre_partita.py::test_put_tactic_xp_invalid_name -v
```

Expected: FAIL with 404 (routes don't exist yet)

- [ ] **Step 3: Create the TacticXP model**

Create `backend/app/models/tactic_xp.py`:

```python
from datetime import datetime
from sqlalchemy import Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

VALID_TACTICS = frozenset([
    "Normal", "Pressing", "Contropiede",
    "Attacco al Centro", "Attacco sulle Fasce",
    "Tiri da Fuori", "Libertà d'Inventiva",
])


class TacticXP(Base):
    __tablename__ = "tactic_xp"

    tactic_name: Mapped[str] = mapped_column(String, primary_key=True)
    xp_level:    Mapped[int] = mapped_column(Integer, default=0)
    source:      Mapped[str] = mapped_column(String, default="manual")
    updated_at:  Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 4: Import TacticXP in main.py**

In `backend/app/main.py`, add after the FormationXP import line:

```python
from app.models.tactic_xp import TacticXP  # noqa: F401
```

The `Base.metadata.create_all(bind=engine)` call already present will create the table automatically.

- [ ] **Step 5: Add TacticXP endpoints to pre_partita.py**

In `backend/app/api/pre_partita.py`, add these imports at the top:

```python
from app.models.tactic_xp import TacticXP, VALID_TACTICS
```

Then add after the `put_formation_xp` route:

```python
@router.get("/pre-partita/tactic-xp")
def get_tactic_xp(db: Session = Depends(get_db)):
    rows = db.query(TacticXP).all()
    return {"tactic_xp": {r.tactic_name: r.xp_level for r in rows}}


class TacticXPUpdate(BaseModel):
    tactic_name: str
    xp_level: int


@router.put("/pre-partita/tactic-xp")
def put_tactic_xp(body: TacticXPUpdate, db: Session = Depends(get_db)):
    if body.tactic_name not in VALID_TACTICS:
        raise HTTPException(status_code=422, detail=f"Tattica non valida: {body.tactic_name}")
    row = db.query(TacticXP).filter_by(tactic_name=body.tactic_name).first()
    if row:
        row.xp_level = body.xp_level
        row.updated_at = datetime.utcnow()
    else:
        db.add(TacticXP(tactic_name=body.tactic_name, xp_level=body.xp_level))
    db.commit()
    return {"ok": True}
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd backend && pytest tests/test_api_pre_partita.py::test_get_tactic_xp_empty tests/test_api_pre_partita.py::test_put_tactic_xp tests/test_api_pre_partita.py::test_put_tactic_xp_invalid_name -v
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/tactic_xp.py backend/app/main.py backend/app/api/pre_partita.py backend/tests/test_api_pre_partita.py
git commit -m "feat: add TacticXP model + GET/PUT /api/pre-partita/tactic-xp endpoints"
```

---

## Task 2: Test Fixtures for Matchdetails

**Files:**
- Create: `backend/tests/fixtures/matchdetails_tarallos_1.xml`
- Create: `backend/tests/fixtures/matchdetails_tarallos_2.xml`

These fixtures represent two league matches of "i tarallos" (team ID 237132). Fixture 1: tarallos at home. Fixture 2: tarallos away.

- [ ] **Step 1: Create matchdetails_tarallos_1.xml** (i tarallos HOME, 5–2 vs real volley)

```xml
<?xml version="1.0" encoding="utf-8"?>
<HattrickData>
  <Match>
    <MatchID>762443878</MatchID>
    <MatchType>1</MatchType>
    <MatchDate>2026-06-06 12:00:00</MatchDate>
    <HomeGoals>5</HomeGoals>
    <AwayGoals>2</AwayGoals>
    <HomeTeam>
      <HomeTeamID>237132</HomeTeamID>
      <HomeTeamName>i tarallos</HomeTeamName>
      <Formation>2-5-3</Formation>
      <TacticType>3</TacticType>
      <TacticSkill>18</TacticSkill>
      <RatingMidfield>30</RatingMidfield>
      <RatingRightDef>24</RatingRightDef>
      <RatingMidDef>46</RatingMidDef>
      <RatingLeftDef>25</RatingLeftDef>
      <RatingRightAtt>25</RatingRightAtt>
      <RatingMidAtt>47</RatingMidAtt>
      <RatingLeftAtt>28</RatingLeftAtt>
    </HomeTeam>
    <AwayTeam>
      <AwayTeamID>728316</AwayTeamID>
      <AwayTeamName>real volley f.c.</AwayTeamName>
      <Formation>3-5-2</Formation>
      <TacticType>0</TacticType>
      <TacticSkill>0</TacticSkill>
      <RatingMidfield>28</RatingMidfield>
      <RatingRightDef>46</RatingRightDef>
      <RatingMidDef>42</RatingMidDef>
      <RatingLeftDef>44</RatingLeftDef>
      <RatingRightAtt>47</RatingRightAtt>
      <RatingMidAtt>55</RatingMidAtt>
      <RatingLeftAtt>52</RatingLeftAtt>
    </AwayTeam>
  </Match>
</HattrickData>
```

- [ ] **Step 2: Create matchdetails_tarallos_2.xml** (i tarallos AWAY, 3–1 vs Pace-Mela)

```xml
<?xml version="1.0" encoding="utf-8"?>
<HattrickData>
  <Match>
    <MatchID>762000001</MatchID>
    <MatchType>1</MatchType>
    <MatchDate>2026-05-30 12:00:00</MatchDate>
    <HomeGoals>1</HomeGoals>
    <AwayGoals>3</AwayGoals>
    <HomeTeam>
      <HomeTeamID>547412</HomeTeamID>
      <HomeTeamName>Pace-Mela</HomeTeamName>
      <Formation>4-4-2</Formation>
      <TacticType>0</TacticType>
      <TacticSkill>0</TacticSkill>
      <RatingMidfield>22</RatingMidfield>
      <RatingRightDef>28</RatingRightDef>
      <RatingMidDef>30</RatingMidDef>
      <RatingLeftDef>27</RatingLeftDef>
      <RatingRightAtt>24</RatingRightAtt>
      <RatingMidAtt>26</RatingMidAtt>
      <RatingLeftAtt>23</RatingLeftAtt>
    </HomeTeam>
    <AwayTeam>
      <AwayTeamID>237132</AwayTeamID>
      <AwayTeamName>i tarallos</AwayTeamName>
      <Formation>2-5-3</Formation>
      <TacticType>3</TacticType>
      <TacticSkill>16</TacticSkill>
      <RatingMidfield>25</RatingMidfield>
      <RatingRightDef>18</RatingRightDef>
      <RatingMidDef>38</RatingMidDef>
      <RatingLeftDef>19</RatingLeftDef>
      <RatingRightAtt>20</RatingRightAtt>
      <RatingMidAtt>40</RatingMidAtt>
      <RatingLeftAtt>22</RatingLeftAtt>
    </AwayTeam>
  </Match>
</HattrickData>
```

- [ ] **Step 3: Commit**

```bash
git add backend/tests/fixtures/matchdetails_tarallos_1.xml backend/tests/fixtures/matchdetails_tarallos_2.xml
git commit -m "test: add matchdetails fixture XMLs for i tarallos (home + away)"
```

---

## Task 3: Matchdetails Parser — Base Parsing

**Files:**
- Modify: `backend/app/hrf/opponent_parser.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_opponent_matchdetails.py`:

```python
from pathlib import Path
from app.hrf.opponent_parser import (
    parse_both_teams, detect_opponent_team_id,
    TeamMatchData,
)

FIXTURES = Path(__file__).parent / "fixtures"
XML1 = (FIXTURES / "matchdetails_tarallos_1.xml").read_text()
XML2 = (FIXTURES / "matchdetails_tarallos_2.xml").read_text()


def test_parse_both_teams_home_team():
    home, away = parse_both_teams(XML1)
    assert home.team_id == 237132
    assert home.team_name == "i tarallos"
    assert home.is_home is True
    assert home.formation == "2-5-3"
    assert home.tactic_type == 3
    assert home.tactic_skill == 18
    assert home.line_ratings["mid_def"] == 46
    assert home.line_ratings["right_def"] == 24
    assert home.goals_for == 5
    assert home.goals_against == 2
    assert home.match_date == "2026-06-06 12:00:00"


def test_parse_both_teams_away_team():
    home, away = parse_both_teams(XML1)
    assert away.team_id == 728316
    assert away.team_name == "real volley f.c."
    assert away.is_home is False
    assert away.goals_for == 2
    assert away.goals_against == 5


def test_parse_both_teams_wrong_match_type():
    wrong_type_xml = XML1.replace("<MatchType>1</MatchType>", "<MatchType>2</MatchType>")
    import pytest
    with pytest.raises(ValueError, match="MatchType=1"):
        parse_both_teams(wrong_type_xml)


def test_detect_opponent_team_id_single_xml():
    # With only one XML, defaults to home team
    team_id = detect_opponent_team_id([XML1])
    # i tarallos is home in XML1
    assert team_id == 237132


def test_detect_opponent_team_id_two_xmls():
    # i tarallos (237132) appears in both XMLs — detected automatically
    team_id = detect_opponent_team_id([XML1, XML2])
    assert team_id == 237132
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && pytest tests/test_opponent_matchdetails.py -v
```

Expected: FAIL — `parse_both_teams` not defined

- [ ] **Step 3: Add TeamMatchData dataclass and parse_both_teams to opponent_parser.py**

In `backend/app/hrf/opponent_parser.py`, add after the existing `MatchResult` dataclass:

```python
@dataclass
class TeamMatchData:
    team_id:       int
    team_name:     str
    is_home:       bool
    formation:     str
    tactic_type:   int
    tactic_skill:  int
    line_ratings:  dict   # keys: midfield, mid_def, mid_att, right_def, left_def, right_att, left_att
    goals_for:     int
    goals_against: int
    match_date:    str
```

Then add the functions:

```python
def parse_both_teams(xml_str: str) -> tuple[TeamMatchData, TeamMatchData]:
    """Extract home and away TeamMatchData from a matchdetails XML. Only MatchType=1 accepted."""
    root = etree.fromstring(xml_str.encode(), _PARSER)
    match = root.find("Match")
    if match is None:
        raise ValueError("Struttura XML non valida: elemento Match mancante")
    match_type = match.findtext("MatchType", "")
    if match_type != "1":
        raise ValueError(f"Solo partite di campionato (MatchType=1). Ricevuto: {match_type}")
    match_date = match.findtext("MatchDate", "")
    home_goals = _int_text(match, "HomeGoals")
    away_goals = _int_text(match, "AwayGoals")
    home_el = match.find("HomeTeam")
    away_el = match.find("AwayTeam")
    if home_el is None or away_el is None:
        raise ValueError("Struttura XML non valida: HomeTeam o AwayTeam mancante")

    def _ratings(el) -> dict:
        return {
            "midfield":  _int_text(el, "RatingMidfield"),
            "mid_def":   _int_text(el, "RatingMidDef"),
            "mid_att":   _int_text(el, "RatingMidAtt"),
            "right_def": _int_text(el, "RatingRightDef"),
            "left_def":  _int_text(el, "RatingLeftDef"),
            "right_att": _int_text(el, "RatingRightAtt"),
            "left_att":  _int_text(el, "RatingLeftAtt"),
        }

    home = TeamMatchData(
        team_id=_int_text(home_el, "HomeTeamID"),
        team_name=home_el.findtext("HomeTeamName", ""),
        is_home=True,
        formation=home_el.findtext("Formation", ""),
        tactic_type=_int_text(home_el, "TacticType"),
        tactic_skill=_int_text(home_el, "TacticSkill"),
        line_ratings=_ratings(home_el),
        goals_for=home_goals,
        goals_against=away_goals,
        match_date=match_date,
    )
    away = TeamMatchData(
        team_id=_int_text(away_el, "AwayTeamID"),
        team_name=away_el.findtext("AwayTeamName", ""),
        is_home=False,
        formation=away_el.findtext("Formation", ""),
        tactic_type=_int_text(away_el, "TacticType"),
        tactic_skill=_int_text(away_el, "TacticSkill"),
        line_ratings=_ratings(away_el),
        goals_for=away_goals,
        goals_against=home_goals,
        match_date=match_date,
    )
    return home, away


def detect_opponent_team_id(xmls: list[str]) -> int:
    """Find the team ID that appears in all provided XMLs.
    With a single XML, defaults to the home team (first XML's home team)."""
    all_id_sets = []
    for xml in xmls:
        home, away = parse_both_teams(xml)
        all_id_sets.append({home.team_id, away.team_id})
    common = all_id_sets[0]
    for ids in all_id_sets[1:]:
        common = common & ids
    if len(common) == 1:
        return common.pop()
    home, _ = parse_both_teams(xmls[0])
    return home.team_id
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && pytest tests/test_opponent_matchdetails.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/hrf/opponent_parser.py backend/tests/test_opponent_matchdetails.py
git commit -m "feat: add parse_both_teams + detect_opponent_team_id to opponent_parser"
```

---

## Task 4: Matchdetails Parser — Opponent Extraction + Averaging

**Files:**
- Modify: `backend/app/hrf/opponent_parser.py`
- Modify: `backend/tests/test_opponent_matchdetails.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_opponent_matchdetails.py`:

```python
from app.hrf.opponent_parser import (
    parse_both_teams, detect_opponent_team_id,
    parse_opponent_matchdetails, average_opponent_profiles,
    OppMatchData, OppProfile,
)


def test_parse_opponent_matchdetails_home():
    opp = parse_opponent_matchdetails(XML1, opponent_team_id=237132)
    assert isinstance(opp, OppMatchData)
    assert opp.team_id == 237132
    assert opp.was_home is True
    assert opp.tactic_type == 3
    assert opp.line_ratings["mid_def"] == 46


def test_parse_opponent_matchdetails_away():
    opp = parse_opponent_matchdetails(XML2, opponent_team_id=237132)
    assert opp.was_home is False
    assert opp.line_ratings["mid_def"] == 38
    assert opp.goals_for == 3
    assert opp.goals_against == 1


def test_parse_opponent_matchdetails_wrong_team():
    import pytest
    with pytest.raises(ValueError, match="non trovato"):
        parse_opponent_matchdetails(XML1, opponent_team_id=99999)


def test_average_opponent_profiles_single_match():
    opp1 = parse_opponent_matchdetails(XML1, 237132)
    profile = average_opponent_profiles([opp1])
    assert isinstance(profile, OppProfile)
    assert profile.team_id == 237132
    assert profile.matches_used == 1
    # Home match normalized: 46 * 0.88 = 40.48
    assert abs(profile.avg_line_ratings["mid_def"] - 40.48) < 0.1
    assert profile.dominant_tactic == 3
    assert profile.typical_formation == "2-5-3"
    assert len(profile.recent_results) == 1
    assert profile.recent_results[0]["result"] == "W"


def test_average_opponent_profiles_two_matches():
    opp1 = parse_opponent_matchdetails(XML1, 237132)
    opp2 = parse_opponent_matchdetails(XML2, 237132)
    profile = average_opponent_profiles([opp1, opp2])
    assert profile.matches_used == 2
    # Match 1 (home, weight 3): mid_def 46 * 0.88 = 40.48
    # Match 2 (away, weight 2): mid_def 38 * 1.0 = 38.0
    # Weighted avg: (40.48*3 + 38*2) / 5 = 39.488
    assert abs(profile.avg_line_ratings["mid_def"] - 39.488) < 0.1
    assert profile.dominant_tactic == 3  # both matches tactic_type==3


def test_average_opponent_profiles_detect_wing_weakness():
    opp1 = parse_opponent_matchdetails(XML1, 237132)
    opp2 = parse_opponent_matchdetails(XML2, 237132)
    profile = average_opponent_profiles([opp1, opp2])
    # wing_avg = (right_def + left_def)/2
    # right_def avg: (24*0.88*3 + 18*2)/5 = (63.36+36)/5 = 19.872
    # left_def avg:  (25*0.88*3 + 19*2)/5 = (66+38)/5 = 20.8
    # wing_avg = (19.872+20.8)/2 = 20.336
    # mid_def = 39.488
    # 20.336 < 39.488 * 0.70 = 27.64 → wing weakness detected
    wing_avg = (profile.avg_line_ratings["right_def"] + profile.avg_line_ratings["left_def"]) / 2
    assert wing_avg < profile.avg_line_ratings["mid_def"] * 0.70
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && pytest tests/test_opponent_matchdetails.py -k "opp_matchdetails or average" -v
```

Expected: FAIL — `OppMatchData`, `parse_opponent_matchdetails`, `average_opponent_profiles`, `OppProfile` not defined

- [ ] **Step 3: Add OppMatchData, OppProfile, parse_opponent_matchdetails, average_opponent_profiles**

In `backend/app/hrf/opponent_parser.py`, add after `TeamMatchData`:

```python
_HOME_NORMALIZE = 0.88  # deflate ratings from matches where opponent played at home


@dataclass
class OppMatchData:
    team_id:       int
    team_name:     str
    was_home:      bool
    formation:     str
    tactic_type:   int
    tactic_skill:  int
    line_ratings:  dict
    goals_for:     int
    goals_against: int
    match_date:    str


@dataclass
class OppProfile:
    team_id:          int
    team_name:        str
    avg_line_ratings: dict
    dominant_tactic:  int | None
    avg_tactic_skill: float
    typical_formation: str
    recent_results:   list
    matches_used:     int
```

Then add the functions:

```python
def parse_opponent_matchdetails(xml_str: str, opponent_team_id: int) -> OppMatchData:
    """Extract opponent data from a matchdetails XML."""
    home, away = parse_both_teams(xml_str)
    if home.team_id == opponent_team_id:
        t = home
    elif away.team_id == opponent_team_id:
        t = away
    else:
        raise ValueError(f"Team {opponent_team_id} non trovato nel match XML")
    return OppMatchData(
        team_id=t.team_id,
        team_name=t.team_name,
        was_home=t.is_home,
        formation=t.formation,
        tactic_type=t.tactic_type,
        tactic_skill=t.tactic_skill,
        line_ratings=t.line_ratings,
        goals_for=t.goals_for,
        goals_against=t.goals_against,
        match_date=t.match_date,
    )


def average_opponent_profiles(matches: list[OppMatchData]) -> OppProfile:
    """Weighted average of opponent match data. Tab 1 = weight 3, tab 2 = 2, tab 3 = 1.
    Normalizes home matches by deflating ratings by _HOME_NORMALIZE."""
    weights = [3, 2, 1][: len(matches)]
    total_weight = sum(weights)

    # Normalize: deflate ratings from matches where opponent played at home
    normalized = []
    for m in matches:
        factor = _HOME_NORMALIZE if m.was_home else 1.0
        normalized.append({k: v * factor for k, v in m.line_ratings.items()})

    keys = ["midfield", "mid_def", "mid_att", "right_def", "left_def", "right_att", "left_att"]
    avg_ratings = {
        k: sum(normalized[i][k] * weights[i] for i in range(len(matches))) / total_weight
        for k in keys
    }

    # Dominant tactic: appears in ≥2 matches, else first match's tactic
    from collections import Counter
    tactics = [m.tactic_type for m in matches]
    if len(matches) >= 2:
        counts = Counter(tactics)
        mc, count = counts.most_common(1)[0]
        dominant = mc if count >= 2 else None
    else:
        dominant = tactics[0]

    avg_skill = sum(m.tactic_skill * weights[i] for i, m in enumerate(matches)) / total_weight
    typical_formation = Counter(m.formation for m in matches).most_common(1)[0][0]

    recent_results = []
    for m in matches:
        gf, ga = m.goals_for, m.goals_against
        result = "W" if gf > ga else "D" if gf == ga else "L"
        recent_results.append({"result": result, "goals_for": gf, "goals_against": ga})

    return OppProfile(
        team_id=matches[0].team_id,
        team_name=matches[0].team_name,
        avg_line_ratings=avg_ratings,
        dominant_tactic=dominant,
        avg_tactic_skill=avg_skill,
        typical_formation=typical_formation,
        recent_results=recent_results,
        matches_used=len(matches),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && pytest tests/test_opponent_matchdetails.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/hrf/opponent_parser.py backend/tests/test_opponent_matchdetails.py
git commit -m "feat: add OppMatchData/OppProfile + parse_opponent_matchdetails + average_opponent_profiles"
```

---

## Task 5: strategy.py — Detection Helpers + optimize_formation home_mod

**Files:**
- Modify: `backend/app/hrf/strategy.py`

TacticType reference: 0=Normal, 1=Pressing, 2=Contropiede, 3=Attacco al Centro, 4=Attacco sulle Fasce, 5=Tiri da Fuori, 6=Libertà d'Inventiva.

Scale note: `_chpp_to_app_scale()` converts CHPP hat-point ratings (range ~15–60) to app internal scale (~4–10) using factor 6.0. This keeps both sides of `optimize_formation()`'s scoring on the same coordinate system.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_strategy_detection.py`:

```python
import pytest
from app.hrf.strategy import (
    apply_home_away_modifier, detect_wing_weakness,
    detect_pressing, detect_center_attack, _chpp_to_app_scale,
    optimize_formation,
)
from app.hrf.opponent_parser import OppProfile

_SAMPLE_CHPP = {
    "midfield":  30,
    "mid_def":   40,
    "mid_att":   45,
    "right_def": 20,
    "left_def":  21,
    "right_att": 22,
    "left_att":  23,
}


def _make_profile(dominant_tactic):
    return OppProfile(
        team_id=1, team_name="Test",
        avg_line_ratings=_SAMPLE_CHPP,
        dominant_tactic=dominant_tactic,
        avg_tactic_skill=10.0,
        typical_formation="4-4-2",
        recent_results=[],
        matches_used=1,
    )


def test_chpp_to_app_scale_proportions():
    app = _chpp_to_app_scale(_SAMPLE_CHPP)
    assert set(app.keys()) == {"goalkeeper", "defense", "midfield", "attack"}
    # midfield: 30/6 = 5.0
    assert abs(app["midfield"] - 5.0) < 0.01
    # defense: (40+20+21)/3/6 = 4.5
    assert abs(app["defense"] - (40 + 20 + 21) / 3 / 6) < 0.01


def test_apply_home_advantage_is_home():
    # When is_home=True, opponent plays away → multiply by 0.88
    result = apply_home_away_modifier(_SAMPLE_CHPP, is_home=True)
    assert abs(result["mid_def"] - 40 * 0.88) < 0.01


def test_apply_home_advantage_is_away():
    # When is_home=False, opponent plays at home → multiply by 1.06
    result = apply_home_away_modifier(_SAMPLE_CHPP, is_home=False)
    assert abs(result["mid_def"] - 40 * 1.06) < 0.01


def test_detect_wing_weakness_true():
    # right_def=20, left_def=21 → wing_avg=20.5; mid_def=40 → threshold=28
    assert detect_wing_weakness(_SAMPLE_CHPP) is True


def test_detect_wing_weakness_false():
    balanced = {**_SAMPLE_CHPP, "right_def": 35, "left_def": 35}
    assert detect_wing_weakness(balanced) is False


def test_detect_pressing_true():
    profile = _make_profile(dominant_tactic=1)
    assert detect_pressing(profile) is True


def test_detect_pressing_false():
    profile = _make_profile(dominant_tactic=3)
    assert detect_pressing(profile) is False


def test_detect_center_attack_true():
    profile = _make_profile(dominant_tactic=3)
    assert detect_center_attack(profile) is True


def test_detect_center_attack_false():
    profile = _make_profile(dominant_tactic=1)
    assert detect_center_attack(profile) is False


def test_optimize_formation_home_mod_raises_rating():
    """home_mod=1.06 should produce a higher score than home_mod=1.0 for the same inputs."""
    from app.models.player import Player
    players = [
        Player(id=i, first_name="P", last_name=str(i), goalkeeper=10 if i == 1 else 0,
               defending=10, playmaking=8, scoring=7, passing=6, winger=8, stamina=7)
        for i in range(1, 12)
    ]
    _, data_neutral = optimize_formation(players, {}, home_mod=1.0)
    _, data_home = optimize_formation(players, {}, home_mod=1.06)
    neutral_total = sum(data_neutral["modified_ratings"].values())
    home_total = sum(data_home["modified_ratings"].values())
    assert home_total > neutral_total
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && pytest tests/test_strategy_detection.py -v
```

Expected: FAIL — `apply_home_away_modifier`, `detect_wing_weakness`, `detect_pressing`, `detect_center_attack`, `_chpp_to_app_scale` not defined

- [ ] **Step 3: Add functions to strategy.py**

In `backend/app/hrf/strategy.py`, add after the `TACTIC_NAMES` list:

```python
_HOME_ATTACK  = 1.06   # our rating boost when playing at home
_AWAY_PENALTY = 0.88   # opponent rating deflate when they play at our ground


def _chpp_to_app_scale(chpp_ratings: dict) -> dict:
    """Convert CHPP 7-key hat-point ratings to app 4-key scale (÷6 approximation)."""
    _S = 6.0
    return {
        "goalkeeper": chpp_ratings.get("mid_def", 0) / _S,
        "defense":    (chpp_ratings.get("mid_def", 0) +
                       chpp_ratings.get("right_def", 0) +
                       chpp_ratings.get("left_def", 0)) / 3 / _S,
        "midfield":   chpp_ratings.get("midfield", 0) / _S,
        "attack":     (chpp_ratings.get("mid_att", 0) +
                       chpp_ratings.get("right_att", 0) +
                       chpp_ratings.get("left_att", 0)) / 3 / _S,
    }


def apply_home_away_modifier(chpp_ratings: dict, is_home: bool) -> dict:
    """Adjust opponent CHPP ratings for the venue context of our match.
    is_home=True: opponent plays away at our ground → deflate by 0.88.
    is_home=False: opponent plays at their home → inflate by 1.06."""
    factor = _AWAY_PENALTY if is_home else _HOME_ATTACK
    return {k: v * factor for k, v in chpp_ratings.items()}


def detect_wing_weakness(chpp_ratings: dict) -> bool:
    """True if opponent's wing defense is <70% of their central defense."""
    wing_avg = (chpp_ratings.get("right_def", 0) + chpp_ratings.get("left_def", 0)) / 2
    mid_def = chpp_ratings.get("mid_def", 0)
    return mid_def > 0 and wing_avg < mid_def * 0.70


def detect_pressing(opp_profile) -> bool:
    """TacticType 1 = Pressing."""
    return opp_profile.dominant_tactic == 1


def detect_center_attack(opp_profile) -> bool:
    """TacticType 3 = Attacco al Centro."""
    return opp_profile.dominant_tactic == 3
```

Now extend `optimize_formation()` to accept `home_mod`. Change the signature from:

```python
def optimize_formation(
    players,
    opp_line_ratings: dict,
    spirit: int = 10,
    confidence: int = 10,
    formation_xp: dict[str, int] | None = None,
) -> tuple[str, dict]:
```

to:

```python
def optimize_formation(
    players,
    opp_line_ratings: dict,
    spirit: int = 10,
    confidence: int = 10,
    formation_xp: dict[str, int] | None = None,
    home_mod: float = 1.0,
) -> tuple[str, dict]:
```

And in the `modified` dict computation inside `optimize_formation()`, multiply all four lines by `home_mod`:

```python
        modified = {
            "goalkeeper": lr["goalkeeper"] * xp_mod * form_mod * home_mod,
            "defense":    lr["defense"]    * xp_mod * form_mod * home_mod,
            "midfield":   lr["midfield"]   * xp_mod * form_mod * spirit_mod * home_mod,
            "attack":     lr["attack"]     * xp_mod * form_mod * confidence_mod * home_mod,
        }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && pytest tests/test_strategy_detection.py -v
```

Expected: all PASS

- [ ] **Step 5: Run full test suite to confirm no regressions**

```bash
cd backend && pytest -v
```

Expected: all existing tests still PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/hrf/strategy.py backend/tests/test_strategy_detection.py
git commit -m "feat: add _chpp_to_app_scale, apply_home_away_modifier, detect_* functions; extend optimize_formation with home_mod"
```

---

## Task 6: strategy.py — recommend_tactic

**Files:**
- Modify: `backend/app/hrf/strategy.py`
- Modify: `backend/tests/test_strategy_detection.py`

`recommend_tactic()` wraps `rank_tactics()` and applies opponent-aware score bonuses/maluses based on detection results.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_strategy_detection.py`:

```python
from app.hrf.strategy import recommend_tactic
from app.models.player import Player


def _make_lineup():
    """11 players in a simple 4-4-2 lineup for tactic tests."""
    players = [
        Player(id=1,  goalkeeper=11, stamina=7),
        Player(id=2,  defending=10, winger=8, stamina=7),
        Player(id=3,  defending=10, winger=8, stamina=7),
        Player(id=4,  defending=9,  stamina=7),
        Player(id=5,  defending=9,  stamina=7),
        Player(id=6,  playmaking=10, passing=8, stamina=7),
        Player(id=7,  playmaking=10, passing=8, stamina=7),
        Player(id=8,  winger=11, playmaking=7, stamina=7),
        Player(id=9,  winger=11, playmaking=7, stamina=7),
        Player(id=10, scoring=11, passing=7, stamina=7),
        Player(id=11, scoring=10, passing=7, stamina=7),
    ]
    for p in players:
        p.first_name = "P"
        p.last_name = str(p.id)
        if not hasattr(p, "form"): p.form = 7
    from app.hrf.strategy import _build_lineup
    data = _build_lineup(players, "4-4-2")
    return data["lineup"]


def test_recommend_tactic_returns_structure():
    lineup = _make_lineup()
    profile = _make_profile(dominant_tactic=None)
    result = recommend_tactic(lineup, profile, _SAMPLE_CHPP, {})
    assert "recommended" in result
    assert "ranking" in result
    assert len(result["ranking"]) == 7


def test_recommend_tactic_wing_weakness_boosts_fasce():
    lineup = _make_lineup()
    # _SAMPLE_CHPP has wing weakness (right_def=20, left_def=21, mid_def=40)
    profile = _make_profile(dominant_tactic=None)
    result = recommend_tactic(lineup, profile, _SAMPLE_CHPP, {})
    fasce = next(r for r in result["ranking"] if r["name"] == "Attacco sulle Fasce")
    normal = next(r for r in result["ranking"] if r["name"] == "Normal")
    # Attacco sulle Fasce should rank higher than it would without the bonus
    fasce_idx = result["ranking"].index(fasce)
    assert fasce_idx < 4  # should be in top 4 when wing weakness detected


def test_recommend_tactic_center_attack_boosts_contropiede():
    lineup = _make_lineup()
    # dominant_tactic=3 (Attacco al Centro) → Contropiede gets bonus, Attacco al Centro gets malus
    profile = _make_profile(dominant_tactic=3)
    result = recommend_tactic(lineup, profile, _SAMPLE_CHPP, {})
    ctrop = next(r for r in result["ranking"] if r["name"] == "Contropiede")
    centro = next(r for r in result["ranking"] if r["name"] == "Attacco al Centro")
    ctrop_idx = result["ranking"].index(ctrop)
    centro_idx = result["ranking"].index(centro)
    assert ctrop_idx < centro_idx
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && pytest tests/test_strategy_detection.py -k "recommend_tactic" -v
```

Expected: FAIL — `recommend_tactic` not defined

- [ ] **Step 3: Add recommend_tactic to strategy.py**

In `backend/app/hrf/strategy.py`, add after `rank_tactics()`:

```python
def recommend_tactic(
    lineup: list[dict],
    opp_profile,
    opp_chpp_ratings: dict,
    my_modified_ratings: dict,
) -> dict:
    """Extends rank_tactics() with opponent-aware bonuses/maluses from CHPP analysis.
    Returns dict with 'recommended' (str) and 'ranking' (sorted list)."""
    app_opp = _chpp_to_app_scale(opp_chpp_ratings)
    ranking = rank_tactics(lineup, app_opp, my_modified_ratings)

    wing_weak    = detect_wing_weakness(opp_chpp_ratings)
    center_atk   = detect_center_attack(opp_profile)
    opp_pressing = detect_pressing(opp_profile)

    for r in ranking:
        if r["name"] == "Attacco sulle Fasce" and wing_weak:
            r["score"] += 20.0
            r["explanation"] += " Bonus: avversario debole sulle fasce (+20)."
        if r["name"] == "Attacco al Centro" and center_atk:
            r["score"] -= 10.0
            r["explanation"] += " Malus: avversario forte al centro (-10)."
        if r["name"] == "Contropiede" and center_atk:
            r["score"] += 10.0
            r["explanation"] += " Bonus: Contropiede efficace contro Attacco al Centro (+10)."
        if r["name"] == "Pressing" and opp_pressing:
            r["score"] -= 5.0
            r["explanation"] += " Malus: avversario abituato al Pressing (-5)."

    ranking.sort(key=lambda x: x["score"], reverse=True)
    return {"recommended": ranking[0]["name"], "ranking": ranking}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && pytest tests/test_strategy_detection.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/hrf/strategy.py backend/tests/test_strategy_detection.py
git commit -m "feat: add recommend_tactic with opponent-aware bonuses to strategy.py"
```

---

## Task 7: strategy.py — generate_sub_plan

**Files:**
- Modify: `backend/app/hrf/strategy.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_strategy_sub_plan.py`:

```python
from app.hrf.strategy import generate_sub_plan, SubEntry, _stamina_to_minute
from app.models.player import Player


def _make_starter(pid, role_key, stamina, **skills):
    p = Player(id=pid, first_name="P", last_name=str(pid), stamina=stamina)
    p.form = 7
    for k, v in skills.items():
        setattr(p, k, v)
    return p


def test_stamina_to_minute():
    assert _stamina_to_minute(5) == 57
    assert _stamina_to_minute(6) == 69
    assert _stamina_to_minute(7) == 81
    # Clamp to [55, 85]
    assert _stamina_to_minute(1) == 55
    assert _stamina_to_minute(9) == 85


def test_sub_plan_skips_high_stamina():
    from app.hrf.strategy import _build_lineup
    players = [
        Player(id=1, goalkeeper=11, stamina=8),
        *[Player(id=i, defending=10, playmaking=8, winger=7, scoring=7, passing=7, stamina=8)
          for i in range(2, 12)],
    ]
    for p in players: p.form = 7; p.first_name = "P"; p.last_name = str(p.id)
    data = _build_lineup(players, "4-4-2")
    bench = []
    plan = generate_sub_plan(data["lineup"], bench)
    assert plan == []  # stamina=8 for all → no subs scheduled


def test_sub_plan_schedules_low_stamina_player():
    from app.hrf.strategy import _build_lineup
    starters = [
        Player(id=1, goalkeeper=11, stamina=8),
        Player(id=2, playmaking=12, passing=9, defending=7, scoring=5, winger=5, stamina=5),
        *[Player(id=i, defending=10, playmaking=8, winger=7, scoring=6, passing=7, stamina=8)
          for i in range(3, 12)],
    ]
    for p in starters: p.form = 7; p.first_name = "P"; p.last_name = str(p.id)
    data = _build_lineup(starters, "4-4-2")
    bench_player = Player(id=20, playmaking=10, passing=8, defending=6, scoring=5, winger=5, stamina=8)
    bench_player.form = 7; bench_player.first_name = "Sub"; bench_player.last_name = "One"
    plan = generate_sub_plan(data["lineup"], [bench_player])
    assert len(plan) == 1
    assert plan[0].out_stamina == 5
    assert plan[0].minute == 57  # stamina 5 → 5*12-3=57
    assert plan[0].in_id == 20


def test_sub_plan_excludes_goalkeeper_from_bench():
    from app.hrf.strategy import _build_lineup
    starters = [
        Player(id=1, goalkeeper=11, stamina=8),
        Player(id=2, playmaking=12, passing=9, defending=7, scoring=5, winger=5, stamina=5),
        *[Player(id=i, defending=10, playmaking=8, winger=7, scoring=6, passing=7, stamina=8)
          for i in range(3, 12)],
    ]
    for p in starters: p.form = 7; p.first_name = "P"; p.last_name = str(p.id)
    data = _build_lineup(starters, "4-4-2")
    # Only a goalkeeper on bench — should be excluded
    gk_bench = Player(id=12, goalkeeper=9, stamina=8)
    gk_bench.form = 7; gk_bench.first_name = "GK"; gk_bench.last_name = "Reserve"
    plan = generate_sub_plan(data["lineup"], [gk_bench])
    assert plan == []  # no valid outfield sub available
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && pytest tests/test_strategy_sub_plan.py -v
```

Expected: FAIL — `generate_sub_plan`, `SubEntry`, `_stamina_to_minute` not defined

- [ ] **Step 3: Add generate_sub_plan to strategy.py**

In `backend/app/hrf/strategy.py`, add after `recommend_tactic()`:

```python
from dataclasses import dataclass as _dc


@_dc
class SubEntry:
    minute:     int
    out_name:   str
    out_id:     int
    out_stamina: int
    in_name:    str
    in_id:      int
    reason:     str


def _stamina_to_minute(stamina: int) -> int:
    """Estimate the minute when stamina degradation becomes substitution-worthy."""
    return max(55, min(85, stamina * 12 - 3))


def generate_sub_plan(lineup: list[dict], bench: list) -> list[SubEntry]:
    """Schedule up to 3 substitutions for starters with stamina ≤ 7.
    Bench goalkeepers (goalkeeper skill > 8) are excluded from outfield sub candidates."""
    starters_at_risk = sorted(
        [e for e in lineup if e["line"] != "goalkeeper"
         and getattr(e["player"], "stamina", 10) <= 7],
        key=lambda e: getattr(e["player"], "stamina", 10),
    )[:3]

    non_gk_bench = [p for p in bench if getattr(p, "goalkeeper", 0) <= 8]

    plan: list[SubEntry] = []
    used: set[int] = set()

    for entry in starters_at_risk:
        p_out = entry["player"]
        stamina = getattr(p_out, "stamina", 10)
        minute = _stamina_to_minute(stamina)
        candidates = [b for b in non_gk_bench if b.id not in used]
        if not candidates:
            break
        best_in = max(candidates, key=lambda b: role_rating(b, entry["role"]))
        used.add(best_in.id)
        plan.append(SubEntry(
            minute=minute,
            out_name=f"{p_out.first_name} {p_out.last_name}",
            out_id=p_out.id,
            out_stamina=stamina,
            in_name=f"{best_in.first_name} {best_in.last_name}",
            in_id=best_in.id,
            reason=f"Stamina {stamina}: calo previsto al {minute}'",
        ))

    return plan
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && pytest tests/test_strategy_sub_plan.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/hrf/strategy.py backend/tests/test_strategy_sub_plan.py
git commit -m "feat: add SubEntry dataclass + generate_sub_plan to strategy.py"
```

---

## Task 8: strategy.py — generate_attitude_orders

**Files:**
- Modify: `backend/app/hrf/strategy.py`

Attitude order minutes are derived from the substitution plan, not hardcoded. `_snap_to_hattrick_minute` rounds to nearest 5 and clamps to [60, 85].

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_strategy_attitude.py`:

```python
from app.hrf.strategy import (
    generate_attitude_orders, AttitudeOrder, _snap_to_hattrick_minute, SubEntry,
)


def _make_sub(minute):
    return SubEntry(minute=minute, out_name="A B", out_id=1, out_stamina=5,
                    in_name="C D", in_id=10, reason="test")


def test_snap_clamps_below_60():
    assert _snap_to_hattrick_minute(40) == 60


def test_snap_clamps_above_85():
    assert _snap_to_hattrick_minute(92) == 85


def test_snap_rounds_to_nearest_5():
    assert _snap_to_hattrick_minute(63) == 65
    assert _snap_to_hattrick_minute(67) == 65
    assert _snap_to_hattrick_minute(68) == 70


def test_generate_attitude_orders_empty_sub_plan():
    result = generate_attitude_orders([], is_home=True, spirit=10, confidence=10)
    assert result == []


def test_generate_attitude_orders_structure():
    subs = [_make_sub(57), _make_sub(69)]
    result = generate_attitude_orders(subs, is_home=True, spirit=10, confidence=10)
    assert len(result) == 3
    assert all(isinstance(o, AttitudeOrder) for o in result)
    conditions = {o.condition for o in result}
    assert conditions == {"se in svantaggio", "se in vantaggio", "pareggio"}


def test_generate_attitude_orders_minutes_derived_from_subs():
    # first_sub_min=57, last_sub_min=69
    # offensive: snap(57+2) = snap(59) = 60
    # defensive: snap(69-3) = snap(66) = 65
    # balanced:  snap((69+90)//2) = snap(79) = 80
    subs = [_make_sub(57), _make_sub(69)]
    result = generate_attitude_orders(subs, is_home=True, spirit=10, confidence=10)
    by_cond = {o.condition: o for o in result}
    assert by_cond["se in svantaggio"].minute == 60
    assert by_cond["se in vantaggio"].minute == 65
    assert by_cond["pareggio"].minute == 80


def test_generate_attitude_orders_single_sub():
    subs = [_make_sub(81)]
    # offensive: snap(81+2) = snap(83) = 85
    # defensive: snap(81-3) = snap(78) = 80
    # balanced:  snap((81+90)//2) = snap(85) = 85
    result = generate_attitude_orders(subs, is_home=False, spirit=8, confidence=12)
    assert len(result) == 3
    by_cond = {o.condition: o for o in result}
    assert by_cond["se in svantaggio"].minute == 85
    assert by_cond["se in vantaggio"].minute == 80
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && pytest tests/test_strategy_attitude.py -v
```

Expected: FAIL — `generate_attitude_orders`, `AttitudeOrder`, `_snap_to_hattrick_minute` not defined

- [ ] **Step 3: Add AttitudeOrder + generate_attitude_orders to strategy.py**

In `backend/app/hrf/strategy.py`, add after `generate_sub_plan()`:

```python
@_dc
class AttitudeOrder:
    minute:    int
    condition: str   # "se in svantaggio" | "se in vantaggio" | "pareggio"
    attitude:  str   # "Offensivo" | "Difensivo" | "Normale"
    reason:    str


def _snap_to_hattrick_minute(m: int) -> int:
    """Round to nearest 5-minute increment, clamped to [60, 85]."""
    return max(60, min(85, round(m / 5) * 5))


def generate_attitude_orders(
    sub_plan: list[SubEntry],
    is_home: bool,
    spirit: int,
    confidence: int,
) -> list[AttitudeOrder]:
    """Derive conditional attitude orders from the substitution plan.
    Returns empty list if no substitutions are planned."""
    if not sub_plan:
        return []

    first_min = sub_plan[0].minute
    last_min  = sub_plan[-1].minute
    ctx       = "in casa" if is_home else "in trasferta"

    offensive_min = _snap_to_hattrick_minute(first_min + 2)
    defensive_min = _snap_to_hattrick_minute(last_min - 3)
    balanced_min  = _snap_to_hattrick_minute((last_min + 90) // 2)

    return [
        AttitudeOrder(
            minute=offensive_min,
            condition="se in svantaggio",
            attitude="Offensivo",
            reason=f"Reagire al gol subito ({ctx}, spirito {spirit})",
        ),
        AttitudeOrder(
            minute=defensive_min,
            condition="se in vantaggio",
            attitude="Difensivo",
            reason=f"Gestire il vantaggio ({ctx})",
        ),
        AttitudeOrder(
            minute=balanced_min,
            condition="pareggio",
            attitude="Normale",
            reason=f"Mantenere l'equilibrio ({ctx}, confidenza {confidence})",
        ),
    ]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && pytest tests/test_strategy_attitude.py -v
```

Expected: all PASS

- [ ] **Step 5: Run full test suite**

```bash
cd backend && pytest -v
```

Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/hrf/strategy.py backend/tests/test_strategy_attitude.py
git commit -m "feat: add AttitudeOrder dataclass + generate_attitude_orders to strategy.py"
```

---

## Task 9: API — Update AnalyzeRequest + analyze endpoint

**Files:**
- Modify: `backend/app/api/pre_partita.py`
- Modify: `backend/tests/test_api_pre_partita.py`

This replaces `players_xml`/`matches_xml` with `matchdetails_xml_1/2/3` + `is_home`. All eight old analyze-related tests are replaced with new ones. Squad/formation_xp/tactic_xp/save/history tests are unchanged.

- [ ] **Step 1: Write the new failing tests (add alongside old tests)**

In `backend/tests/test_api_pre_partita.py`, add at the bottom:

```python
# ---------------------------------------------------------------------------
# NEW analyze endpoint tests (matchdetails-based)
# ---------------------------------------------------------------------------

def test_new_analyze_returns_complete_structure(client, db):
    _add_squad(db)
    xml1 = (FIXTURES / "matchdetails_tarallos_1.xml").read_text()
    r = client.post("/api/pre-partita/analyze", json={
        "matchdetails_xml_1": xml1,
        "is_home": False,
        "spirit": 10,
        "confidence": 10,
    })
    assert r.status_code == 200
    data = r.json()
    opp = data["opponent"]
    assert opp["team_name"] == "i tarallos"
    assert opp["team_id"] == 237132
    assert opp["typical_formation"] == "2-5-3"
    assert "chpp_ratings" in opp
    assert set(opp["chpp_ratings"].keys()) == {
        "midfield", "mid_def", "mid_att", "right_def", "left_def", "right_att", "left_att"
    }
    assert "recent_results" in opp
    assert len(opp["recent_results"]) == 1
    assert opp["recent_results"][0]["result"] == "W"
    my = data["my_team"]
    all_formations = {"4-4-2","3-5-2","4-3-3","3-4-3","5-4-1","4-5-1","5-3-2","5-2-3","5-5-0","2-5-3"}
    assert my["best_formation"] in all_formations
    assert "tactic_ranking" in data
    assert "tactic_recommendation" in data
    assert data["tactic_recommendation"]["recommended"] in [t["name"] for t in data["tactic_ranking"]]
    assert "sub_plan" in data
    assert "attitude_orders" in data
    assert "attitude" in data
    assert isinstance(data["explanation"], str) and len(data["explanation"]) > 10


def test_new_analyze_with_two_matchdetails_returns_two_results(client, db):
    _add_squad(db)
    xml1 = (FIXTURES / "matchdetails_tarallos_1.xml").read_text()
    xml2 = (FIXTURES / "matchdetails_tarallos_2.xml").read_text()
    r = client.post("/api/pre-partita/analyze", json={
        "matchdetails_xml_1": xml1,
        "matchdetails_xml_2": xml2,
        "is_home": True,
    })
    assert r.status_code == 200
    results = r.json()["opponent"]["recent_results"]
    assert len(results) == 2
    assert results[0]["result"] in ("W", "D", "L")


def test_new_analyze_is_home_false_inflates_opp_ratings(client, db):
    _add_squad(db)
    xml1 = (FIXTURES / "matchdetails_tarallos_1.xml").read_text()
    r_home = client.post("/api/pre-partita/analyze", json={
        "matchdetails_xml_1": xml1, "is_home": True,
    })
    r_away = client.post("/api/pre-partita/analyze", json={
        "matchdetails_xml_1": xml1, "is_home": False,
    })
    assert r_home.status_code == r_away.status_code == 200
    # When we're away, opponent has home advantage → their adjusted ratings should be higher
    home_mid = r_home.json()["opponent"]["chpp_ratings"]["mid_def"]
    away_mid = r_away.json()["opponent"]["chpp_ratings"]["mid_def"]
    assert away_mid > home_mid


def test_new_analyze_missing_matchdetails_returns_422(client):
    r = client.post("/api/pre-partita/analyze", json={
        "matchdetails_xml_1": "",
        "is_home": True,
    })
    assert r.status_code == 422
    assert "matchdetails_xml_1" in r.json()["detail"].lower()


def test_new_analyze_malformed_xml_returns_422(client, db):
    _add_squad(db)
    r = client.post("/api/pre-partita/analyze", json={
        "matchdetails_xml_1": "<invalid",
        "is_home": True,
    })
    assert r.status_code == 422
    assert "matchdetails_xml_1" in r.json()["detail"].lower()


def test_new_analyze_tactic_ranking_has_seven_entries(client, db):
    _add_squad(db)
    xml1 = (FIXTURES / "matchdetails_tarallos_1.xml").read_text()
    r = client.post("/api/pre-partita/analyze", json={
        "matchdetails_xml_1": xml1, "is_home": True,
    })
    assert r.status_code == 200
    assert len(r.json()["tactic_ranking"]) == 7


def test_new_save_and_history(client, db):
    _add_squad(db)
    xml1 = (FIXTURES / "matchdetails_tarallos_1.xml").read_text()
    resp = client.post("/api/pre-partita/analyze", json={
        "matchdetails_xml_1": xml1,
        "is_home": False,
        "spirit": 10,
        "confidence": 10,
    })
    assert resp.status_code == 200
    analysis = resp.json()

    save_resp = client.post("/api/pre-partita/save", json={
        "analysis": analysis,
        "my_spirit": 10,
        "my_confidence": 10,
        "my_attitude": analysis["attitude"]["attitude"],
        "match_type": "league",
    })
    assert save_resp.status_code == 200

    hist = client.get("/api/pre-partita/history")
    assert hist.status_code == 200
    assert len(hist.json()["history"]) >= 1
```

- [ ] **Step 2: Run new tests to verify they fail**

```bash
cd backend && pytest tests/test_api_pre_partita.py -k "new_analyze or new_save" -v
```

Expected: FAIL (endpoint still expects `players_xml`)

- [ ] **Step 3: Update AnalyzeRequest and analyze endpoint in pre_partita.py**

Replace the `AnalyzeRequest` class and `analyze` function in `backend/app/api/pre_partita.py`.

First, update the imports at the top:

```python
from app.hrf.opponent_parser import (
    detect_opponent_team_id, parse_opponent_matchdetails, average_opponent_profiles,
)
from app.hrf.strategy import (
    FORMATIONS, role_rating, optimize_formation, rank_tactics,
    recommend_attitude, generate_explanation, recommend_tactic,
    generate_sub_plan, generate_attitude_orders,
    apply_home_away_modifier, _chpp_to_app_scale,
)
from app.models.tactic_xp import TacticXP
```

Remove the old imports of `parse_opponent_players`, `parse_opponent_matches`.

Replace the `AnalyzeRequest` class:

```python
class AnalyzeRequest(BaseModel):
    matchdetails_xml_1: str
    matchdetails_xml_2: str = ""
    matchdetails_xml_3: str = ""
    is_home: bool = True
    match_type: str = "league"
    spirit: int = 10
    confidence: int = 10
    formation_xp: dict[str, int] = {}
    tactic_xp: dict[str, int] = {}
```

Replace the `analyze` function:

```python
@router.post("/pre-partita/analyze")
def analyze(body: AnalyzeRequest, db: Session = Depends(get_db)):
    if not body.matchdetails_xml_1.strip():
        raise HTTPException(status_code=422, detail="matchdetails_xml_1 obbligatorio")

    xmls = [x for x in [
        body.matchdetails_xml_1,
        body.matchdetails_xml_2,
        body.matchdetails_xml_3,
    ] if x.strip()]

    try:
        opponent_team_id = detect_opponent_team_id(xmls)
        opp_matches = [parse_opponent_matchdetails(xml, opponent_team_id) for xml in xmls]
        opp_profile = average_opponent_profiles(opp_matches)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"matchdetails_xml_1 non valido: {e}")

    adjusted_chpp = apply_home_away_modifier(opp_profile.avg_line_ratings, body.is_home)
    app_opp = _chpp_to_app_scale(adjusted_chpp)

    my_players = get_current_players(db)
    db_fxp = {r.formation_name: r.xp_level for r in db.query(FormationXP).all()}
    merged_fxp = {**db_fxp, **body.formation_xp}
    db_txp = {r.tactic_name: r.xp_level for r in db.query(TacticXP).all()}
    merged_txp = {**db_txp, **body.tactic_xp}

    home_mod = 1.06 if body.is_home else 1.0

    try:
        my_formation, my_data = optimize_formation(
            my_players, app_opp,
            spirit=body.spirit,
            confidence=body.confidence,
            formation_xp=merged_fxp,
            home_mod=home_mod,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Rosa locale: {e}")

    my_ratings     = my_data["line_ratings"]
    my_mod_ratings = my_data.get("modified_ratings", my_ratings)
    xp_level       = my_data.get("xp_level", 0)

    tactic_rec = recommend_tactic(my_data["lineup"], opp_profile, adjusted_chpp, my_mod_ratings)

    attitude = recommend_attitude(
        spirit=body.spirit,
        confidence=body.confidence,
        match_type=body.match_type,
        league_position=None,
        opp_position=None,
    )

    starter_ids = {e["player"].id for e in my_data["lineup"]}
    bench = [p for p in my_players
             if p.id not in starter_ids and getattr(p, "injury_days", -1) <= 0]
    sub_plan = generate_sub_plan(my_data["lineup"], bench)
    attitude_orders = generate_attitude_orders(sub_plan, body.is_home, body.spirit, body.confidence)

    explanation = generate_explanation(
        my_mod_ratings, app_opp, my_formation, tactic_rec["recommended"], attitude
    )

    xp_warning = xp_level < 8
    xp_alternative = None
    if xp_warning:
        best_alt, best_alt_xp = None, -1
        for fname in FORMATIONS:
            fxp = merged_fxp.get(fname, 0)
            if fxp >= 8 and fname != my_formation and fxp > best_alt_xp:
                best_alt_xp = fxp
                best_alt = fname
        xp_alternative = best_alt

    def fmt_lineup(lineup_data):
        by_line: dict[str, list] = {"goalkeeper": [], "defense": [], "midfield": [], "attack": []}
        for entry in lineup_data:
            p = entry["player"]
            by_line[entry["line"]].append({
                "id": p.id,
                "name": f"{p.first_name} {p.last_name}",
                "rating": round(role_rating(p, entry["role"]), 1),
            })
        return by_line

    return {
        "opponent": {
            "team_name":         opp_profile.team_name,
            "team_id":           opp_profile.team_id,
            "typical_formation": opp_profile.typical_formation,
            "dominant_tactic":   opp_profile.dominant_tactic,
            "avg_tactic_skill":  round(opp_profile.avg_tactic_skill, 1),
            "chpp_ratings":      {k: round(v, 1) for k, v in adjusted_chpp.items()},
            "recent_results":    opp_profile.recent_results,
            "matches_used":      opp_profile.matches_used,
        },
        "my_team": {
            "best_formation":  my_formation,
            "xp_level":        xp_level,
            "xp_warning":      xp_warning,
            "xp_alternative":  xp_alternative,
            "lineup":          fmt_lineup(my_data["lineup"]),
            "line_ratings":    {k: round(v, 1) for k, v in my_ratings.items()},
            "modified_ratings": {k: round(v, 1) for k, v in my_mod_ratings.items()},
        },
        "tactic_ranking":      tactic_rec["ranking"],
        "tactic_recommendation": {"recommended": tactic_rec["recommended"]},
        "sub_plan": [
            {
                "minute":      s.minute,
                "out_name":    s.out_name,
                "out_id":      s.out_id,
                "out_stamina": s.out_stamina,
                "in_name":     s.in_name,
                "in_id":       s.in_id,
                "reason":      s.reason,
            }
            for s in sub_plan
        ],
        "attitude_orders": [
            {
                "minute":    a.minute,
                "condition": a.condition,
                "attitude":  a.attitude,
                "reason":    a.reason,
            }
            for a in attitude_orders
        ],
        "attitude":     attitude,
        "explanation":  explanation,
    }
```

- [ ] **Step 4: Run new tests to verify they pass**

```bash
cd backend && pytest tests/test_api_pre_partita.py -k "new_analyze or new_save" -v
```

Expected: all PASS

- [ ] **Step 5: Delete old analyze tests**

In `backend/tests/test_api_pre_partita.py`, remove these functions (they test the old interface):
- `test_analyze_returns_complete_structure`
- `test_analyze_with_spirit_and_confidence`
- `test_analyze_missing_players_xml`
- `test_analyze_with_matches_xml_returns_recent_results`
- `test_analyze_malformed_players_xml_returns_422`
- `test_analyze_malformed_matches_xml_returns_422`
- `test_analyze_tactic_ranking_has_seven_entries`
- `test_analyze_attitude_is_valid`
- `test_save_and_history` (replaced by `test_new_save_and_history`)

Also remove `PLAYERS_XML` constant (no longer needed for analyze tests).

- [ ] **Step 6: Run full test suite**

```bash
cd backend && pytest -v
```

Expected: all PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/pre_partita.py backend/tests/test_api_pre_partita.py
git commit -m "feat: update analyze endpoint to use matchdetails XML; add sub_plan + attitude_orders + tactic_recommendation to response"
```

---

## Task 10: Frontend — TypeScript Types + is_home + 3-Tab XML Input

**Files:**
- Modify: `frontend/src/api/pre_partita.ts`
- Modify: `frontend/src/pages/PrePartita.tsx`

- [ ] **Step 1: Update TypeScript types in pre_partita.ts**

In `frontend/src/api/pre_partita.ts`, update the request/response types. Replace the existing `AnalyzeRequest` and `AnalyzeResponse` types (if they exist) or add:

```typescript
export interface AnalyzeRequest {
  matchdetails_xml_1: string;
  matchdetails_xml_2?: string;
  matchdetails_xml_3?: string;
  is_home: boolean;
  match_type?: string;
  spirit?: number;
  confidence?: number;
  formation_xp?: Record<string, number>;
  tactic_xp?: Record<string, number>;
}

export interface SubPlanEntry {
  minute: number;
  out_name: string;
  out_id: number;
  out_stamina: number;
  in_name: string;
  in_id: number;
  reason: string;
}

export interface AttitudeOrderEntry {
  minute: number;
  condition: string;
  attitude: string;
  reason: string;
}

export interface TacticEntry {
  name: string;
  score: number;
  explanation: string;
}

export interface AnalyzeResponse {
  opponent: {
    team_name: string;
    team_id: number;
    typical_formation: string;
    dominant_tactic: number | null;
    avg_tactic_skill: number;
    chpp_ratings: Record<string, number>;
    recent_results: Array<{ result: string; goals_for: number; goals_against: number }>;
    matches_used: number;
  };
  my_team: {
    best_formation: string;
    xp_level: number;
    xp_warning: boolean;
    xp_alternative: string | null;
    lineup: Record<string, Array<{ id: number; name: string; rating: number }>>;
    line_ratings: Record<string, number>;
    modified_ratings: Record<string, number>;
  };
  tactic_ranking: TacticEntry[];
  tactic_recommendation: { recommended: string };
  sub_plan: SubPlanEntry[];
  attitude_orders: AttitudeOrderEntry[];
  attitude: { attitude: string; reason: string };
  explanation: string;
}

export interface TacticXP {
  tactic_xp: Record<string, number>;
}
```

Add the API call function:

```typescript
export async function fetchTacticXP(): Promise<TacticXP> {
  const res = await fetch("/api/pre-partita/tactic-xp");
  if (!res.ok) throw new Error("Failed to fetch tactic XP");
  return res.json();
}

export async function putTacticXP(tactic_name: string, xp_level: number): Promise<void> {
  const res = await fetch("/api/pre-partita/tactic-xp", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tactic_name, xp_level }),
  });
  if (!res.ok) throw new Error("Failed to update tactic XP");
}
```

Also update the `postAnalyze` function to use the new request type.

- [ ] **Step 2: Add is_home toggle and 3-tab XML input to PrePartita.tsx**

In `frontend/src/pages/PrePartita.tsx`:

**State additions** (in the wizard state section):

```typescript
const [isHome, setIsHome] = useState<boolean>(true);
const [matchdetailsXml1, setMatchdetailsXml1] = useState("");
const [matchdetailsXml2, setMatchdetailsXml2] = useState("");
const [matchdetailsXml3, setMatchdetailsXml3] = useState("");
const [activeXmlTab, setActiveXmlTab] = useState<1 | 2 | 3>(1);
```

**Replace** the existing XML textarea section in Step 1 (opponent data input) with:

```tsx
{/* is_home toggle */}
<div className="flex gap-2 mb-4">
  <button
    className={`px-4 py-2 rounded ${isHome ? "bg-blue-600 text-white" : "bg-gray-200 text-gray-700"}`}
    onClick={() => setIsHome(true)}
  >
    Casa
  </button>
  <button
    className={`px-4 py-2 rounded ${!isHome ? "bg-blue-600 text-white" : "bg-gray-200 text-gray-700"}`}
    onClick={() => setIsHome(false)}
  >
    Trasferta
  </button>
</div>

{/* 3-tab matchdetails XML input */}
<div className="mb-4">
  <div className="flex gap-1 mb-2 border-b">
    {[1, 2, 3].map((tab) => (
      <button
        key={tab}
        className={`px-3 py-1 text-sm rounded-t ${
          activeXmlTab === tab
            ? "bg-white border border-b-white -mb-px font-semibold"
            : "bg-gray-100 text-gray-500"
        }`}
        onClick={() => setActiveXmlTab(tab as 1 | 2 | 3)}
      >
        Partita {tab}{tab === 1 ? " *" : " (opz.)"}
      </button>
    ))}
  </div>
  {activeXmlTab === 1 && (
    <textarea
      className="w-full h-40 font-mono text-xs border rounded p-2"
      placeholder="Incolla il matchdetails XML dell'ultima partita di campionato..."
      value={matchdetailsXml1}
      onChange={(e) => setMatchdetailsXml1(e.target.value)}
    />
  )}
  {activeXmlTab === 2 && (
    <textarea
      className="w-full h-40 font-mono text-xs border rounded p-2"
      placeholder="Partita precedente (opzionale)..."
      value={matchdetailsXml2}
      onChange={(e) => setMatchdetailsXml2(e.target.value)}
    />
  )}
  {activeXmlTab === 3 && (
    <textarea
      className="w-full h-40 font-mono text-xs border rounded p-2"
      placeholder="Due partite fa (opzionale)..."
      value={matchdetailsXml3}
      onChange={(e) => setMatchdetailsXml3(e.target.value)}
    />
  )}
</div>
```

**Update the analyze call** to use the new fields:

```typescript
const payload: AnalyzeRequest = {
  matchdetails_xml_1: matchdetailsXml1,
  matchdetails_xml_2: matchdetailsXml2 || undefined,
  matchdetails_xml_3: matchdetailsXml3 || undefined,
  is_home: isHome,
  spirit,
  confidence,
  formation_xp: formationXp,
  tactic_xp: tacticXp,
};
```

- [ ] **Step 3: Add TacticXP panel to the wizard**

In the wizard configuration step (where FormationXP is shown), add a TacticXP panel below it. Use `useQuery` to fetch tactic XP and display editable number inputs for each of the 7 tactics:

```tsx
const { data: tacticXpData } = useQuery({
  queryKey: ["tactic-xp"],
  queryFn: fetchTacticXP,
});

// In the JSX:
<div className="mt-4">
  <h3 className="font-semibold mb-2">Esperienza tattica</h3>
  <div className="grid grid-cols-2 gap-2">
    {["Normal","Pressing","Contropiede","Attacco al Centro",
      "Attacco sulle Fasce","Tiri da Fuori","Libertà d'Inventiva"].map((t) => (
      <label key={t} className="flex items-center gap-2 text-sm">
        <span className="flex-1">{t}</span>
        <input
          type="number"
          min={0}
          max={20}
          className="w-14 border rounded px-1 text-right"
          value={tacticXp[t] ?? (tacticXpData?.tactic_xp[t] ?? 0)}
          onChange={(e) => setTacticXp({ ...tacticXp, [t]: Number(e.target.value) })}
        />
      </label>
    ))}
  </div>
</div>
```

Add `tacticXp` state:

```typescript
const [tacticXp, setTacticXp] = useState<Record<string, number>>({});
```

- [ ] **Step 4: Verify frontend builds without TypeScript errors**

```bash
cd frontend && npm run build
```

Expected: build succeeds with no type errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/pre_partita.ts frontend/src/pages/PrePartita.tsx
git commit -m "feat: frontend — add is_home toggle, 3-tab matchdetails XML input, TacticXP panel"
```

---

## Task 11: Frontend — Sub Plan + Attitude Orders Output

**Files:**
- Modify: `frontend/src/pages/PrePartita.tsx`

- [ ] **Step 1: Add sub plan display to Step 3 (results)**

In the Step 3 results section of `PrePartita.tsx`, add after the tactic ranking block:

```tsx
{/* Sub Plan */}
{analysis.sub_plan && analysis.sub_plan.length > 0 && (
  <div className="mt-4">
    <h3 className="font-semibold mb-2">Piano sostituzioni</h3>
    <div className="space-y-2">
      {analysis.sub_plan.map((s, i) => (
        <div key={i} className="flex items-center gap-3 text-sm bg-gray-50 rounded px-3 py-2">
          <span className="font-mono font-bold w-10 text-center">{s.minute}'</span>
          <span className="flex-1">
            <span className="line-through text-gray-500">{s.out_name}</span>
            <span className="mx-2 text-gray-400">→</span>
            <span className="font-medium">{s.in_name}</span>
          </span>
          <span className="text-xs text-gray-400">{s.reason}</span>
        </div>
      ))}
    </div>
    {analysis.sub_plan.length === 0 && (
      <p className="text-sm text-gray-500">Nessuna sostituzione pianificata (stamina sufficiente).</p>
    )}
  </div>
)}

{/* Attitude Orders */}
{analysis.attitude_orders && analysis.attitude_orders.length > 0 && (
  <div className="mt-4">
    <h3 className="font-semibold mb-2">Ordini condizionali atteggiamento</h3>
    <div className="space-y-2">
      {analysis.attitude_orders.map((o, i) => (
        <div key={i} className="flex items-center gap-3 text-sm bg-blue-50 rounded px-3 py-2">
          <span className="font-mono font-bold w-10 text-center">{o.minute}'</span>
          <span className="text-gray-500 w-32">{o.condition}</span>
          <span className="font-semibold w-24">{o.attitude}</span>
          <span className="text-xs text-gray-400 flex-1">{o.reason}</span>
        </div>
      ))}
    </div>
  </div>
)}
```

- [ ] **Step 2: Update tactic recommendation display**

Replace the existing tactic ranking display header to highlight the recommended tactic:

```tsx
{analysis.tactic_recommendation && (
  <div className="mb-3 p-3 bg-green-50 border border-green-200 rounded">
    <span className="text-sm font-semibold text-green-800">
      Tattica consigliata: {analysis.tactic_recommendation.recommended}
    </span>
  </div>
)}
```

And in the tactic ranking list, highlight the recommended entry:

```tsx
{analysis.tactic_ranking.map((t, i) => (
  <div
    key={t.name}
    className={`flex items-center gap-2 text-sm py-1 px-2 rounded ${
      t.name === analysis.tactic_recommendation?.recommended
        ? "bg-green-100 font-semibold"
        : i === 0 ? "text-gray-700" : "text-gray-500"
    }`}
  >
    <span className="w-4 text-right text-gray-400">{i + 1}.</span>
    <span className="flex-1">{t.name}</span>
    <span className="text-xs text-gray-400">{t.explanation}</span>
  </div>
))}
```

- [ ] **Step 3: Update opponent info display**

Replace `line_ratings` references with `chpp_ratings`, and `best_formation` with `typical_formation` in the opponent info block:

```tsx
<p className="text-sm">
  Formazione tipica: <strong>{analysis.opponent.typical_formation}</strong>
  {analysis.opponent.dominant_tactic !== null && (
    <> · Tattica dominante: <strong>{TACTIC_NAMES[analysis.opponent.dominant_tactic]}</strong></>
  )}
  {" · "}Partite analizzate: {analysis.opponent.matches_used}
</p>
```

Where `TACTIC_NAMES` is:

```typescript
const TACTIC_NAMES: Record<number, string> = {
  0: "Normal", 1: "Pressing", 2: "Contropiede",
  3: "Attacco al Centro", 4: "Attacco sulle Fasce",
  5: "Tiri da Fuori", 6: "Libertà d'Inventiva",
};
```

- [ ] **Step 4: Verify frontend builds**

```bash
cd frontend && npm run build
```

Expected: build succeeds

- [ ] **Step 5: Start dev servers and manually verify the wizard**

```bash
cd /media/michel/Lavoro/source/hattrick-ai-assistant && make dev
```

Verify the wizard:
- Step 1 shows Casa/Trasferta toggle + 3 tabs (Partita 1 *, Partita 2 (opz.), Partita 3 (opz.))
- Pasting XML in tab 1 and submitting returns a complete analysis
- Results show: tactic recommendation banner + sub plan + attitude orders
- Opponent section shows `typical_formation` and `chpp_ratings` keys

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/PrePartita.tsx
git commit -m "feat: frontend — add sub plan + attitude orders display, tactic recommendation highlight"
```

---

## Self-Review

**Spec coverage:**

| Spec requirement | Task that implements it |
|---|---|
| TacticXP model (follows FormationXP pattern) | Task 1 |
| TacticXP GET/PUT endpoints | Task 1 |
| parse_both_teams + detect_opponent_team_id | Task 3 |
| parse_opponent_matchdetails + OppProfile average | Task 4 |
| HOME_NORMALIZE = 0.88 for normalization | Task 4 |
| apply_home_away_modifier | Task 5 |
| detect_wing_weakness (< 70% threshold) | Task 5 |
| detect_pressing (TacticType=1) | Task 5 |
| detect_center_attack (TacticType=3) | Task 5 |
| optimize_formation home_mod param | Task 5 |
| _chpp_to_app_scale conversion | Task 5 |
| recommend_tactic with bonuses/maluses | Task 6 |
| generate_sub_plan (stamina×12−3 formula) | Task 7 |
| generate_attitude_orders with dynamic minutes | Task 8 |
| _snap_to_hattrick_minute [60,85] | Task 8 |
| API: AnalyzeRequest with matchdetails_xml_1/2/3 + is_home | Task 9 |
| API: response with sub_plan + attitude_orders + tactic_recommendation | Task 9 |
| Frontend: is_home toggle | Task 10 |
| Frontend: 3-tab XML input | Task 10 |
| Frontend: TacticXP panel | Task 10 |
| Frontend: sub plan display | Task 11 |
| Frontend: attitude orders display | Task 11 |
| Frontend: tactic recommendation highlight | Task 11 |

**Placeholder scan:** No TBD, no "similar to task N" references, all code is explicit.

**Type consistency check:**
- `OppMatchData` and `OppProfile` defined in Task 4 → used in Task 6, 9
- `SubEntry` and `AttitudeOrder` defined in Tasks 7–8 → consumed in Task 9
- `recommend_tactic()` signature: `(lineup, opp_profile, opp_chpp_ratings, my_modified_ratings)` used consistently in Tasks 6 and 9
- `_chpp_to_app_scale` named consistently in Tasks 5 and 9
- `home_mod` param default=1.0 added to `optimize_formation` in Task 5 → used in Task 9
- Frontend types in Task 10 match backend response shape defined in Task 9

**Scale consistency:** `_chpp_to_app_scale` divides by 6.0. The resulting `app_opp` keys (`goalkeeper`, `defense`, `midfield`, `attack`) are on app scale (≈4–9) which is compatible with `modified_ratings` (≈7–14). The `generate_explanation()` call in Task 9 passes `app_opp` as opponent ratings — correct.

**Edge cases covered:**
- Single matchdetails XML: `detect_opponent_team_id` defaults to home team
- No bench non-GK available: `generate_sub_plan` returns `[]`
- Empty sub plan: `generate_attitude_orders` returns `[]`
- `matchdetails_xml_1` empty string: endpoint raises 422 with correct detail message
