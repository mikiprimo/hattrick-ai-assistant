from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.queries import get_current_players

router = APIRouter()

PLAYER_FIELDS = [
    "id", "first_name", "last_name", "age", "age_days", "tsi", "form",
    "stamina", "injury_days", "salary", "goalkeeper", "defending",
    "playmaking", "winger", "passing", "scoring", "set_pieces",
    "speed", "leadership", "experience", "loyalty",
    "market_value", "speciality", "last_match_rating",
    "transfer_listed", "data_source",
]


@router.get("/squad")
def get_squad(db: Session = Depends(get_db)):
    players = get_current_players(db)
    return [{field: getattr(p, field) for field in PLAYER_FIELDS} for p in players]
