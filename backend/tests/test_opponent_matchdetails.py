from pathlib import Path
import pytest
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
