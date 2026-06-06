from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.player import Player
from app.models.player_skill_history import PlayerSkillHistory


def get_current_players(db: Session) -> list[Player]:
    latest = db.query(func.max(PlayerSkillHistory.snapshot_date)).scalar()
    if latest is None:
        return db.query(Player).all()
    active_ids = {
        r.player_id
        for r in db.query(PlayerSkillHistory.player_id)
        .filter(PlayerSkillHistory.snapshot_date == latest)
    }
    return db.query(Player).filter(Player.id.in_(active_ids)).all()
