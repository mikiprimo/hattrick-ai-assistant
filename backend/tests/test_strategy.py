import pytest
from app.hrf.strategy import (
    FORMATIONS, role_rating, optimize_formation, rank_tactics, recommend_attitude,
    _apply_spirit_modifier, _apply_confidence_modifier, _apply_xp_modifier, _apply_form_modifier,
)
from app.models.player import Player


def _player(**kwargs) -> Player:
    defaults = dict(
        id=1, first_name="A", last_name="B", age=25, age_days=0, tsi=1000,
        form=10, stamina=10, injury_days=-1, salary=0,
        goalkeeper=5, defending=5, playmaking=5, winger=5,
        passing=5, scoring=5, set_pieces=5,
        speed=5, leadership=5, experience=5, loyalty=10,
        market_value=0, speciality=None, last_match_rating=None,
        transfer_listed=False, country_id=None, homegrown=False, data_source="HRF",
    )
    defaults.update(kwargs)
    p = Player.__new__(Player)
    p.__dict__.update(defaults)
    return p


def _squad(n=14, **skill_overrides):
    players = []
    for i in range(n):
        p = _player(id=i+1, **skill_overrides)
        players.append(p)
    return players


class TestFormations:
    def test_all_10_formations_present(self):
        expected = {"4-4-2","3-5-2","4-3-3","3-4-3","5-4-1","4-5-1","5-3-2","5-2-3","5-5-0","2-5-3"}
        assert set(FORMATIONS.keys()) == expected

    def test_optimize_returns_valid_formation(self):
        players = _squad(14)
        name, data = optimize_formation(players, {})
        assert name in FORMATIONS
        assert "line_ratings" in data

    def test_no_healthy_players_raises(self):
        players = [_player(id=i+1, injury_days=7) for i in range(14)]
        with pytest.raises(ValueError, match="sano"):
            optimize_formation(players, {})


class TestRoleRating:
    def test_goalkeeper_weights(self):
        p = _player(goalkeeper=10, defending=5, set_pieces=5)
        expected = 10 * 0.85 + 5 * 0.10 + 5 * 0.05
        assert abs(role_rating(p, "goalkeeper") - expected) < 0.01

    def test_wing_back_weights(self):
        p = _player(defending=10, winger=5, playmaking=4, passing=3)
        expected = 10 * 0.65 + 5 * 0.20 + 4 * 0.10 + 3 * 0.05
        assert abs(role_rating(p, "side_defender") - expected) < 0.01

    def test_center_def_weights(self):
        p = _player(defending=10, playmaking=5, passing=3)
        expected = 10 * 0.75 + 5 * 0.20 + 3 * 0.05
        assert abs(role_rating(p, "center_defender") - expected) < 0.01

    def test_inner_mid_weights(self):
        p = _player(playmaking=10, passing=5, defending=4, scoring=3)
        expected = 10 * 0.55 + 5 * 0.25 + 4 * 0.15 + 3 * 0.05
        assert abs(role_rating(p, "inside_mid") - expected) < 0.01

    def test_winger_weights(self):
        p = _player(winger=10, playmaking=5, passing=4, defending=3)
        expected = 10 * 0.65 + 5 * 0.20 + 4 * 0.10 + 3 * 0.05
        assert abs(role_rating(p, "winger") - expected) < 0.01

    def test_forward_weights(self):
        p = _player(scoring=10, passing=5, winger=3)
        expected = 10 * 0.65 + 5 * 0.25 + 3 * 0.10
        assert abs(role_rating(p, "forward") - expected) < 0.01


class TestModifiers:
    def test_spirit_low(self):
        assert abs(_apply_spirit_modifier(3) - 0.85) < 0.001

    def test_spirit_high(self):
        assert abs(_apply_spirit_modifier(16) - 1.10) < 0.001

    def test_spirit_mid(self):
        m = _apply_spirit_modifier(10)
        assert 0.85 < m < 1.10

    def test_confidence_low(self):
        assert abs(_apply_confidence_modifier(3) - 0.88) < 0.001

    def test_confidence_high(self):
        assert abs(_apply_confidence_modifier(16) - 1.08) < 0.001

    def test_xp_low(self):
        assert abs(_apply_xp_modifier(7) - 0.90) < 0.001

    def test_xp_mid(self):
        assert abs(_apply_xp_modifier(10) - 0.95) < 0.001

    def test_xp_high(self):
        assert abs(_apply_xp_modifier(12) - 1.00) < 0.001

    def test_form_low(self):
        assert abs(_apply_form_modifier(3) - 0.90) < 0.001

    def test_form_high(self):
        assert abs(_apply_form_modifier(15) - 1.05) < 0.001


class TestTacticRanking:
    def test_returns_7_tactics(self):
        players = _squad(14)
        name, data = optimize_formation(players, {})
        tactics = rank_tactics(data["lineup"], {}, data["line_ratings"])
        assert len(tactics) == 7

    def test_tactics_have_required_keys(self):
        players = _squad(14)
        name, data = optimize_formation(players, {})
        tactics = rank_tactics(data["lineup"], {}, data["line_ratings"])
        for t in tactics:
            assert "name" in t
            assert "score" in t
            assert "explanation" in t

    def test_tactics_ordered_by_score_desc(self):
        players = _squad(14)
        name, data = optimize_formation(players, {})
        tactics = rank_tactics(data["lineup"], {}, data["line_ratings"])
        scores = [t["score"] for t in tactics]
        assert scores == sorted(scores, reverse=True)


class TestAttitude:
    def test_low_spirit_non_decisive_gives_cool(self):
        result = recommend_attitude(spirit=4, confidence=10, match_type="league",
                                    league_position=5, opp_position=None)
        assert result["attitude"] == "cool"

    def test_top_position_gives_mots(self):
        result = recommend_attitude(spirit=10, confidence=10, match_type="league",
                                    league_position=1, opp_position=None)
        assert result["attitude"] == "mots"

    def test_cup_gives_mots(self):
        result = recommend_attitude(spirit=10, confidence=10, match_type="cup",
                                    league_position=5, opp_position=None)
        assert result["attitude"] == "mots"

    def test_high_confidence_vs_stronger_gives_mots(self):
        result = recommend_attitude(spirit=10, confidence=15, match_type="league",
                                    league_position=8, opp_position=4)
        assert result["attitude"] == "mots"

    def test_default_is_normal(self):
        result = recommend_attitude(spirit=10, confidence=10, match_type="league",
                                    league_position=5, opp_position=None)
        assert result["attitude"] == "normal"
