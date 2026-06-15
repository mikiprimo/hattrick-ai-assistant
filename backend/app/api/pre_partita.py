import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.queries import get_current_players
from app.hrf.opponent_parser import (
    detect_opponent_team_id, parse_opponent_matchdetails, average_opponent_profiles,
)
from app.hrf.strategy import (
    FORMATIONS, role_rating, optimize_formation, rank_tactics,
    recommend_attitude, generate_explanation, recommend_tactic,
    generate_sub_plan, generate_attitude_orders,
    apply_home_away_modifier, _chpp_to_app_scale,
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
    matchdetails_xml_1: str
    matchdetails_xml_2: str = ""
    matchdetails_xml_3: str = ""
    is_home: bool = True
    match_type: str = "league"
    spirit: int = 10
    confidence: int = 10
    formation_xp: dict[str, int] = {}
    tactic_xp: dict[str, int] = {}


@router.post("/pre-partita/analyze")
def analyze(body: AnalyzeRequest, db: Session = Depends(get_db)):
    if not body.matchdetails_xml_1.strip():
        raise HTTPException(status_code=422, detail="matchdetails_xml_1 obbligatorio")

    xmls = [x for x in [
        body.matchdetails_xml_1,
        body.matchdetails_xml_2,
        body.matchdetails_xml_3,
    ] if x.strip()]

    try:
        opponent_team_id = detect_opponent_team_id(xmls)
        opp_matches = [parse_opponent_matchdetails(xml, opponent_team_id) for xml in xmls]
        opp_profile = average_opponent_profiles(opp_matches)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"matchdetails_xml_1 non valido: {e}")

    adjusted_chpp = apply_home_away_modifier(opp_profile.avg_line_ratings, body.is_home)
    app_opp = _chpp_to_app_scale(adjusted_chpp)

    my_players = get_current_players(db)
    db_fxp = {r.formation_name: r.xp_level for r in db.query(FormationXP).all()}
    merged_fxp = {**db_fxp, **body.formation_xp}
    db_txp = {r.tactic_name: r.xp_level for r in db.query(TacticXP).all()}
    merged_txp = {**db_txp, **body.tactic_xp}

    home_mod = 1.06 if body.is_home else 1.0

    try:
        my_formation, my_data = optimize_formation(
            my_players, app_opp,
            spirit=body.spirit,
            confidence=body.confidence,
            formation_xp=merged_fxp,
            home_mod=home_mod,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Rosa locale: {e}")

    my_ratings     = my_data["line_ratings"]
    my_mod_ratings = my_data.get("modified_ratings", my_ratings)
    xp_level       = my_data.get("xp_level", 0)

    tactic_rec = recommend_tactic(my_data["lineup"], opp_profile, adjusted_chpp, my_mod_ratings)

    attitude = recommend_attitude(
        spirit=body.spirit,
        confidence=body.confidence,
        match_type=body.match_type,
        league_position=None,
        opp_position=None,
    )

    starter_ids = {e["player"].id for e in my_data["lineup"]}
    bench = [p for p in my_players
             if p.id not in starter_ids and (getattr(p, "injury_days", None) or 0) <= 0]
    sub_plan = generate_sub_plan(my_data["lineup"], bench)
    attitude_orders = generate_attitude_orders(sub_plan, body.is_home, body.spirit, body.confidence)

    explanation = generate_explanation(
        my_mod_ratings, app_opp, my_formation, tactic_rec["recommended"], attitude
    )

    xp_warning = xp_level < 8
    xp_alternative = None
    if xp_warning:
        best_alt, best_alt_xp = None, -1
        for fname in FORMATIONS:
            fxp = merged_fxp.get(fname, 0)
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
            "team_name":         opp_profile.team_name,
            "team_id":           opp_profile.team_id,
            "typical_formation": opp_profile.typical_formation,
            "dominant_tactic":   opp_profile.dominant_tactic,
            "avg_tactic_skill":  round(opp_profile.avg_tactic_skill, 1),
            "chpp_ratings":      {k: round(v, 1) for k, v in adjusted_chpp.items()},
            "recent_results":    opp_profile.recent_results,
            "matches_used":      opp_profile.matches_used,
        },
        "my_team": {
            "best_formation":   my_formation,
            "xp_level":         xp_level,
            "xp_warning":       xp_warning,
            "xp_alternative":   xp_alternative,
            "lineup":           fmt_lineup(my_data["lineup"]),
            "line_ratings":     {k: round(v, 1) for k, v in my_ratings.items()},
            "modified_ratings": {k: round(v, 1) for k, v in my_mod_ratings.items()},
        },
        "tactic_ranking":      tactic_rec["ranking"],
        "tactic_recommendation": {"recommended": tactic_rec["recommended"]},
        "sub_plan": [
            {
                "minute":      s.minute,
                "out_name":    s.out_name,
                "out_id":      s.out_id,
                "out_stamina": s.out_stamina,
                "in_name":     s.in_name,
                "in_id":       s.in_id,
                "reason":      s.reason,
            }
            for s in sub_plan
        ],
        "attitude_orders": [
            {
                "minute":    a.minute,
                "condition": a.condition,
                "attitude":  a.attitude,
                "reason":    a.reason,
            }
            for a in attitude_orders
        ],
        "attitude":    attitude,
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
