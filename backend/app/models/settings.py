from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class CHPPSettings(Base):
    __tablename__ = "chpp_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    consumer_key: Mapped[str] = mapped_column(String, default="")
    consumer_secret: Mapped[str] = mapped_column(String, default="")
    access_token: Mapped[str] = mapped_column(String, default="")
    access_token_secret: Mapped[str] = mapped_column(String, default="")
