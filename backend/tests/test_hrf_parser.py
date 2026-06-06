import pytest
from datetime import datetime
from pathlib import Path
from app.hrf.parser import _extract_filename_metadata, parse_hrf_file

FIXTURES = Path(__file__).parent / "fixtures"


def test_extract_valid_filename():
    team_id, date = _extract_filename_metadata("549298-2026-05-20.hrf")
    assert team_id == 549298
    assert date == datetime(2026, 5, 20)


def test_extract_invalid_filename_raises():
    with pytest.raises(ValueError, match="Invalid HRF filename"):
        _extract_filename_metadata("invalid_file.hrf")


def test_extract_missing_extension_raises():
    with pytest.raises(ValueError, match="Invalid HRF filename"):
        _extract_filename_metadata("549298-2026-05-20")


def test_parse_hrf_file_returns_snapshot():
    snapshot = parse_hrf_file(str(FIXTURES / "549298-2026-05-20.hrf"))
    assert snapshot.team_id == 549298
    assert snapshot.snapshot_date.year == 2026
    assert snapshot.snapshot_date.month == 5
    assert snapshot.snapshot_date.day == 20


def test_parse_hrf_file_extracts_players():
    snapshot = parse_hrf_file(str(FIXTURES / "549298-2026-05-20.hrf"))
    assert len(snapshot.players) == 2  # trainer excluded


def test_parse_hrf_player_skills():
    snapshot = parse_hrf_file(str(FIXTURES / "549298-2026-05-20.hrf"))
    mario = next(p for p in snapshot.players if p.player_id == 100001)
    assert mario.form == 7
    assert mario.stamina == 8
    assert mario.defending == 10
    assert mario.playmaking == 12
    assert mario.age == 25
    assert mario.age_days == 100
    assert mario.salary == 80000
    assert mario.homegrown is True
    assert mario.transfer_listed is False
    assert mario.last_match_rating == 7.5
    assert mario.speciality is None  # specialityLabel empty -> None


def test_parse_hrf_player_speciality():
    snapshot = parse_hrf_file(str(FIXTURES / "549298-2026-05-20.hrf"))
    luca = next(p for p in snapshot.players if p.player_id == 100002)
    assert luca.speciality == "Veloce"
    assert luca.transfer_listed is True
    assert luca.country_id == 7


def test_parse_hrf_skips_trainer():
    snapshot = parse_hrf_file(str(FIXTURES / "549298-2026-05-20.hrf"))
    ids = {p.player_id for p in snapshot.players}
    assert 295000001 not in ids


import configparser as _cp
from app.hrf.parser import _parse_basics, _parse_lastlineup, _parse_league


def _make_cfg(text: str) -> _cp.ConfigParser:
    cfg = _cp.ConfigParser()
    cfg.optionxform = str
    cfg.read_string(text)
    return cfg


def test_parse_basics_extracts_season_and_matchround():
    cfg = _make_cfg("[basics]\nseason=82\nmatchround=5\n")
    season, matchround = _parse_basics(cfg)
    assert season == 82
    assert matchround == 5


def test_parse_basics_missing_fields_returns_zeros():
    cfg = _make_cfg("[basics]\napplication=HO\n")
    season, matchround = _parse_basics(cfg)
    assert season == 0
    assert matchround == 0


def test_parse_lastlineup_includes_valid_positions():
    cfg = _make_cfg(
        "[lastlineup]\nkeeper=100001\nrightBack=100002\n"
        "insideBack1=-1\ninsideBack2=0\n"
    )
    result = _parse_lastlineup(cfg)
    assert result["lineup"] == {"keeper": 100001, "rightBack": 100002}


def test_parse_lastlineup_excludes_zero_and_minus_one():
    cfg = _make_cfg("[lastlineup]\nkeeper=0\nrightBack=-1\nforward1=100003\n")
    result = _parse_lastlineup(cfg)
    assert "keeper" not in result["lineup"]
    assert "rightBack" not in result["lineup"]
    assert result["lineup"]["forward1"] == 100003


def test_parse_league_extracts_all_fields():
    cfg = _make_cfg(
        "[league]\nspelade=4\ngjorda=8\ninslappta=3\npoang=10\nplacering=2\n"
    )
    league = _parse_league(cfg)
    assert league["position"] == 2
    assert league["points"] == 10
    assert league["played"] == 4
    assert league["goals_for"] == 8
    assert league["goals_against"] == 3
    assert league["series"] == ""  # nessun campo serie in questo cfg


def test_parse_league_missing_section_returns_empty():
    cfg = _make_cfg("[basics]\nseason=1\n")
    assert _parse_league(cfg) == {}


def test_parse_hrf_file_populates_match_data():
    snapshot = parse_hrf_file(str(FIXTURES / "549298-2026-05-21.hrf"))
    md = snapshot.match_data
    assert md is not None
    assert md.season == 82
    assert md.matchround == 5
    assert md.league_position == 2
    assert md.league_points == 10
    assert md.lineup == {"keeper": 100001, "rightBack": 100002}
    assert md.ratings[100001] == 7
    assert md.ratings[100002] == 0


def test_parse_hrf_file_match_data_excludes_empty_lineup_positions():
    snapshot = parse_hrf_file(str(FIXTURES / "549298-2026-05-21.hrf"))
    lineup = snapshot.match_data.lineup
    assert "insideBack1" not in lineup
    assert "insideBack2" not in lineup


def test_parse_lastlineup_includes_tactictype_and_installning():
    cfg = _make_cfg("[lastlineup]\nkeeper=100001\ntactictype=3\ninstallning=2\n")
    result = _parse_lastlineup(cfg)
    assert result["tactictype"] == 3
    assert result["installning"] == 2
    assert result["lineup"]["keeper"] == 100001


def test_parse_lastlineup_missing_section_returns_defaults():
    cfg = _make_cfg("[basics]\nseason=1\n")
    result = _parse_lastlineup(cfg)
    assert result == {"lineup": {}, "tactictype": 0, "installning": 0}


def test_parse_league_includes_series():
    cfg = _make_cfg("[league]\nplacering=2\npoang=10\nspelade=4\ngjorda=8\ninslappta=3\nserie=VII.935\n")
    league = _parse_league(cfg)
    assert league["series"] == "VII.935"


def test_hrf_snapshot_match_data_has_tactictype_installning_series():
    snapshot = parse_hrf_file(str(FIXTURES / "549298-2026-05-21.hrf"))
    md = snapshot.match_data
    assert hasattr(md, "tactictype")
    assert hasattr(md, "installning")
    assert hasattr(md, "league_series")
    assert isinstance(md.tactictype, int)
    assert isinstance(md.installning, int)
    assert md.league_series == "VII.935"
