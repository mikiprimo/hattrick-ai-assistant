from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models.settings import CHPPSettings

router = APIRouter()


class SettingsPayload(BaseModel):
    consumer_key: str
    consumer_secret: str
    access_token: str
    access_token_secret: str


@router.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    s = db.query(CHPPSettings).first()
    if not s:
        return {"configured": False, "oauth_complete": False}
    oauth_complete = bool(s.access_token)
    return {
        "configured": True,
        "oauth_complete": oauth_complete,
        "consumer_key": s.consumer_key,
        "access_token": s.access_token if oauth_complete else None,
    }


@router.post("/settings")
def save_settings(payload: SettingsPayload, db: Session = Depends(get_db)):
    s = db.query(CHPPSettings).first()
    if s:
        s.consumer_key = payload.consumer_key
        s.consumer_secret = payload.consumer_secret
        s.access_token = payload.access_token
        s.access_token_secret = payload.access_token_secret
    else:
        s = CHPPSettings(
            id=1,
            consumer_key=payload.consumer_key,
            consumer_secret=payload.consumer_secret,
            access_token=payload.access_token,
            access_token_secret=payload.access_token_secret,
        )
        db.add(s)
    db.commit()
    return {"status": "saved"}
