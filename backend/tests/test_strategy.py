import pytest
from dataclasses import dataclass
from app.hrf.strategy import role_rating, optimize_formation, compute_tactics, generate_explanation
from app.hrf.opponent_parser import MatchResult


@dataclass
class P:
    """Fake player per i test."""
    first_name: str = "X"
    last_name: str = "Y"
    injury_days: int = -1
    stamina: int = 7
    goalkeeper: int = 0
    defending: int = 0
    playmaking: int = 0
    scoring: int = 0
    passing: int = 0
    winger: int = 0
    set_pieces: int = 3


def squad(gk=10, df=10, mid=10, win=10, fwd=10):
    """11 giocatori con skill mirate per testare l'assegnazione."""
    return [
        P(first_name="GK", last_name="GK", goalkeeper=gk, set_pieces=8),
        P(first_name="D1", last_name="D1", defending=df),
        P(first_name="D2", last_name="D2", defending=df - 1),
        P(first_name="D3", last_name="D3", defending=df - 2),
        P(first_name="D4", last_name="D4", defending=df - 3),
        P(first_name="M1", last_name="M1", playmaking=mid),
        P(first_name="M2", last_name="M2", playmaking=mid - 1),
        P(first_name="W1", last_name="W1", winger=win),
        P(first_name="W2", last_name="W2", winger=win - 1),
        P(first_name="F1", last_name="F1", scoring=fwd),
        P(first_name="F2", last_name="F2", scoring=fwd - 1),
    ]


# --- role_rating ---

def test_role_rating_goalkeeper():
    assert role_rating(P(goalkeeper=11), "goalkeeper") == 11.0


def test_role_rating_center_defender():
    p = P(defending=10, playmaking=5)
    assert role_rating(p, "center_defender") == pytest.approx(10 * 0.8 + 5 * 0.2)


def test_role_rating_side_defender():
    p = P(defending=10, stamina=5)
    assert role_rating(p, "side_defender") == pytest.approx(10 * 0.7 + 5 * 0.3)


def test_role_rating_inside_mid():
    p = P(playmaking=10, passing=5)
    assert role_rating(p, "inside_mid") == pytest.approx(10 * 0.6 + 5 * 0.4)


def test_role_rating_winger():
    p = P(winger=10, passing=5)
    assert role_rating(p, "winger") == pytest.approx(10 * 0.7 + 5 * 0.3)


def test_role_rating_forward():
    p = P(scoring=10, passing=5)
    assert role_rating(p, "forward") == pytest.approx(10 * 0.7 + 5 * 0.3)


# --- optimize_formation ---

def test_optimize_formation_assigns_best_goalkeeper():
    players = squad(gk=15)
    _, data = optimize_formation(players, {"goalkeeper": 5, "defense": 5, "midfield": 5, "attack": 5})
    gk_entry = next(e for e in data["lineup"] if e["line"] == "goalkeeper")
    assert gk_entry["player"].first_name == "GK"


def test_optimize_formation_excludes_injured():
    players = squad()
    players[0].injury_days = 3  # GK infortunato
    _, data = optimize_formation(players, {})
    gk_entry = next(e for e in data["lineup"] if e["line"] == "goalkeeper")
    assert gk_entry["player"].first_name != "GK"


def test_optimize_formation_returns_valid_formation_name():
    valid = {"4-4-2", "4-5-1", "4-3-3", "3-5-2", "5-3-2"}
    name, _ = optimize_formation(squad(), {})
    assert name in valid


def test_optimize_formation_line_ratings_present():
    _, data = optimize_formation(squad(), {})
    for line in ("goalkeeper", "defense", "midfield", "attack"):
        assert line in data["line_ratings"]
        assert data["line_ratings"][line] >= 0


def test_optimize_formation_picks_formation_exploiting_opp_weakness():
    players = squad(df=15, mid=8, fwd=8)
    opp = {"goalkeeper": 10, "defense": 10, "midfield": 10, "attack": 5}
    name, _ = optimize_formation(players, opp)
    assert name in {"4-4-2", "4-5-1", "4-3-3", "3-5-2", "5-3-2"}


# --- compute_tactics ---

def _lineup_11(stamina=7, playmaking=8, winger=6, defending=10, sp_taker_sp=5):
    gk = P(first_name="GK", last_name="GK", goalkeeper=10, stamina=stamina, set_pieces=sp_taker_sp)
    return (
        [{"player": gk, "line": "goalkeeper", "role": "goalkeeper"}]
        + [{"player": P(stamina=stamina, defending=defending, set_pieces=1), "line": "defense", "role": "center_defender"} for _ in range(4)]
        + [{"player": P(stamina=stamina, playmaking=playmaking, set_pieces=1), "line": "midfield", "role": "inside_mid"} for _ in range(4)]
        + [{"player": P(stamina=stamina, scoring=8, winger=winger, set_pieces=1), "line": "attack", "role": "forward"} for _ in range(2)]
    )


def test_compute_tactics_pressing_on_when_stamina_ok_and_opp_weak():
    lineup = _lineup_11(stamina=8)
    recent = [MatchResult("L", 0, 1), MatchResult("D", 0, 0), MatchResult("L", 0, 2), MatchResult("D", 0, 0)]
    tactics = compute_tactics(lineup, {}, recent)
    assert tactics["pressing"] is True


def test_compute_tactics_pressing_off_when_opp_strong():
    lineup = _lineup_11(stamina=8)
    recent = [MatchResult("W", 2, 0), MatchResult("W", 3, 0), MatchResult("W", 1, 0), MatchResult("W", 2, 1)]
    tactics = compute_tactics(lineup, {}, recent)
    assert tactics["pressing"] is False


def test_compute_tactics_pressing_off_when_stamina_low():
    lineup = _lineup_11(stamina=4)
    recent = [MatchResult("L", 0, 1), MatchResult("L", 0, 2), MatchResult("L", 0, 3), MatchResult("L", 0, 1)]
    tactics = compute_tactics(lineup, {}, recent)
    assert tactics["pressing"] is False


def test_compute_tactics_attack_direction_center_when_playmaking_dominates():
    lineup = _lineup_11(playmaking=14, winger=4)
    tactics = compute_tactics(lineup, {}, [])
    assert tactics["attack_direction"] == "center"


def test_compute_tactics_attack_direction_wings_when_winger_dominates():
    lineup = _lineup_11(playmaking=4, winger=14)
    tactics = compute_tactics(lineup, {}, [])
    assert tactics["attack_direction"] == "wings"


def test_compute_tactics_set_pieces_taker_is_highest():
    lineup = _lineup_11(sp_taker_sp=12)
    tactics = compute_tactics(lineup, {}, [])
    assert tactics["set_pieces_taker"]["name"] == "GK GK"
    assert tactics["set_pieces_taker"]["set_pieces"] == 12


def test_compute_tactics_attitude_normal_when_defense_ok():
    lineup = _lineup_11(defending=12)
    opp = {"defense": 10}
    tactics = compute_tactics(lineup, opp, [])
    assert tactics["attitude"] == "normal"


def test_compute_tactics_attitude_defensive_when_defense_weak():
    lineup = _lineup_11(defending=5)
    opp = {"defense": 14}
    tactics = compute_tactics(lineup, opp, [])
    assert tactics["attitude"] == "defensive"


# --- generate_explanation ---

def test_generate_explanation_mentions_best_line():
    my = {"goalkeeper": 11.0, "defense": 13.0, "midfield": 15.0, "attack": 10.0}
    opp = {"goalkeeper": 9.0, "defense": 10.0, "midfield": 9.0, "attack": 8.0}
    tactics = {"pressing": True, "attack_direction": "center",
               "set_pieces_taker": {"name": "Mario Rossi", "set_pieces": 12}, "attitude": "normal"}
    text = generate_explanation(my, opp, "4-3-3", tactics)
    assert "centrocampo" in text.lower()
    assert "4-3-3" in text
    assert "pressing" in text.lower()
    assert "Mario Rossi" in text


def test_generate_explanation_returns_nonempty_string():
    my = {"goalkeeper": 8.0, "defense": 8.0, "midfield": 8.0, "attack": 8.0}
    opp = {"goalkeeper": 8.0, "defense": 8.0, "midfield": 8.0, "attack": 8.0}
    tactics = {"pressing": False, "attack_direction": "wings",
               "set_pieces_taker": None, "attitude": "normal"}
    text = generate_explanation(my, opp, "4-4-2", tactics)
    assert len(text) > 10
