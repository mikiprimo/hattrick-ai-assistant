from app.hrf.strategy import generate_sub_plan, SubEntry, _stamina_to_minute
from app.models.player import Player


def test_stamina_to_minute():
    assert _stamina_to_minute(5) == 57
    assert _stamina_to_minute(6) == 69
    assert _stamina_to_minute(7) == 81
    assert _stamina_to_minute(1) == 55
    assert _stamina_to_minute(9) == 85


def test_sub_plan_skips_high_stamina():
    from app.hrf.strategy import _build_lineup
    players = [
        Player(id=1, goalkeeper=11, stamina=8),
        *[Player(id=i, defending=10, playmaking=8, winger=7, scoring=7, passing=7, stamina=8)
          for i in range(2, 12)],
    ]
    for p in players:
        p.form = 7
        p.first_name = "P"
        p.last_name = str(p.id)
    data = _build_lineup(players, "4-4-2")
    plan = generate_sub_plan(data["lineup"], [])
    assert plan == []


def test_sub_plan_schedules_low_stamina_player():
    from app.hrf.strategy import _build_lineup
    starters = [
        Player(id=1, goalkeeper=11, stamina=8),
        Player(id=2, playmaking=12, passing=9, defending=7, scoring=5, winger=5, stamina=5),
        *[Player(id=i, defending=10, playmaking=8, winger=7, scoring=6, passing=7, stamina=8)
          for i in range(3, 12)],
    ]
    for p in starters:
        p.form = 7
        p.first_name = "P"
        p.last_name = str(p.id)
    data = _build_lineup(starters, "4-4-2")
    bench_player = Player(id=20, playmaking=10, passing=8, defending=6, scoring=5, winger=5, stamina=8)
    bench_player.form = 7
    bench_player.first_name = "Sub"
    bench_player.last_name = "One"
    plan = generate_sub_plan(data["lineup"], [bench_player])
    assert len(plan) == 1
    assert plan[0].out_stamina == 5
    assert plan[0].minute == 57
    assert plan[0].in_id == 20


def test_sub_plan_excludes_goalkeeper_from_bench():
    from app.hrf.strategy import _build_lineup
    starters = [
        Player(id=1, goalkeeper=11, stamina=8),
        Player(id=2, playmaking=12, passing=9, defending=7, scoring=5, winger=5, stamina=5),
        *[Player(id=i, defending=10, playmaking=8, winger=7, scoring=6, passing=7, stamina=8)
          for i in range(3, 12)],
    ]
    for p in starters:
        p.form = 7
        p.first_name = "P"
        p.last_name = str(p.id)
    data = _build_lineup(starters, "4-4-2")
    gk_bench = Player(id=12, goalkeeper=9, stamina=8)
    gk_bench.form = 7
    gk_bench.first_name = "GK"
    gk_bench.last_name = "Reserve"
    plan = generate_sub_plan(data["lineup"], [gk_bench])
    assert plan == []
