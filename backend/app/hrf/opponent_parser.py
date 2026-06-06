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
