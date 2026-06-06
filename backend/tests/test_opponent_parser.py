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


def test_parse_matches_malformed_xml_raises():
    with pytest.raises(Exception):
        parse_opponent_matches("<not valid xml", 1)
