from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.player import Player
from app.models.player_skill_history import PlayerSkillHistory
from app.models.sync_log import SyncLog


def upsert_sync_log(db: Session, entity: str, status: str, synced_at: datetime) -> None:
    existing = db.query(SyncLog).filter_by(entity=entity).first()
    if existing:
        existing.status = status
        existing.synced_at = synced_at
    else:
        db.add(SyncLog(entity=entity, status=status, synced_at=synced_at))


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
