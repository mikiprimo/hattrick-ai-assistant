from pathlib import Path
import pytest
from app.hrf.opponent_parser import (
    parse_both_teams, detect_opponent_team_id,
    parse_opponent_matchdetails, average_opponent_profiles,
    OppMatchData, OppProfile, TeamMatchData,
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
