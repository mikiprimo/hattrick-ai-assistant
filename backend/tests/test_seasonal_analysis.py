import pytest
from dataclasses import dataclass, field
from app.hrf.seasonal_analysis import (
    compute_status,
    analyze_youth,
    analyze_maintain,
    analyze_promote,
)


@dataclass
class P:
    """Minimal player proxy for testing."""
    id: int
    first_name: str
    last_name: str
    age: int
    age_days: int = 0
    goalkeeper: int = 0
    defending: int = 0
    playmaking: int = 0
    scoring: int = 0
    passing: int = 0
    winger: int = 0
    set_pieces: int = 0
    form: int = 7
    stamina: int = 7
    injury_days: int = -1
    salary: int = 50_000
    speciality: str = ""


def _squad():
    """11 generic players with reasonable skills."""
    return [
        P(1,  "GK",  "A", 25, goalkeeper=9),
        P(2,  "RB",  "B", 26, defending=7, winger=6),
        P(3,  "CB",  "C", 27, defending=8, playmaking=5),
        P(4,  "CB",  "D", 28, defending=8, playmaking=5),
        P(5,  "LB",  "E", 26, defending=7, winger=6),
        P(6,  "RM",  "F", 24, winger=8, playmaking=6),
        P(7,  "CM",  "G", 23, playmaking=8, passing=7),
        P(8,  "CM",  "H", 22, playmaking=7, passing=6),
        P(9,  "LM",  "I", 25, winger=7, playmaking=6),
        P(10, "FW",  "J", 24, scoring=8, passing=6),
        P(11, "FW",  "K", 23, scoring=7, passing=5),
    ]


# --- compute_status ---

def test_status_promote_on_track():
    r = compute_status("promote", position=2, points=18, played=9, history=[])
    assert r["status"] == "on_track"
    assert abs(r["projected_points"] - 28.0) < 0.1


def test_status_promote_at_risk():
    r = compute_status("promote", position=4, points=14, played=9, history=[])
    assert r["status"] == "at_risk"


def test_status_promote_off_track():
    r = compute_status("promote", position=6, points=8, played=9, history=[])
    assert r["status"] == "off_track"
    assert r["suggested_strategy"] == "maintain"


def test_status_maintain_on_track():
    r = compute_status("maintain", position=4, points=16, played=9, history=[])
    assert r["status"] == "on_track"


def test_status_maintain_at_risk():
    r = compute_status("maintain", position=7, points=10, played=9, history=[])
    assert r["status"] == "at_risk"


def test_status_no_games_played():
    r = compute_status("promote", position=0, points=0, played=0, history=[])
    assert r["status"] == "on_track"
    assert r["projected_points"] == 0


# --- analyze_youth ---

def test_analyze_youth_filters_over_24():
    players = _squad()  # all >= 22, with some >= 24
    result = analyze_youth(players, [])
    assert all(p["age"] < 24 for p in result)


def test_analyze_youth_sorted_by_potential():
    players = [
        P(1, "Young", "A", 19, playmaking=8),
        P(2, "Old", "B", 23, playmaking=9),
    ]
    result = analyze_youth(players, [])
    assert result[0]["age"] == 19  # higher potential despite lower skill


def test_analyze_youth_delta():
    @dataclass
    class FakeHistory:
        player_id: int
        snapshot_date: object
        playmaking: int
        goalkeeper: int = 0
        defending: int = 0
        scoring: int = 0
        passing: int = 0
        winger: int = 0

    from datetime import date
    history = [
        FakeHistory(1, date(2026, 1, 1), playmaking=6),
        FakeHistory(1, date(2026, 5, 1), playmaking=8),
    ]
    players = [P(1, "A", "B", 20, playmaking=8)]
    result = analyze_youth(players, history)
    assert result[0]["skill_delta"] == 2


# --- analyze_maintain ---

def test_analyze_maintain_returns_formation():
    result = analyze_maintain(_squad())
    assert result["best_formation"] in [
        "4-4-2", "3-5-2", "4-3-3", "3-4-3", "5-4-1",
        "4-5-1", "5-3-2", "5-2-3", "5-5-0", "2-5-3",
    ]


def test_analyze_maintain_weakest_sector():
    # GK strong, attack very weak
    players = [
        P(1,  "GK", "A", 25, goalkeeper=12),
        P(2,  "CB", "B", 25, defending=10),
        P(3,  "CB", "C", 25, defending=10),
        P(4,  "CB", "D", 25, defending=10),
        P(5,  "CM", "E", 25, playmaking=8),
        P(6,  "CM", "F", 25, playmaking=8),
        P(7,  "CM", "G", 25, playmaking=8),
        P(8,  "WG", "H", 25, winger=8),
        P(9,  "WG", "I", 25, winger=8),
        P(10, "FW", "J", 25, scoring=3),
        P(11, "FW", "K", 25, scoring=3),
    ]
    result = analyze_maintain(players)
    assert result["weakest_sector"] == "attack"


# --- analyze_promote ---

def test_analyze_promote_no_rivals():
    result = analyze_promote(_squad(), [])
    assert "message" in result
    assert result["rival_avg"] is None


def test_analyze_promote_with_rivals():
    strong_rival_players = [
        P(i, "R", str(i), 25, defending=10, playmaking=10, scoring=10, winger=9, goalkeeper=9)
        for i in range(11)
    ]
    rivals = [{"team_name": "FC Forte", "players": strong_rival_players, "manual_ratings": None}]
    result = analyze_promote(_squad(), rivals)
    assert result["rival_avg"] is not None
    assert len(result["needed_skills"]) > 0
    assert any(gap < 0 for gap in result["gaps"].values())


def test_analyze_promote_manual_ratings_override():
    rivals = [{"team_name": "FC Manual", "players": [], "manual_ratings": {
        "defense": 9.0, "midfield": 9.0, "attack": 9.0,
    }}]
    result = analyze_promote(_squad(), rivals)
    assert result["rival_avg"]["defense"] == pytest.approx(9.0)


def test_analyze_promote_manual_ratings_no_goalkeeper():
    """Manual ratings senza portiere non devono generare un gap portiere fittizio."""
    rivals = [{"team_name": "FC Manual", "players": [], "manual_ratings": {
        "defense": 9.0, "midfield": 9.0, "attack": 9.0,
    }}]
    result = analyze_promote(_squad(), rivals)
    assert "goalkeeper" not in result["rival_avg"]
    assert "goalkeeper" not in result["gaps"]
