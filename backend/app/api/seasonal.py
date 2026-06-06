from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.seasonal_objective import SeasonalObjective

router = APIRouter()

VALID_STRATEGIES = {"promote", "maintain", "youth"}


def _generate_recommendation(strategy: str, position: int, points: int, budget: int) -> str:
    if strategy == "promote":
        if position <= 2:
            return (f"Sei in posizione {position}: continua così, la promozione è alla portata. "
                    "Investi in qualità per i play-off.")
        return (f"Sei in posizione {position} con {points} punti. "
                "Serve una rimonta: considera acquisti mirati e massimizza l'allenamento.")
    if strategy == "youth":
        return ("Stagione di sviluppo giovani: priorità ai talenti under-21. "
                "Accetta qualche sconfitta per garantire minutaggio.")
    # maintain
    if points >= 20:
        return (f"Con {points} punti la salvezza è sicura. "
                "Mantieni il ritmo e investi nelle infrastrutture.")
    return (f"Sei in posizione {position} con {points} punti. "
            "Attenzione alla zona retrocessione: stabilizza la difesa prima di tutto.")


class SeasonalRequest(BaseModel):
    season: int
    league_position: int = 5
    league_points: int = 0
    league_series: str = ""
    budget_manual: int = 0
    strategy: str = "maintain"
    notes: str = ""


@router.get("/seasonal/current")
def get_current(db: Session = Depends(get_db)):
    obj = db.query(SeasonalObjective).order_by(SeasonalObjective.season.desc()).first()
    if not obj:
        return {"objective": None}
    return {"objective": _serialize(obj)}


@router.post("/seasonal")
def create_or_update(body: SeasonalRequest, db: Session = Depends(get_db)):
    if body.strategy not in VALID_STRATEGIES:
        raise HTTPException(status_code=422, detail=f"Strategia non valida: {body.strategy}")

    recommendation = _generate_recommendation(
        body.strategy, body.league_position, body.league_points, body.budget_manual
    )

    obj = db.query(SeasonalObjective).filter_by(season=body.season).first()
    if obj:
        obj.league_position = body.league_position
        obj.league_points   = body.league_points
        obj.league_series   = body.league_series
        obj.budget_manual   = body.budget_manual
        obj.strategy        = body.strategy
        obj.notes           = body.notes
        obj.recommendation  = recommendation
    else:
        obj = SeasonalObjective(
            season=body.season,
            created_at=datetime.utcnow(),
            league_position=body.league_position,
            league_points=body.league_points,
            league_series=body.league_series,
            budget_manual=body.budget_manual,
            strategy=body.strategy,
            notes=body.notes,
            recommendation=recommendation,
        )
        db.add(obj)
    db.commit()
    db.refresh(obj)
    return _serialize(obj)


@router.get("/seasonal/history")
def get_history(db: Session = Depends(get_db)):
    rows = db.query(SeasonalObjective).order_by(SeasonalObjective.season.desc()).all()
    return {"history": [_serialize(r) for r in rows]}


def _serialize(obj: SeasonalObjective) -> dict:
    return {
        "id": obj.id,
        "season": obj.season,
        "created_at": obj.created_at.isoformat(),
        "league_position": obj.league_position,
        "league_points": obj.league_points,
        "league_series": obj.league_series,
        "budget_manual": obj.budget_manual,
        "strategy": obj.strategy,
        "notes": obj.notes,
        "recommendation": obj.recommendation,
    }
