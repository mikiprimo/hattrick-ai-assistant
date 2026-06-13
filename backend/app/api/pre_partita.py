import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.queries import get_current_players
from app.hrf.opponent_parser import parse_opponent_players, parse_opponent_matches
from app.hrf.strategy import (
    FORMATIONS, role_rating, optimize_formation, rank_tactics,
    recommend_attitude, generate_explanation,
)
from app.models.formation_xp import FormationXP
from app.models.tactic_xp import TacticXP, VALID_TACTICS
from app.models.match_prep import MatchPrep

router = APIRouter()

ROLES = [
    ("goalkeeper",     "Portiere"),
    ("side_defender",  "Terzino"),
    ("center_defender","Difensore"),
    ("inside_mid",     "Centrocampista"),
    ("winger",         "Ala"),
    ("forward",        "Attaccante"),
]


@router.get("/pre-partita/squad")
def get_squad(db: Session = Depends(get_db)):
    players = get_current_players(db)
    result = []
    for p in players:
        best_role_key, best_role_label = max(ROLES, key=lambda r: role_rating(p, r[0]))
        result.append({
            "id": p.id,
            "name": f"{p.first_name} {p.last_name}",
            "form": p.form,
            "stamina": p.stamina,
            "injury_days": p.injury_days,
            "best_role": best_role_label,
            "role_rating": round(role_rating(p, best_role_key), 1),
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


@router.get("/pre-partita/formation-xp")
def get_formation_xp(db: Session = Depends(get_db)):
    rows = db.query(FormationXP).all()
    return {"formation_xp": {r.formation_name: r.xp_level for r in rows}}


class FormationXPUpdate(BaseModel):
    formation_name: str
    xp_level: int


@router.put("/pre-partita/formation-xp")
def put_formation_xp(body: FormationXPUpdate, db: Session = Depends(get_db)):
    if body.formation_name not in FORMATIONS:
        raise HTTPException(status_code=422, detail=f"Formazione non valida: {body.formation_name}")
    row = db.query(FormationXP).filter_by(formation_name=body.formation_name).first()
    if row:
        row.xp_level = body.xp_level
        row.updated_at = datetime.utcnow()
    else:
        db.add(FormationXP(formation_name=body.formation_name, xp_level=body.xp_level))
    db.commit()
    return {"ok": True}


@router.get("/pre-partita/tactic-xp")
def get_tactic_xp(db: Session = Depends(get_db)):
    rows = db.query(TacticXP).all()
    return {"tactic_xp": {r.tactic_name: r.xp_level for r in rows}}


class TacticXPUpdate(BaseModel):
    tactic_name: str
    xp_level: int


@router.put("/pre-partita/tactic-xp")
def put_tactic_xp(body: TacticXPUpdate, db: Session = Depends(get_db)):
    if body.tactic_name not in VALID_TACTICS:
        raise HTTPException(status_code=422, detail=f"Tattica non valida: {body.tactic_name}")
    row = db.query(TacticXP).filter_by(tactic_name=body.tactic_name).first()
    if row:
        row.xp_level = body.xp_level
        row.updated_at = datetime.utcnow()
    else:
        db.add(TacticXP(tactic_name=body.tactic_name, xp_level=body.xp_level))
    db.commit()
    return {"ok": True}


class AnalyzeRequest(BaseModel):
    players_xml: str
    matches_xml: str = ""
    match_type: str = "league"
    spirit: int = 10
    confidence: int = 10
    formation_xp: dict[str, int] = {}


@router.post("/pre-partita/analyze")
def analyze(body: AnalyzeRequest, db: Session = Depends(get_db)):
    if not body.players_xml.strip():
        raise HTTPException(status_code=422, detail="players_xml obbligatorio")

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
    db_xp = {r.formation_name: r.xp_level for r in db.query(FormationXP).all()}
    merged_xp = {**db_xp, **body.formation_xp}

    try:
        my_formation, my_data = optimize_formation(
            my_players, opp_ratings,
            spirit=body.spirit,
            confidence=body.confidence,
            formation_xp=merged_xp,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Rosa locale: {e}")

    my_ratings     = my_data["line_ratings"]
    my_mod_ratings = my_data.get("modified_ratings", my_ratings)
    xp_level       = my_data.get("xp_level", 0)

    tactic_ranking = rank_tactics(my_data["lineup"], opp_ratings, my_mod_ratings)
    best_tactic    = tactic_ranking[0]["name"] if tactic_ranking else "Normal"
    attitude       = recommend_attitude(
        spirit=body.spirit,
        confidence=body.confidence,
        match_type=body.match_type,
        league_position=None,
        opp_position=None,
    )
    explanation = generate_explanation(my_mod_ratings, opp_ratings, my_formation, best_tactic, attitude)

    xp_warning     = xp_level < 8
    xp_alternative = None
    if xp_warning:
        best_alt, best_alt_xp = None, -1
        for fname in FORMATIONS:
            fxp = merged_xp.get(fname, 0)
            if fxp >= 8 and fname != my_formation and fxp > best_alt_xp:
                best_alt_xp = fxp
                best_alt = fname
        xp_alternative = best_alt

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
            "team_id": opp_team_id,
            "best_formation": opp_formation,
            "line_ratings": {k: round(v, 1) for k, v in opp_ratings.items()},
            "recent_results": [
                {"result": r.result, "goals_for": r.goals_for, "goals_against": r.goals_against}
                for r in opp_recent
            ],
        },
        "my_team": {
            "best_formation": my_formation,
            "xp_level": xp_level,
            "xp_warning": xp_warning,
            "xp_alternative": xp_alternative,
            "lineup": fmt_lineup(my_data["lineup"]),
            "line_ratings": {k: round(v, 1) for k, v in my_ratings.items()},
            "modified_ratings": {k: round(v, 1) for k, v in my_mod_ratings.items()},
        },
        "tactic_ranking": tactic_ranking,
        "attitude": attitude,
        "explanation": explanation,
    }


class SaveRequest(BaseModel):
    analysis: dict
    my_spirit: int
    my_confidence: int
    my_attitude: str
    match_type: str


@router.post("/pre-partita/save")
def save_analysis(body: SaveRequest, db: Session = Depends(get_db)):
    a       = body.analysis
    my_team = a.get("my_team", {})
    opp     = a.get("opponent", {})
    db.add(MatchPrep(
        created_at=datetime.utcnow(),
        opponent_name=opp.get("team_name", ""),
        opponent_team_id=opp.get("team_id", 0),
        match_type=body.match_type,
        my_formation=my_team.get("best_formation", ""),
        my_tactic=a.get("tactic_ranking", [{}])[0].get("name", "") if a.get("tactic_ranking") else "",
        my_attitude=body.my_attitude,
        my_spirit=body.my_spirit,
        my_confidence=body.my_confidence,
        my_line_ratings=json.dumps(my_team.get("modified_ratings", {})),
        opp_line_ratings=json.dumps(opp.get("line_ratings", {})),
        tactic_ranking=json.dumps(a.get("tactic_ranking", [])),
        explanation=a.get("explanation", ""),
    ))
    db.commit()
    return {"ok": True}


@router.get("/pre-partita/history")
def get_history(db: Session = Depends(get_db)):
    rows = db.query(MatchPrep).order_by(MatchPrep.created_at.desc()).limit(20).all()
    return {"history": [
        {
            "id": r.id,
            "created_at": r.created_at.isoformat(),
            "opponent_name": r.opponent_name,
            "match_type": r.match_type,
            "my_formation": r.my_formation,
            "my_tactic": r.my_tactic,
            "my_attitude": r.my_attitude,
            "explanation": r.explanation,
        }
        for r in rows
    ]}
