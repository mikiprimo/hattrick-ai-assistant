from app.hrf.strategy import (
    generate_attitude_orders, AttitudeOrder, _snap_to_hattrick_minute, SubEntry,
)


def _make_sub(minute):
    return SubEntry(minute=minute, out_name="A B", out_id=1, out_stamina=5,
                    in_name="C D", in_id=10, reason="test")


def test_snap_clamps_below_60():
    assert _snap_to_hattrick_minute(40) == 60


def test_snap_clamps_above_85():
    assert _snap_to_hattrick_minute(92) == 85


def test_snap_rounds_to_nearest_5():
    assert _snap_to_hattrick_minute(63) == 65
    assert _snap_to_hattrick_minute(67) == 65
    assert _snap_to_hattrick_minute(68) == 70


def test_generate_attitude_orders_empty_sub_plan():
    result = generate_attitude_orders([], is_home=True, spirit=10, confidence=10)
    assert result == []


def test_generate_attitude_orders_structure():
    subs = [_make_sub(57), _make_sub(69)]
    result = generate_attitude_orders(subs, is_home=True, spirit=10, confidence=10)
    assert len(result) == 3
    assert all(isinstance(o, AttitudeOrder) for o in result)
    conditions = {o.condition for o in result}
    assert conditions == {"se in svantaggio", "se in vantaggio", "pareggio"}


def test_generate_attitude_orders_minutes_derived_from_subs():
    # first_sub_min=57, last_sub_min=69
    # offensive: snap(57+2) = snap(59) = 60
    # defensive: snap(69-3) = snap(66) = 65
    # balanced:  snap((69+90)//2) = snap(79) = 80
    subs = [_make_sub(57), _make_sub(69)]
    result = generate_attitude_orders(subs, is_home=True, spirit=10, confidence=10)
    by_cond = {o.condition: o for o in result}
    assert by_cond["se in svantaggio"].minute == 60
    assert by_cond["se in vantaggio"].minute == 65
    assert by_cond["pareggio"].minute == 80


def test_generate_attitude_orders_single_sub():
    subs = [_make_sub(81)]
    # offensive: snap(81+2) = snap(83) = 85
    # defensive: snap(81-3) = snap(78) = 80
    # balanced:  snap((81+90)//2) = snap(85) = 85
    result = generate_attitude_orders(subs, is_home=False, spirit=8, confidence=12)
    assert len(result) == 3
    by_cond = {o.condition: o for o in result}
    assert by_cond["se in svantaggio"].minute == 85
    assert by_cond["se in vantaggio"].minute == 80
