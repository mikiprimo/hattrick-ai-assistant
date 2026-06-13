from datetime import datetime
from sqlalchemy import Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

VALID_TACTICS = frozenset([
    "Normal", "Pressing", "Contropiede",
    "Attacco al Centro", "Attacco sulle Fasce",
    "Tiri da Fuori", "Libertà d'Inventiva",
])


class TacticXP(Base):
    __tablename__ = "tactic_xp"

    tactic_name: Mapped[str] = mapped_column(String, primary_key=True)
    xp_level:    Mapped[int] = mapped_column(Integer, default=0)
    source:      Mapped[str] = mapped_column(String, default="manual")
    updated_at:  Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
