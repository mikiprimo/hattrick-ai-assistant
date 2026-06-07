from datetime import datetime
from sqlalchemy import Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class RivalTeam(Base):
    __tablename__ = "rival_team"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    team_name: Mapped[str] = mapped_column(String, default="")
    league_series: Mapped[str] = mapped_column(String, default="")
    season: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
