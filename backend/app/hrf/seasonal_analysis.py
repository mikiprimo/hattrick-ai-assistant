from __future__ import annotations
from dataclasses import dataclass

SKILL_LABELS: dict[int, str] = {
    0: "inesistente", 1: "disastroso", 2: "tremendo", 3: "scarso",
    4: "debole", 5: "insufficiente", 6: "accettabile", 7: "buono",
    8: "eccellente", 9: "formidabile", 10: "straordinario",
    11: "splendido", 12: "magnifico", 13: "fuoriclasse",
    14: "sovrannaturale", 15: "titanico", 16: "extraterrestre",
    17: "mitico", 18: "magico", 19: "utopico", 20: "divino",
}

_PRIMARY_SKILLS = ["goalkeeper", "defending", "playmaking", "scoring", "passing", "winger"]

LINE_IT = {
    "goalkeeper": "Portiere",
    "defense": "Difesa",
    "midfield": "Centrocampo",
    "attack": "Attacco",
}


def _primary_skill(player) -> tuple[str, int]:
    return max(
        ((s, getattr(player, s, 0)) for s in _PRIMARY_SKILLS),
        key=lambda x: x[1],
    )


def _potential_score(player) -> float:
    _, val = _primary_skill(player)
    return round(val * max(0, 24 - player.age) / 24, 2)


def compute_status(
    strategy: str,
    position: int,
    points: int,
    played: int,
    history: list[dict],
) -> dict:
    projected = round((points / played) * 14, 1) if played > 0 else 0.0
    status, message, suggested = _classify(strategy, position, points, played, projected)
    return {
        "status": status,
        "projected_points": projected,
        "current_points": points,
        "current_position": position,
        "played": played,
        "remaining": 14 - played,
        "message": message,
        "suggested_strategy": suggested,
        "history": history,
    }


def _classify(
    strategy: str, position: int, points: int, played: int, projected: float
) -> tuple[str, str, str | None]:
    if played == 0:
        return "on_track", "Stagione non ancora iniziata.", None

    if strategy == "promote":
        if position <= 2 and projected >= 26:
            return "on_track", f"Sei {position}° con {points} pt. Ottimo ritmo per la promozione.", None
        if position <= 4 or projected >= 20:
            sug = "maintain" if position > 4 else None
            return "at_risk", f"Sei {position}° con {points} pt. Ritmo a rischio (proiezione: {projected:.0f} pt).", sug
        return "off_track", (
            f"Sei {position}° con {points} pt. La promozione è difficile — valuta di cambiare obiettivo."
        ), "maintain"

    if strategy == "maintain":
        if position <= 6 and projected >= 16:
            return "on_track", f"Sei {position}° con {points} pt. Salvezza gestita.", None
        if projected >= 12:
            return "at_risk", f"Sei {position}° con {points} pt (proiezione: {projected:.0f}). Attenzione alla retrocessione.", None
        return "off_track", f"Sei in zona retrocessione ({position}°, {points} pt). Serve un cambio di rotta.", None

    # youth — no quantitative threshold
    return "on_track", "Stagione di sviluppo. Monitora i progressi dei giovani.", None


def analyze_youth(players: list, skill_history: list) -> list[dict]:
    young = [p for p in players if p.age < 24 and getattr(p, "injury_days", -1) <= 0]

    by_player: dict[int, list] = {}
    for h in skill_history:
        by_player.setdefault(h.player_id, []).append(h)

    deltas: dict[int, int] = {}
    for pid, entries in by_player.items():
        if len(entries) >= 2:
            entries.sort(key=lambda h: h.snapshot_date)
            first, last = entries[0], entries[-1]
            deltas[pid] = sum(
                max(0, getattr(last, s, 0) - getattr(first, s, 0))
                for s in _PRIMARY_SKILLS
            )
        else:
            deltas[pid] = 0

    result = []
    for p in young:
        skill_name, skill_val = _primary_skill(p)
        result.append({
            "player_id": p.id,
            "name": f"{p.first_name} {p.last_name}",
            "age": p.age,
            "primary_skill": skill_name,
            "primary_skill_value": skill_val,
            "primary_skill_label": SKILL_LABELS.get(skill_val, str(skill_val)),
            "potential_score": _potential_score(p),
            "skill_delta": deltas.get(p.id, 0),
            "speciality": getattr(p, "speciality", None),
        })

    result.sort(key=lambda x: x["potential_score"], reverse=True)
    return result


def analyze_maintain(players: list) -> dict:
    from app.hrf.strategy import _build_lineup, FORMATIONS

    healthy = [p for p in players if getattr(p, "injury_days", -1) <= 0]
    if not healthy:
        return {"error": "Nessun giocatore sano disponibile"}

    best_name, best_score, best_ratings = None, float("-inf"), None
    for name in FORMATIONS:
        data = _build_lineup(healthy, name)
        lr = data["line_ratings"]
        score = sum(lr.values())
        if score > best_score:
            best_score, best_name, best_ratings = score, name, lr

    weakest = min(best_ratings, key=lambda k: best_ratings[k])
    return {
        "best_formation": best_name,
        "line_ratings": {k: round(v, 2) for k, v in best_ratings.items()},
        "weakest_sector": weakest,
        "weakest_sector_label": LINE_IT[weakest],
        "weakest_rating": round(best_ratings[weakest], 2),
        "message": (
            f"Il reparto più debole è la {LINE_IT[weakest].lower()} "
            f"(rating {best_ratings[weakest]:.1f}). Schema consigliato: {best_name}."
        ),
    }


@dataclass
class _RivalProxy:
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
    speciality: str = ""


def _rival_line_ratings(players: list, manual: dict | None) -> dict:
    if manual and any(manual.get(k) for k in ("defense", "midfield", "attack")):
        return {
            "goalkeeper": float(manual.get("goalkeeper") or 0),
            "defense":    float(manual.get("defense")    or 0),
            "midfield":   float(manual.get("midfield")   or 0),
            "attack":     float(manual.get("attack")     or 0),
        }
    if not players:
        return {"goalkeeper": 0.0, "defense": 0.0, "midfield": 0.0, "attack": 0.0}

    from app.hrf.strategy import _build_lineup
    proxies = [_RivalProxy(
        goalkeeper=rp.goalkeeper, defending=rp.defending,
        playmaking=rp.playmaking, scoring=rp.scoring,
        passing=rp.passing, winger=rp.winger, set_pieces=rp.set_pieces,
    ) for rp in players]
    return _build_lineup(proxies, "4-4-2")["line_ratings"]


def analyze_promote(my_players: list, rivals: list) -> dict:
    """
    rivals: list of dicts with keys:
      team_name: str
      players: list of objects with goalkeeper/defending/… attributes
      manual_ratings: dict | None  — {"defense": float, "midfield": float, "attack": float}
    """
    from app.hrf.strategy import _build_lineup, FORMATIONS, role_rating

    healthy = [p for p in my_players if getattr(p, "injury_days", -1) <= 0]
    if not healthy:
        return {"error": "Nessun giocatore sano disponibile"}

    best_name, best_score, my_ratings = None, float("-inf"), None
    for name in FORMATIONS:
        data = _build_lineup(healthy, name)
        lr = data["line_ratings"]
        score = sum(lr.values())
        if score > best_score:
            best_score, best_name, my_ratings = score, name, lr

    if not rivals:
        return {
            "best_formation": best_name,
            "my_ratings": {k: round(v, 2) for k, v in my_ratings.items()},
            "rival_avg": None,
            "gaps": {},
            "needed_skills": [],
            "sell_candidates": [],
            "message": (
                "Nessuna squadra rivale registrata. "
                "Aggiungi le squadre del girone nella sezione Girone."
            ),
        }

    rival_ratings_list = [
        _rival_line_ratings(r.get("players", []), r.get("manual_ratings"))
        for r in rivals
    ]
    rival_avg = {
        line: round(sum(r[line] for r in rival_ratings_list) / len(rival_ratings_list), 2)
        for line in ("goalkeeper", "defense", "midfield", "attack")
    }

    gaps = {
        line: round(my_ratings[line] - rival_avg[line], 2)
        for line in ("goalkeeper", "defense", "midfield", "attack")
    }

    _ROLES = ["goalkeeper", "side_defender", "center_defender", "inside_mid", "winger", "forward"]

    def contribution(p) -> float:
        return max(role_rating(p, r) for r in _ROLES)

    needed_skills = []
    for line, gap in gaps.items():
        if gap < -0.5:
            skill_val = min(20, round(rival_avg[line] + 1.5))
            needed_skills.append({
                "sector": line,
                "sector_label": LINE_IT[line],
                "gap": gap,
                "min_skill_value": skill_val,
                "min_skill_label": SKILL_LABELS.get(skill_val, str(skill_val)),
            })
    needed_skills.sort(key=lambda x: x["gap"])

    avg_salary = sum(getattr(p, "salary", 0) for p in healthy) / len(healthy)
    avg_rating = sum(my_ratings.values()) / 4
    sell_candidates = [
        {
            "player_id": p.id,
            "name": f"{p.first_name} {p.last_name}",
            "age": p.age,
            "salary": getattr(p, "salary", 0),
            "contribution": round(contribution(p), 2),
        }
        for p in healthy
        if getattr(p, "salary", 0) > avg_salary and contribution(p) < avg_rating
    ]
    sell_candidates.sort(key=lambda x: x["salary"], reverse=True)

    message = f"Schema consigliato: {best_name}."
    if needed_skills:
        worst = needed_skills[0]
        message += (
            f" Gap critico in {worst['sector_label'].lower()} (∆ {worst['gap']:.1f}): "
            f"cerca almeno un giocatore '{worst['min_skill_label']}' in quel reparto."
        )

    return {
        "best_formation": best_name,
        "my_ratings": {k: round(v, 2) for k, v in my_ratings.items()},
        "rival_avg": rival_avg,
        "gaps": gaps,
        "needed_skills": needed_skills,
        "sell_candidates": sell_candidates[:3],
        "message": message,
    }
