import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.hrf_settings import HRFSettings
from app.models.match_snapshot import MatchSnapshot
from app.models.player import Player
from app.models.player_skill_history import PlayerSkillHistory
from app.hrf.scanner import scan_hrf_directory
from app.hrf.parser import _extract_filename_metadata

router = APIRouter()

_SKILL_FIELDS = (
    "form", "stamina", "speed", "scoring", "passing", "winger",
    "defending", "playmaking", "goalkeeper", "set_pieces",
    "leadership", "experience", "loyalty",
)


def _player_fields(hp) -> dict:
    return {
        "first_name": hp.first_name, "last_name": hp.last_name,
        "age": hp.age, "age_days": hp.age_days,
        "salary": hp.salary, "injury_days": hp.injury_days,
        **{f: getattr(hp, f) for f in _SKILL_FIELDS},
        "market_value": hp.market_value, "speciality": hp.speciality,
        "last_match_rating": hp.last_match_rating,
        "transfer_listed": hp.transfer_listed,
        "country_id": hp.country_id, "homegrown": hp.homegrown,
        "data_source": "HRF",
    }


class HRFSettingsRequest(BaseModel):
    hrf_folder_path: str
    team_id: Optional[int] = None
    enabled: bool = True


@router.get("/hrf/settings")
def get_hrf_settings(db: Session = Depends(get_db)):
    s = db.query(HRFSettings).first()
    if not s:
        raise HTTPException(status_code=404, detail="HRF not configured")
    return {"hrf_folder_path": s.hrf_folder_path, "team_id": s.team_id, "enabled": s.enabled}


@router.post("/hrf/settings")
def set_hrf_settings(body: HRFSettingsRequest, db: Session = Depends(get_db)):
    resolved = Path(body.hrf_folder_path).resolve()
    if not resolved.exists():
        raise HTTPException(status_code=400, detail=f"Path not found: {body.hrf_folder_path}")
    if not resolved.is_dir():
        raise HTTPException(status_code=400, detail="Path must be a directory")
    body = body.model_copy(update={"hrf_folder_path": str(resolved)})
    s = db.query(HRFSettings).first()
    if s:
        s.hrf_folder_path = body.hrf_folder_path
        s.team_id = body.team_id
        s.enabled = body.enabled
    else:
        db.add(HRFSettings(id=1, hrf_folder_path=body.hrf_folder_path,
                           team_id=body.team_id, enabled=body.enabled))
    db.commit()
    return {"status": "ok"}


@router.post("/hrf/scan")
def scan_and_import(db: Session = Depends(get_db)):
    s = db.query(HRFSettings).first()
    if not s or not s.enabled:
        raise HTTPException(status_code=400, detail="HRF not configured — POST /api/hrf/settings first")

    try:
        snapshots = scan_hrf_directory(s.hrf_folder_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    players_upserted = 0

    for snapshot in snapshots:
        for hp in snapshot.players:
            fields = _player_fields(hp)
            existing = db.get(Player, hp.player_id)
            if existing:
                for k, v in fields.items():
                    setattr(existing, k, v)
            else:
                db.add(Player(id=hp.player_id, **fields))
            players_upserted += 1

            already = db.query(PlayerSkillHistory).filter_by(
                player_id=hp.player_id, snapshot_date=snapshot.snapshot_date
            ).first()
            if not already:
                skill_vals = {f: getattr(hp, f) for f in _SKILL_FIELDS}
                db.add(PlayerSkillHistory(
                    player_id=hp.player_id,
                    snapshot_date=snapshot.snapshot_date,
                    source="HRF",
                    **skill_vals,
                ))

        if snapshot.match_data:
            md = snapshot.match_data
            ms_data = {
                "season": md.season,
                "matchround": md.matchround,
                "league_position": md.league_position,
                "league_points": md.league_points,
                "league_played": md.league_played,
                "league_goals_for": md.league_goals_for,
                "league_goals_against": md.league_goals_against,
                "league_series": md.league_series,
                "lineup_json": json.dumps(md.lineup),
                "ratings_json": json.dumps({str(k): v for k, v in md.ratings.items()}),
            }
            existing_ms = db.query(MatchSnapshot).filter_by(
                snapshot_date=snapshot.snapshot_date
            ).first()
            if existing_ms:
                for k, v in ms_data.items():
                    setattr(existing_ms, k, v)
            else:
                db.add(MatchSnapshot(snapshot_date=snapshot.snapshot_date, **ms_data))

    now = datetime.now(timezone.utc)
    db.commit()
    return {
        "status": "ok",
        "scanned_at": now.isoformat(),
        "files_imported": len(snapshots),
        "players_upserted": players_upserted,
    }


@router.get("/hrf/files")
def list_hrf_files(db: Session = Depends(get_db)):
    s = db.query(HRFSettings).first()
    if not s:
        raise HTTPException(status_code=404, detail="HRF not configured")

    folder = Path(s.hrf_folder_path)
    if not folder.exists():
        raise HTTPException(status_code=404, detail=f"Folder not found: {s.hrf_folder_path}")

    imported_dates = {
        row.snapshot_date.date()
        for row in db.query(PlayerSkillHistory.snapshot_date).distinct()
    }

    files = []
    for hrf_file in sorted(folder.glob("*.hrf")):
        try:
            _team_id, snapshot_date = _extract_filename_metadata(hrf_file.name)
        except ValueError:
            continue
        files.append({
            "filename": hrf_file.name,
            "date": snapshot_date.strftime("%Y-%m-%d"),
            "imported": snapshot_date.date() in imported_dates,
        })

    return {"folder": str(folder), "files": files}
