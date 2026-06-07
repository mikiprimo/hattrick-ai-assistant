from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.rival_team import RivalTeam
from app.models.rival_player import RivalPlayer
from app.models.rival_ratings_manual import RivalRatingsManual
from app.hrf.opponent_parser import parse_opponent_players

router = APIRouter()


class RivalCreateRequest(BaseModel):
    team_id: int
    team_name: str
    league_series: str = ""
    season: int = 0


class RivalXMLRequest(BaseModel):
    xml: str


class RivalRatingsRequest(BaseModel):
    defense: float | None = None
    midfield: float | None = None
    attack: float | None = None


def _serialize_team(t: RivalTeam, player_count: int, manual: RivalRatingsManual | None) -> dict:
    return {
        "team_id": t.team_id,
        "team_name": t.team_name,
        "league_series": t.league_series,
        "season": t.season,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
        "player_count": player_count,
        "manual_ratings": {
            "defense": manual.defense if manual else None,
            "midfield": manual.midfield if manual else None,
            "attack": manual.attack if manual else None,
        } if manual else None,
    }


@router.get("/rivals")
def list_rivals(db: Session = Depends(get_db)):
    teams = db.query(RivalTeam).order_by(RivalTeam.team_name).all()
    result = []
    for t in teams:
        count = db.query(RivalPlayer).filter_by(team_id=t.team_id).count()
        manual = db.query(RivalRatingsManual).filter_by(team_id=t.team_id).first()
        result.append(_serialize_team(t, count, manual))
    return result


@router.post("/rivals")
def create_rival(body: RivalCreateRequest, db: Session = Depends(get_db)):
    existing = db.query(RivalTeam).filter_by(team_id=body.team_id).first()
    if existing:
        existing.team_name = body.team_name
        existing.league_series = body.league_series
        existing.season = body.season
        existing.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        t = existing
    else:
        t = RivalTeam(
            team_id=body.team_id,
            team_name=body.team_name,
            league_series=body.league_series,
            season=body.season,
            updated_at=datetime.now(timezone.utc),
        )
        db.add(t)
        db.commit()
        db.refresh(t)
    return _serialize_team(t, 0, None)


@router.post("/rivals/{team_id}/import-xml")
def import_rival_xml(team_id: int, body: RivalXMLRequest, db: Session = Depends(get_db)):
    team = db.query(RivalTeam).filter_by(team_id=team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail=f"Squadra {team_id} non trovata")

    try:
        _parsed_team_id, _name, players = parse_opponent_players(body.xml)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"XML non valido: {e}")

    now = datetime.now(timezone.utc)
    db.query(RivalPlayer).filter_by(team_id=team_id).delete()
    for p in players:
        db.add(RivalPlayer(
            team_id=team_id,
            player_id=p.player_id,
            first_name=p.first_name,
            last_name=p.last_name,
            goalkeeper=p.goalkeeper,
            defending=p.defending,
            playmaking=p.playmaking,
            scoring=p.scoring,
            passing=p.passing,
            winger=p.winger,
            set_pieces=p.set_pieces,
            form=p.form,
            stamina=p.stamina,
            injury_days=p.injury_days,
            imported_at=now,
        ))
    team.updated_at = now
    db.commit()
    return {"players_imported": len(players), "team_id": team_id}


@router.put("/rivals/{team_id}/ratings")
def set_manual_ratings(team_id: int, body: RivalRatingsRequest, db: Session = Depends(get_db)):
    if not db.query(RivalTeam).filter_by(team_id=team_id).first():
        raise HTTPException(status_code=404, detail=f"Squadra {team_id} non trovata")
    manual = db.query(RivalRatingsManual).filter_by(team_id=team_id).first()
    now = datetime.now(timezone.utc)
    if manual:
        manual.defense = body.defense
        manual.midfield = body.midfield
        manual.attack = body.attack
        manual.updated_at = now
    else:
        manual = RivalRatingsManual(
            team_id=team_id,
            defense=body.defense,
            midfield=body.midfield,
            attack=body.attack,
            updated_at=now,
        )
        db.add(manual)
    db.commit()
    db.refresh(manual)
    return {"team_id": team_id, "defense": manual.defense,
            "midfield": manual.midfield, "attack": manual.attack}


@router.delete("/rivals/{team_id}")
def delete_rival(team_id: int, db: Session = Depends(get_db)):
    team = db.query(RivalTeam).filter_by(team_id=team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail=f"Squadra {team_id} non trovata")
    db.query(RivalPlayer).filter_by(team_id=team_id).delete()
    db.query(RivalRatingsManual).filter_by(team_id=team_id).delete()
    db.delete(team)
    db.commit()
    return {"deleted": team_id}
