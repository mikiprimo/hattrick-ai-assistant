from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.queries import get_current_players
from app.hrf.opponent_parser import parse_opponent_players, parse_opponent_matches
from app.hrf.strategy import role_rating, optimize_formation, compute_tactics, generate_explanation

router = APIRouter()

ROLES = [
    ("goalkeeper", "Portiere"),
    ("side_defender", "Terzino"),
    ("center_defender", "Difensore"),
    ("inside_mid", "Centrocampista"),
    ("winger", "Ala"),
    ("forward", "Attaccante"),
]


@router.get("/pre-partita/squad")
def get_squad(db: Session = Depends(get_db)):
    players = get_current_players(db)
    result = []
    for p in players:
        best_role_key, best_role_label = max(ROLES, key=lambda r: role_rating(p, r[0]))
        best_rating = role_rating(p, best_role_key)
        result.append({
            "id": p.id,
            "name": f"{p.first_name} {p.last_name}",
            "form": p.form,
            "stamina": p.stamina,
            "injury_days": p.injury_days,
            "best_role": best_role_label,
            "role_rating": round(best_rating, 1),
            "skills": {
                "goalkeeper": p.goalkeeper,
                "defending": p.defending,
                "playmaking": p.playmaking,
                "scoring": p.scoring,
                "passing": p.passing,
                "winger": p.winger,
                "set_pieces": p.set_pieces,
            },
        })
    return {"players": result}


class AnalyzeRequest(BaseModel):
    players_xml: str
    matches_xml: str = ""


@router.post("/pre-partita/analyze")
def analyze(body: AnalyzeRequest, db: Session = Depends(get_db)):
    try:
        opp_team_id, opp_team_name, opp_players = parse_opponent_players(body.players_xml)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"players_xml non valido: {e}")

    opp_recent = []
    if body.matches_xml.strip():
        try:
            opp_recent = parse_opponent_matches(body.matches_xml, opp_team_id)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"matches_xml non valido: {e}")

    try:
        opp_formation, opp_data = optimize_formation(opp_players, {})
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Avversario: {e}")
    opp_ratings = opp_data["line_ratings"]

    my_players = get_current_players(db)
    try:
        my_formation, my_data = optimize_formation(my_players, opp_ratings)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Rosa locale: {e}")
    my_ratings = my_data["line_ratings"]

    tactics = compute_tactics(my_data["lineup"], opp_ratings, opp_recent)
    explanation = generate_explanation(my_ratings, opp_ratings, my_formation, tactics)

    def fmt_lineup(lineup_data):
        by_line: dict[str, list] = {"goalkeeper": [], "defense": [], "midfield": [], "attack": []}
        for entry in lineup_data:
            p = entry["player"]
            by_line[entry["line"]].append({
                "id": p.id,
                "name": f"{p.first_name} {p.last_name}",
                "rating": round(role_rating(p, entry["role"]), 1),
            })
        return by_line

    return {
        "opponent": {
            "team_name": opp_team_name,
            "best_formation": opp_formation,
            "line_ratings": {k: round(v, 1) for k, v in opp_ratings.items()},
            "recent_results": [
                {"result": r.result, "goals_for": r.goals_for, "goals_against": r.goals_against}
                for r in opp_recent
            ],
        },
        "my_team": {
            "best_formation": my_formation,
            "lineup": fmt_lineup(my_data["lineup"]),
            "line_ratings": {k: round(v, 1) for k, v in my_ratings.items()},
        },
        "tactics": tactics,
        "explanation": explanation,
    }
