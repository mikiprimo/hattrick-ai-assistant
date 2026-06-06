from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.constants import SKILL_FIELDS
from app.database import get_db
from app.models.player import Player
from app.models.player_skill_history import PlayerSkillHistory

router = APIRouter()

PLAYER_DETAIL_FIELDS = [
    "id", "first_name", "last_name", "age", "age_days", "tsi", "form",
    "stamina", "speed", "injury_days", "salary",
    "goalkeeper", "defending", "playmaking", "winger", "passing", "scoring", "set_pieces",
    "leadership", "experience", "loyalty", "market_value", "speciality",
    "last_match_rating", "transfer_listed", "country_id", "homegrown", "data_source",
]


@router.get("/players/{player_id}")
def get_player(player_id: int, db: Session = Depends(get_db)):
    p = db.get(Player, player_id)
    if not p:
        raise HTTPException(status_code=404, detail="Player not found")
    return {field: getattr(p, field) for field in PLAYER_DETAIL_FIELDS}


@router.get("/players/{player_id}/history")
def get_player_history(player_id: int, db: Session = Depends(get_db)):
    p = db.get(Player, player_id)
    if not p:
        raise HTTPException(status_code=404, detail="Player not found")
    rows = (
        db.query(PlayerSkillHistory)
        .filter_by(player_id=player_id)
        .order_by(PlayerSkillHistory.snapshot_date)
        .all()
    )
    return [
        {"snapshot_date": r.snapshot_date.isoformat(),
         **{f: getattr(r, f) for f in SKILL_FIELDS}}
        for r in rows
    ]
