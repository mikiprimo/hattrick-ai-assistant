from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class SeasonalObjective(Base):
    __tablename__ = "seasonal_objectives"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    season: Mapped[int] = mapped_column(Integer, default=0)
    objective: Mapped[str] = mapped_column(String, default="")
