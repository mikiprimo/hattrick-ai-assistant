from typing import Optional
from sqlalchemy import String, Integer, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # CHPP PlayerID
    first_name: Mapped[str] = mapped_column(String, default="")
    last_name: Mapped[str] = mapped_column(String, default="")
    age: Mapped[int] = mapped_column(Integer, default=0)
    age_days: Mapped[int] = mapped_column(Integer, default=0)
    tsi: Mapped[int] = mapped_column(Integer, default=0)
    form: Mapped[int] = mapped_column(Integer, default=0)
    stamina: Mapped[int] = mapped_column(Integer, default=0)
    injury_days: Mapped[int] = mapped_column(Integer, default=-1)  # -1 = sano, >0 = settimane out
    salary: Mapped[int] = mapped_column(Integer, default=0)
    goalkeeper: Mapped[int] = mapped_column(Integer, default=0)
    defending: Mapped[int] = mapped_column(Integer, default=0)
    playmaking: Mapped[int] = mapped_column(Integer, default=0)
    winger: Mapped[int] = mapped_column(Integer, default=0)
    passing: Mapped[int] = mapped_column(Integer, default=0)
    scoring: Mapped[int] = mapped_column(Integer, default=0)
    set_pieces: Mapped[int] = mapped_column(Integer, default=0)

    # HRF fields — add after set_pieces
    speed: Mapped[int] = mapped_column(Integer, default=0)
    leadership: Mapped[int] = mapped_column(Integer, default=0)
    experience: Mapped[int] = mapped_column(Integer, default=0)
    loyalty: Mapped[int] = mapped_column(Integer, default=0)
    market_value: Mapped[int] = mapped_column(Integer, default=0)
    speciality: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_match_rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    transfer_listed: Mapped[bool] = mapped_column(Boolean, default=False)
    country_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    homegrown: Mapped[bool] = mapped_column(Boolean, default=False)
    data_source: Mapped[str] = mapped_column(String, default="CHPP")
