FORMATIONS = {
    "4-4-2": {"side_defenders": 2, "center_defenders": 2, "inside_mids": 2, "wingers": 2, "forwards": 2},
    "4-5-1": {"side_defenders": 2, "center_defenders": 2, "inside_mids": 3, "wingers": 2, "forwards": 1},
    "4-3-3": {"side_defenders": 2, "center_defenders": 2, "inside_mids": 1, "wingers": 2, "forwards": 3},
    "3-5-2": {"side_defenders": 0, "center_defenders": 3, "inside_mids": 3, "wingers": 2, "forwards": 2},
    "5-3-2": {"side_defenders": 2, "center_defenders": 3, "inside_mids": 1, "wingers": 2, "forwards": 2},
}


def role_rating(p, role: str) -> float:
    if role == "goalkeeper":
        return float(p.goalkeeper)
    if role == "side_defender":
        return p.defending * 0.7 + p.stamina * 0.3
    if role == "center_defender":
        return p.defending * 0.8 + p.playmaking * 0.2
    if role == "inside_mid":
        return p.playmaking * 0.6 + p.passing * 0.4
    if role == "winger":
        return p.winger * 0.7 + p.passing * 0.3
    if role == "forward":
        return p.scoring * 0.7 + p.passing * 0.3
    return 0.0


def _assign(available: list, role: str, n: int) -> list:
    result = []
    for _ in range(n):
        if not available:
            break
        best = max(available, key=lambda p: role_rating(p, role))
        result.append(best)
        available.remove(best)
    return result


def _build_lineup(players: list, formation_name: str) -> dict:
    available = list(players)
    f = FORMATIONS[formation_name]

    gk = _assign(available, "goalkeeper", 1)
    side_defs = _assign(available, "side_defender", f["side_defenders"])
    center_defs = _assign(available, "center_defender", f["center_defenders"])
    wingers = _assign(available, "winger", f["wingers"])
    inside_mids = _assign(available, "inside_mid", f["inside_mids"])
    forwards = _assign(available, "forward", f["forwards"])

    all_defs = side_defs + center_defs
    all_mids = wingers + inside_mids

    line_ratings = {
        "goalkeeper": role_rating(gk[0], "goalkeeper") if gk else 0.0,
        "defense": (
            sum(role_rating(p, "side_defender") for p in side_defs) +
            sum(role_rating(p, "center_defender") for p in center_defs)
        ) / len(all_defs) if all_defs else 0.0,
        "midfield": (
            sum(role_rating(p, "winger") for p in wingers) +
            sum(role_rating(p, "inside_mid") for p in inside_mids)
        ) / len(all_mids) if all_mids else 0.0,
        "attack": sum(role_rating(p, "forward") for p in forwards) / len(forwards) if forwards else 0.0,
    }

    _groups = [
        (gk,         "goalkeeper", "goalkeeper"),
        (side_defs,  "defense",    "side_defender"),
        (center_defs,"defense",    "center_defender"),
        (wingers,    "midfield",   "winger"),
        (inside_mids,"midfield",   "inside_mid"),
        (forwards,   "attack",     "forward"),
    ]
    lineup = [
        {"player": p, "line": line, "role": role}
        for group, line, role in _groups
        for p in group
    ]

    return {"lineup": lineup, "line_ratings": line_ratings}


def optimize_formation(players, opp_line_ratings: dict) -> tuple[str, dict]:
    healthy = [p for p in players if getattr(p, "injury_days", -1) <= 0]
    if not healthy:
        raise ValueError("Nessun giocatore sano disponibile")
    best_name, best_score, best_data = None, float("-inf"), None
    for name in FORMATIONS:
        data = _build_lineup(healthy, name)
        score = sum(
            max(0.0, data["line_ratings"][line] - opp_line_ratings.get(line, 0.0))
            for line in ("goalkeeper", "defense", "midfield", "attack")
        )
        if score > best_score:
            best_score, best_name, best_data = score, name, data
    return best_name, best_data


def compute_tactics(lineup_data: list, opp_line_ratings: dict, recent_results: list) -> dict:
    titolari = [e["player"] for e in lineup_data]

    stamina_avg = sum(p.stamina for p in titolari) / len(titolari) if titolari else 0
    opp_wins = sum(1 for r in recent_results[:4] if r.result == "W")
    pressing = stamina_avg >= 6 and opp_wins <= 1

    outfield = [e["player"] for e in lineup_data if e["line"] != "goalkeeper"]
    avg_ply = sum(p.playmaking for p in outfield) / len(outfield) if outfield else 0
    avg_win = sum(p.winger for p in outfield) / len(outfield) if outfield else 0
    attack_direction = "center" if avg_ply >= avg_win else "wings"

    sp_player = max(titolari, key=lambda p: p.set_pieces) if titolari else None
    set_pieces_taker = (
        {"name": f"{sp_player.first_name} {sp_player.last_name}", "set_pieces": sp_player.set_pieces}
        if sp_player else None
    )

    def_players = [e["player"] for e in lineup_data if e["line"] == "defense"]
    my_def_avg = sum(p.defending for p in def_players) / len(def_players) if def_players else 0
    attitude = "normal" if my_def_avg >= opp_line_ratings.get("defense", 0) else "defensive"

    return {
        "pressing": pressing,
        "attack_direction": attack_direction,
        "set_pieces_taker": set_pieces_taker,
        "attitude": attitude,
    }


def generate_explanation(my_line_ratings: dict, opp_line_ratings: dict,
                         formation: str, tactics: dict) -> str:
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

    parts.append(f"usa il {formation} per massimizzare questo vantaggio")

    if tactics.get("pressing"):
        parts.append("applica il pressing: la tua resistenza è maggiore")

    if tactics.get("attack_direction") == "center":
        parts.append("attacca al centro dove il tuo playmaking domina")
    else:
        parts.append("usa le fasce dove i tuoi ali fanno la differenza")

    sp = tactics.get("set_pieces_taker")
    if sp:
        parts.append(f"calci piazzati a {sp['name']} (SP {sp['set_pieces']})")

    text = ". ".join(parts)
    return text[0].upper() + text[1:] + "." if text else ""
