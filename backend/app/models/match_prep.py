from datetime import datetime
from sqlalchemy import Integer, String, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class MatchPrep(Base):
    __tablename__ = "match_prep"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    opponent_name: Mapped[str] = mapped_column(String, default="")
    opponent_team_id: Mapped[int] = mapped_column(Integer, default=0)
    match_type: Mapped[str] = mapped_column(String, default="league")
    my_formation: Mapped[str] = mapped_column(String, default="")
    my_tactic: Mapped[str] = mapped_column(String, default="")
    my_attitude: Mapped[str] = mapped_column(String, default="normal")
    my_spirit: Mapped[int] = mapped_column(Integer, default=10)
    my_confidence: Mapped[int] = mapped_column(Integer, default=10)
    my_line_ratings: Mapped[str] = mapped_column(Text, default="{}")
    opp_line_ratings: Mapped[str] = mapped_column(Text, default="{}")
    tactic_ranking: Mapped[str] = mapped_column(Text, default="[]")
    explanation: Mapped[str] = mapped_column(Text, default="")
