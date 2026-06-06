from pathlib import Path
from app.chpp.parsers.squad import parse_squad

FIXTURE = (Path(__file__).parent / "fixtures" / "squad.xml").read_bytes()


def test_parse_squad_returns_two_players():
    result = parse_squad(FIXTURE)
    assert len(result) == 2


def test_parse_squad_first_player_fields():
    result = parse_squad(FIXTURE)
    p = result[0]
    assert p["id"] == 1000001
    assert p["first_name"] == "John"
    assert p["last_name"] == "Doe"
    assert p["age"] == 25
    assert p["age_days"] == 100
    assert p["tsi"] == 4200
    assert p["form"] == 7
    assert p["injury_days"] == -1
    assert p["salary"] == 7800
    assert p["stamina"] == 8
    assert p["goalkeeper"] == 5
    assert p["defending"] == 6
    assert p["playmaking"] == 8
    assert p["winger"] == 4
    assert p["passing"] == 7
    assert p["scoring"] == 9
    assert p["set_pieces"] == 3


def test_parse_squad_injured_player():
    result = parse_squad(FIXTURE)
    p = result[1]
    assert p["id"] == 1000002
    assert p["first_name"] == "Marco"
    assert p["injury_days"] == 2
    assert p["defending"] == 10
