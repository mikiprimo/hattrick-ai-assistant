from datetime import datetime
from sqlalchemy import Integer, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class MatchSnapshot(Base):
    __tablename__ = "match_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, unique=True)
    season: Mapped[int] = mapped_column(Integer, default=0)
    matchround: Mapped[int] = mapped_column(Integer, default=0)
    league_position: Mapped[int] = mapped_column(Integer, default=0)
    league_points: Mapped[int] = mapped_column(Integer, default=0)
    league_played: Mapped[int] = mapped_column(Integer, default=0)
    league_goals_for: Mapped[int] = mapped_column(Integer, default=0)
    league_goals_against: Mapped[int] = mapped_column(Integer, default=0)
    lineup_json: Mapped[str] = mapped_column(String, default="{}")
    ratings_json: Mapped[str] = mapped_column(String, default="{}")
