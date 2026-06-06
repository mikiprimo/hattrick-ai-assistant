from datetime import datetime
from sqlalchemy import Integer, DateTime, String, ForeignKey, UniqueConstraint, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class PlayerSkillHistory(Base):
    __tablename__ = "player_skill_history"
    __table_args__ = (
        UniqueConstraint("player_id", "snapshot_date", name="uq_player_snapshot"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"), nullable=False)
    snapshot_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    source: Mapped[str] = mapped_column(String, default="HRF")

    form: Mapped[int] = mapped_column(Integer, default=0)
    stamina: Mapped[int] = mapped_column(Integer, default=0)
    speed: Mapped[int] = mapped_column(Integer, default=0)
    scoring: Mapped[int] = mapped_column(Integer, default=0)
    passing: Mapped[int] = mapped_column(Integer, default=0)
    winger: Mapped[int] = mapped_column(Integer, default=0)
    defending: Mapped[int] = mapped_column(Integer, default=0)
    playmaking: Mapped[int] = mapped_column(Integer, default=0)
    goalkeeper: Mapped[int] = mapped_column(Integer, default=0)
    set_pieces: Mapped[int] = mapped_column(Integer, default=0)
    leadership: Mapped[int] = mapped_column(Integer, default=0)
    experience: Mapped[int] = mapped_column(Integer, default=0)
    loyalty: Mapped[int] = mapped_column(Integer, default=0)
