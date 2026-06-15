from __future__ import annotations

FORMATIONS = {
    "4-4-2": {"side_defenders": 2, "center_defenders": 2, "inside_mids": 2, "wingers": 2, "forwards": 2},
    "3-5-2": {"side_defenders": 0, "center_defenders": 3, "inside_mids": 3, "wingers": 2, "forwards": 2},
    "4-3-3": {"side_defenders": 2, "center_defenders": 2, "inside_mids": 1, "wingers": 2, "forwards": 3},
    "3-4-3": {"side_defenders": 0, "center_defenders": 3, "inside_mids": 2, "wingers": 2, "forwards": 3},
    "5-4-1": {"side_defenders": 2, "center_defenders": 3, "inside_mids": 2, "wingers": 2, "forwards": 1},
    "4-5-1": {"side_defenders": 2, "center_defenders": 2, "inside_mids": 3, "wingers": 2, "forwards": 1},
    "5-3-2": {"side_defenders": 2, "center_defenders": 3, "inside_mids": 1, "wingers": 2, "forwards": 2},
    "5-2-3": {"side_defenders": 2, "center_defenders": 3, "inside_mids": 0, "wingers": 2, "forwards": 3},
    "5-5-0": {"side_defenders": 2, "center_defenders": 3, "inside_mids": 3, "wingers": 2, "forwards": 0},
    "2-5-3": {"side_defenders": 0, "center_defenders": 2, "inside_mids": 3, "wingers": 2, "forwards": 3},
}

_CENTER_DEF_PENALTY = {2: 0.95, 3: 0.90}
_INSIDE_MID_PENALTY = {2: 0.90, 3: 0.80}
_FORWARD_PENALTY    = {2: 0.925, 3: 0.87}

TACTIC_NAMES = [
    "Normal", "Pressing", "Contropiede",
    "Attacco al Centro", "Attacco sulle Fasce",
    "Tiri da Fuori", "Libertà d'Inventiva",
]

_HOME_ATTACK  = 1.06
_AWAY_PENALTY = 0.88


def _chpp_to_app_scale(chpp_ratings: dict) -> dict:
    """Convert CHPP 7-key hat-point ratings to app 4-key scale (÷6 approximation)."""
    _S = 6.0
    return {
        "goalkeeper": chpp_ratings.get("mid_def", 0) / _S,
        "defense":    (chpp_ratings.get("mid_def", 0) +
                       chpp_ratings.get("right_def", 0) +
                       chpp_ratings.get("left_def", 0)) / 3 / _S,
        "midfield":   chpp_ratings.get("midfield", 0) / _S,
        "attack":     (chpp_ratings.get("mid_att", 0) +
                       chpp_ratings.get("right_att", 0) +
                       chpp_ratings.get("left_att", 0)) / 3 / _S,
    }


def apply_home_away_modifier(chpp_ratings: dict, is_home: bool) -> dict:
    """Adjust opponent CHPP ratings for venue context.
    is_home=True: opponent plays away → deflate by 0.88.
    is_home=False: opponent plays at home → inflate by 1.06."""
    factor = _AWAY_PENALTY if is_home else _HOME_ATTACK
    return {k: v * factor for k, v in chpp_ratings.items()}


def detect_wing_weakness(chpp_ratings: dict) -> bool:
    """True if opponent's wing defense is <70% of their central defense."""
    wing_avg = (chpp_ratings.get("right_def", 0) + chpp_ratings.get("left_def", 0)) / 2
    mid_def = chpp_ratings.get("mid_def", 0)
    return mid_def > 0 and wing_avg < mid_def * 0.70


def detect_pressing(opp_profile) -> bool:
    """TacticType 1 = Pressing."""
    return opp_profile.dominant_tactic == 1


def detect_center_attack(opp_profile) -> bool:
    """TacticType 3 = Attacco al Centro."""
    return opp_profile.dominant_tactic == 3


def _skill(p, attr: str) -> float:
    return getattr(p, attr, None) or 0


def role_rating(p, role: str) -> float:
    if role == "goalkeeper":
        return _skill(p, "goalkeeper") * 0.85 + _skill(p, "defending") * 0.10 + _skill(p, "set_pieces") * 0.05
    if role == "side_defender":
        return _skill(p, "defending") * 0.65 + _skill(p, "winger") * 0.20 + _skill(p, "playmaking") * 0.10 + _skill(p, "passing") * 0.05
    if role == "center_defender":
        return _skill(p, "defending") * 0.75 + _skill(p, "playmaking") * 0.20 + _skill(p, "passing") * 0.05
    if role == "inside_mid":
        return _skill(p, "playmaking") * 0.55 + _skill(p, "passing") * 0.25 + _skill(p, "defending") * 0.15 + _skill(p, "scoring") * 0.05
    if role == "winger":
        return _skill(p, "winger") * 0.65 + _skill(p, "playmaking") * 0.20 + _skill(p, "passing") * 0.10 + _skill(p, "defending") * 0.05
    if role == "forward":
        return _skill(p, "scoring") * 0.65 + _skill(p, "passing") * 0.25 + _skill(p, "winger") * 0.10
    return 0.0


def _apply_spirit_modifier(spirit: int) -> float:
    return max(0.85, min(1.10, 0.85 + (spirit - 3) * 0.25 / 13))


def _apply_confidence_modifier(confidence: int) -> float:
    return max(0.88, min(1.08, 0.88 + (confidence - 3) * 0.20 / 13))


def _apply_xp_modifier(xp: int) -> float:
    if xp < 8:
        return 0.90
    if xp < 12:
        return 0.95
    return 1.0


def _apply_form_modifier(avg_form: float) -> float:
    return max(0.90, min(1.05, 0.90 + (avg_form - 3) * 0.15 / 12))


def _assign(available: list, role: str, n: int) -> list:
    result = []
    for _ in range(n):
        if not available:
            break
        best = max(available, key=lambda p: role_rating(p, role))
        result.append(best)
        available.remove(best)
    return result


def _crowding_factor(players: list, role: str) -> float:
    n = len(players)
    if role == "center_defender":
        return _CENTER_DEF_PENALTY.get(n, 1.0)
    if role == "inside_mid":
        return _INSIDE_MID_PENALTY.get(n, 1.0)
    if role == "forward":
        return _FORWARD_PENALTY.get(n, 1.0)
    return 1.0


def _build_lineup(players: list, formation_name: str) -> dict:
    available = list(players)
    f = FORMATIONS[formation_name]

    gk          = _assign(available, "goalkeeper",      1)
    side_defs   = _assign(available, "side_defender",   f["side_defenders"])
    center_defs = _assign(available, "center_defender", f["center_defenders"])
    wingers     = _assign(available, "winger",          f["wingers"])
    inside_mids = _assign(available, "inside_mid",      f["inside_mids"])
    forwards    = _assign(available, "forward",         f["forwards"])

    cd_factor = _crowding_factor(center_defs, "center_defender")
    im_factor = _crowding_factor(inside_mids, "inside_mid")
    fw_factor = _crowding_factor(forwards,    "forward")

    all_defs = side_defs + center_defs
    all_mids = wingers + inside_mids

    def_rating = 0.0
    if all_defs:
        total = sum(role_rating(p, "side_defender") for p in side_defs)
        total += sum(role_rating(p, "center_defender") * cd_factor for p in center_defs)
        def_rating = total / len(all_defs)

    mid_rating = 0.0
    if all_mids:
        total = sum(role_rating(p, "winger") for p in wingers)
        total += sum(role_rating(p, "inside_mid") * im_factor for p in inside_mids)
        mid_rating = total / len(all_mids)

    atk_rating = 0.0
    if forwards:
        atk_rating = sum(role_rating(p, "forward") * fw_factor for p in forwards) / len(forwards)

    line_ratings = {
        "goalkeeper": role_rating(gk[0], "goalkeeper") if gk else 0.0,
        "defense": def_rating,
        "midfield": mid_rating,
        "attack": atk_rating,
    }

    _groups = [
        (gk,          "goalkeeper", "goalkeeper"),
        (side_defs,   "defense",    "side_defender"),
        (center_defs, "defense",    "center_defender"),
        (wingers,     "midfield",   "winger"),
        (inside_mids, "midfield",   "inside_mid"),
        (forwards,    "attack",     "forward"),
    ]
    lineup = [
        {"player": p, "line": line, "role": role}
        for group, line, role in _groups
        for p in group
    ]

    return {"lineup": lineup, "line_ratings": line_ratings}


def optimize_formation(
    players,
    opp_line_ratings: dict,
    spirit: int = 10,
    confidence: int = 10,
    formation_xp: dict[str, int] | None = None,
    home_mod: float = 1.0,
) -> tuple[str, dict]:
    healthy = [p for p in players if (getattr(p, "injury_days", None) or 0) <= 0]
    if not healthy:
        raise ValueError("Nessun giocatore sano disponibile")

    formation_xp = formation_xp or {}
    spirit_mod     = _apply_spirit_modifier(spirit)
    confidence_mod = _apply_confidence_modifier(confidence)

    best_name, best_score, best_data = None, float("-inf"), None

    for name in FORMATIONS:
        data = _build_lineup(healthy, name)
        lr   = data["line_ratings"]

        xp       = formation_xp.get(name, 0)
        xp_mod   = _apply_xp_modifier(xp)
        avg_form = (sum(_skill(e["player"], "form") or 10 for e in data["lineup"])
                    / max(len(data["lineup"]), 1))
        form_mod = _apply_form_modifier(avg_form)

        modified = {
            "goalkeeper": lr["goalkeeper"] * xp_mod * form_mod * home_mod,
            "defense":    lr["defense"]    * xp_mod * form_mod * home_mod,
            "midfield":   lr["midfield"]   * xp_mod * form_mod * spirit_mod * home_mod,
            "attack":     lr["attack"]     * xp_mod * form_mod * confidence_mod * home_mod,
        }
        data["modified_ratings"] = modified
        data["xp_level"] = xp

        score = sum(
            max(0.0, modified[line] - opp_line_ratings.get(line, 0.0))
            for line in ("goalkeeper", "defense", "midfield", "attack")
        )

        if score > best_score:
            best_score, best_name, best_data = score, name, data

    return best_name, best_data


def rank_tactics(
    lineup: list[dict],
    opp_line_ratings: dict,
    my_modified_ratings: dict,
) -> list[dict]:
    titolari  = [e["player"] for e in lineup]
    outfield  = [e["player"] for e in lineup if e["line"] != "goalkeeper"]
    defenders = [e["player"] for e in lineup if e["line"] == "defense"]
    my_wingers = [e["player"] for e in lineup if e["role"] == "winger"]

    opp_def       = opp_line_ratings.get("defense", 7.0)
    opp_mid       = opp_line_ratings.get("midfield", 7.0)
    my_winger_avg = (sum(_skill(p, "winger") for p in my_wingers) / len(my_wingers)
                     if my_wingers else 0.0)

    def _quick(p) -> bool:
        sp = (getattr(p, "speciality", None) or "").lower()
        return "quick" in sp or "veloce" in sp

    def _unpredictable(p) -> bool:
        sp = (getattr(p, "speciality", None) or "").lower()
        return "unpredictable" in sp or "imprevedibile" in sp

    results = []

    # Normal
    results.append({
        "name": "Normal",
        "score": 0.0,
        "explanation": "Gioco equilibrato senza modificatori tattici.",
    })

    # Pressing
    pressing_score = (sum(_skill(p, "defending") + _skill(p, "stamina") for p in titolari)
                      / max(len(titolari), 1))
    results.append({
        "name": "Pressing",
        "score": round(pressing_score, 2),
        "explanation": f"Pressing attivo: stamina e difesa media = {pressing_score:.1f}.",
    })

    # Contropiede
    ctrop_base = sum(_skill(p, "defending") + _skill(p, "passing") * 2 for p in defenders)
    quick_bonus = sum(0.15 for p in outfield if _quick(p))
    ctrop_score = ctrop_base * (1 + quick_bonus)
    results.append({
        "name": "Contropiede",
        "score": round(ctrop_score, 2),
        "explanation": f"Contropiede: difensori+bonus velocisti = {ctrop_score:.1f}.",
    })

    # Attacco al Centro
    centro_base = sum(_skill(p, "passing") for p in outfield)
    centro_score = centro_base * (1.20 if opp_def < 7 else 1.0)
    results.append({
        "name": "Attacco al Centro",
        "score": round(centro_score, 2),
        "explanation": (f"Attacco centrale: {centro_score:.1f}"
                        + (" (+20% difesa avv. debole)" if opp_def < 7 else "") + "."),
    })

    # Attacco sulle Fasce
    fasce_base = sum(_skill(p, "passing") for p in outfield)
    fasce_score = fasce_base * (1.20 if my_winger_avg > opp_mid else 1.0)
    results.append({
        "name": "Attacco sulle Fasce",
        "score": round(fasce_score, 2),
        "explanation": (f"Attacco sulle fasce: {fasce_score:.1f}"
                        + (" (+20% ali superiori)" if my_winger_avg > opp_mid else "") + "."),
    })

    # Tiri da Fuori
    tdf_base = sum(_skill(p, "scoring") + _skill(p, "set_pieces") / 3 for p in outfield)
    tdf_score = tdf_base * (1.10 if opp_def >= 8 else 1.0)
    results.append({
        "name": "Tiri da Fuori",
        "score": round(tdf_score, 2),
        "explanation": (f"Tiri da fuori: {tdf_score:.1f}"
                        + (" (+10% difesa avv. alta)" if opp_def >= 8 else "") + "."),
    })

    # Libertà d'Inventiva
    lib_base = sum(_skill(p, "passing") + _skill(p, "experience") for p in outfield)
    unp_bonus = sum(0.25 for p in outfield if _unpredictable(p))
    lib_score = lib_base * (1 + unp_bonus)
    results.append({
        "name": "Libertà d'Inventiva",
        "score": round(lib_score, 2),
        "explanation": (f"Libertà d'inventiva: {lib_score:.1f}"
                        + (f" (+{unp_bonus*100:.0f}% imprevedibili)" if unp_bonus > 0 else "") + "."),
    })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def recommend_tactic(
    lineup: list[dict],
    opp_profile,
    opp_chpp_ratings: dict,
    my_modified_ratings: dict,
) -> dict:
    """Extends rank_tactics() with opponent-aware bonuses/maluses from CHPP analysis."""
    app_opp = _chpp_to_app_scale(opp_chpp_ratings)
    ranking = rank_tactics(lineup, app_opp, my_modified_ratings)

    wing_weak    = detect_wing_weakness(opp_chpp_ratings)
    center_atk   = detect_center_attack(opp_profile)
    opp_pressing = detect_pressing(opp_profile)

    for r in ranking:
        if r["name"] == "Attacco sulle Fasce" and wing_weak:
            r["score"] += 20.0
            r["explanation"] += " Bonus: avversario debole sulle fasce (+20)."
        if r["name"] == "Attacco al Centro" and center_atk:
            r["score"] -= 10.0
            r["explanation"] += " Malus: avversario forte al centro (-10)."
        if r["name"] == "Contropiede" and center_atk:
            r["score"] += 10.0
            r["explanation"] += " Bonus: Contropiede efficace contro Attacco al Centro (+10)."
        if r["name"] == "Pressing" and opp_pressing:
            r["score"] -= 5.0
            r["explanation"] += " Malus: avversario abituato al Pressing (-5)."

    ranking.sort(key=lambda x: x["score"], reverse=True)
    return {"recommended": ranking[0]["name"], "ranking": ranking}


from dataclasses import dataclass as _dc


@_dc
class SubEntry:
    minute:      int
    out_name:    str
    out_id:      int
    out_stamina: int
    in_name:     str
    in_id:       int
    reason:      str


def _stamina_to_minute(stamina: int) -> int:
    return max(55, min(85, stamina * 12 - 3))


def generate_sub_plan(lineup: list[dict], bench: list) -> list[SubEntry]:
    """Schedule up to 3 substitutions for starters with stamina ≤ 7.
    Bench goalkeepers (goalkeeper skill > 8) are excluded from outfield sub candidates."""
    starters_at_risk = sorted(
        [e for e in lineup if e["line"] != "goalkeeper"
         and (_skill(e["player"], "stamina") or 10) <= 7],
        key=lambda e: _skill(e["player"], "stamina") or 10,
    )[:3]

    non_gk_bench = [p for p in bench if (_skill(p, "goalkeeper") or 0) <= 8]

    plan: list[SubEntry] = []
    used: set[int] = set()

    for entry in starters_at_risk:
        p_out = entry["player"]
        stamina = _skill(p_out, "stamina") or 10
        minute = _stamina_to_minute(stamina)
        candidates = [b for b in non_gk_bench if b.id not in used]
        if not candidates:
            break
        best_in = max(candidates, key=lambda b: role_rating(b, entry["role"]))
        used.add(best_in.id)
        plan.append(SubEntry(
            minute=minute,
            out_name=f"{p_out.first_name} {p_out.last_name}",
            out_id=p_out.id,
            out_stamina=stamina,
            in_name=f"{best_in.first_name} {best_in.last_name}",
            in_id=best_in.id,
            reason=f"Stamina {stamina}: calo previsto al {minute}'",
        ))

    return plan


def recommend_attitude(
    spirit: int,
    confidence: int,
    match_type: str,
    league_position: int | None,
    opp_position: int | None,
) -> dict:
    pos = league_position or 99

    if spirit <= 5 and match_type != "cup":
        return {"attitude": "cool", "reason": "Spirito basso: risparmia energie con la Partitella."}

    if spirit >= 8 and (pos <= 2 or match_type == "cup"):
        return {"attitude": "mots", "reason": "Posizione o coppa: gioca la Partita della Stagione."}

    if confidence >= 15 and opp_position is not None and opp_position <= pos - 3:
        return {"attitude": "mots", "reason": "Avversario più forte: MotS per annullare la sottovalutazione."}

    return {"attitude": "normal", "reason": "Condizioni standard: atteggiamento Normale."}


def generate_explanation(
    my_line_ratings: dict,
    opp_line_ratings: dict,
    formation: str,
    best_tactic: str,
    attitude: dict,
) -> str:
    LINE_IT = {
        "goalkeeper": "portiere", "defense": "difesa",
        "midfield": "centrocampo", "attack": "attacco",
    }
    diffs = {k: my_line_ratings.get(k, 0) - opp_line_ratings.get(k, 0) for k in LINE_IT}
    best = max(diffs, key=lambda k: diffs[k])
    my_v, opp_v, diff = my_line_ratings.get(best, 0), opp_line_ratings.get(best, 0), diffs[best]

    parts = []
    if diff > 3:
        parts.append(f"il tuo {LINE_IT[best]} è nettamente superiore ({my_v:.1f} vs {opp_v:.1f})")
    elif diff > 0:
        parts.append(f"il tuo {LINE_IT[best]} è superiore ({my_v:.1f} vs {opp_v:.1f})")
    else:
        parts.append("la partita è equilibrata")

    parts.append(f"usa il {formation}")
    parts.append(f"tattica consigliata: {best_tactic}")
    parts.append(attitude["reason"])

    text = ". ".join(parts)
    return text[0].upper() + text[1:] + "." if text else ""
