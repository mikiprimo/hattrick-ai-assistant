from datetime import datetime
from sqlalchemy import Integer, String, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class SeasonalObjective(Base):
    __tablename__ = "seasonal_objective"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    season: Mapped[int] = mapped_column(Integer, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    league_position: Mapped[int] = mapped_column(Integer, default=0)
    league_points: Mapped[int] = mapped_column(Integer, default=0)
    league_series: Mapped[str] = mapped_column(String, default="")
    budget_manual: Mapped[int] = mapped_column(Integer, default=0)
    strategy: Mapped[str] = mapped_column(String, default="maintain")
    notes: Mapped[str] = mapped_column(Text, default="")
    recommendation: Mapped[str] = mapped_column(Text, default="")
