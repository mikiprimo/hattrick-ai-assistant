from datetime import datetime
from sqlalchemy import Integer, String, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class RivalPlayer(Base):
    __tablename__ = "rival_player"
    __table_args__ = (UniqueConstraint("team_id", "player_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(Integer, nullable=False)
    player_id: Mapped[int] = mapped_column(Integer, nullable=False)
    first_name: Mapped[str] = mapped_column(String, default="")
    last_name: Mapped[str] = mapped_column(String, default="")
    goalkeeper: Mapped[int] = mapped_column(Integer, default=0)
    defending: Mapped[int] = mapped_column(Integer, default=0)
    playmaking: Mapped[int] = mapped_column(Integer, default=0)
    scoring: Mapped[int] = mapped_column(Integer, default=0)
    passing: Mapped[int] = mapped_column(Integer, default=0)
    winger: Mapped[int] = mapped_column(Integer, default=0)
    set_pieces: Mapped[int] = mapped_column(Integer, default=0)
    form: Mapped[int] = mapped_column(Integer, default=7)
    stamina: Mapped[int] = mapped_column(Integer, default=7)
    injury_days: Mapped[int] = mapped_column(Integer, default=-1)
    imported_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
