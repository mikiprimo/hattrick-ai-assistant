from dataclasses import dataclass
from lxml import etree

_PARSER = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, huge_tree=False)


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
    team_id:           int
    team_name:         str
    avg_line_ratings:  dict
    dominant_tactic:   int | None
    avg_tactic_skill:  float
    typical_formation: str
    recent_results:    list
    matches_used:      int


def _int_text(el, tag: str, default: int = 0) -> int:
    try:
        return int(el.findtext(tag, str(default)))
    except (ValueError, TypeError):
        return default


def parse_opponent_players(xml_str: str) -> tuple[int, str, list[OpponentPlayer]]:
    root = etree.fromstring(xml_str.encode(), _PARSER)
    team = root.find(".//Team")
    team_id = int(team.findtext("TeamID", "0"))
    team_name = team.findtext("TeamName", "")

    players = []
    for el in team.findall(".//PlayerList/Player"):
        if _int_text(el, "InjuryLevel", -1) > 0:
            continue
        players.append(OpponentPlayer(
            player_id=_int_text(el, "PlayerID"),
            first_name=el.findtext("FirstName", ""),
            last_name=el.findtext("LastName", ""),
            form=_int_text(el, "PlayerForm"),
            stamina=_int_text(el, "StaminaSkill"),
            injury_days=-1,
            goalkeeper=_int_text(el, "KeeperSkill"),
            defending=_int_text(el, "DefenderSkill"),
            playmaking=_int_text(el, "PlaymakerSkill"),
            scoring=_int_text(el, "ScorerSkill"),
            passing=_int_text(el, "PassingSkill"),
            winger=_int_text(el, "WingerSkill"),
            set_pieces=_int_text(el, "SetPiecesSkill"),
        ))
    return team_id, team_name, players


def parse_opponent_matches(xml_str: str, team_id: int) -> list[MatchResult]:
    root = etree.fromstring(xml_str.encode(), _PARSER)
    results = []
    for match in root.findall(".//MatchList/Match"):
        if match.findtext("MatchType") != "1":
            continue
        if match.findtext("Status") != "FINISHED":
            continue
        home_id = _int_text(match, ".//HomeTeamID")
        home_goals = _int_text(match, "HomeGoals")
        away_goals = _int_text(match, "AwayGoals")
        if home_id == team_id:
            gf, ga = home_goals, away_goals
        else:
            gf, ga = away_goals, home_goals
        result = "W" if gf > ga else "D" if gf == ga else "L"
        results.append(MatchResult(result=result, goals_for=gf, goals_against=ga))
    return results[-5:][::-1]


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
    from collections import Counter

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

    # Dominant tactic: appears in >=2 matches, else first match's tactic
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
