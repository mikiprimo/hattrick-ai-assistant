from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class FormationXP(Base):
    __tablename__ = "formation_xp"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    formation: Mapped[str] = mapped_column(String, default="")
    xp: Mapped[int] = mapped_column(Integer, default=0)
