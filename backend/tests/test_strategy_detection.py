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
