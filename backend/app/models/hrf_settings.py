from typing import Optional
from sqlalchemy import Integer, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class HRFSettings(Base):
    __tablename__ = "hrf_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hrf_folder_path: Mapped[str] = mapped_column(String, nullable=False)
    team_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
