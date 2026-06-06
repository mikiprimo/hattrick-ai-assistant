from datetime import datetime
from sqlalchemy import Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class FormationXP(Base):
    __tablename__ = "formation_xp"

    formation_name: Mapped[str] = mapped_column(String, primary_key=True)
    xp_level: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String, default="manual")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
