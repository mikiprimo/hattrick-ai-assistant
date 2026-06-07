from datetime import datetime
from sqlalchemy import Integer, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class RivalRatingsManual(Base):
    __tablename__ = "rival_ratings_manual"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    defense: Mapped[float] = mapped_column(Float, nullable=True)
    midfield: Mapped[float] = mapped_column(Float, nullable=True)
    attack: Mapped[float] = mapped_column(Float, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
