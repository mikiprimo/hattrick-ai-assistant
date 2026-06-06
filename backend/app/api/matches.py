import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.match_snapshot import MatchSnapshot
from app.models.player import Player

router = APIRouter()

_LINEUP_MAP = [
    ("keeper",        "GK",          "Portiere"),
    ("rightBack",     "Difesa",      "Terzino Dx"),
    ("insideBack1",   "Difesa",      "Difensore Cen"),
    ("insideBack2",   "Difesa",      "Difensore Cen"),
    ("insideBack3",   "Difesa",      "Difensore Cen"),
    ("leftBack",      "Difesa",      "Terzino Sx"),
    ("rightWinger",   "Centrocampo", "Ala Dx"),
    ("insideMid1",    "Centrocampo", "Centrocampista"),
    ("insideMid2",    "Centrocampo", "Centrocampista"),
    ("insideMid3",    "Centrocampo", "Centrocampista"),
    ("leftWinger",    "Centrocampo", "Ala Sx"),
    ("forward1",      "Attacco",     "Attaccante"),
    ("forward2",      "Attacco",     "Attaccante"),
    ("forward3",      "Attacco",     "Attaccante"),
    ("substBack",     "Panchina",    "Riserva Dif"),
    ("substInsideMid","Panchina",    "Riserva Cen"),
    ("substWinger",   "Panchina",    "Riserva Ala"),
    ("substKeeper",   "Panchina",    "Riserva Por"),
    ("substForward",  "Panchina",    "Riserva Att"),
]


@router.get("/matches")
def get_matches(db: Session = Depends(get_db)):
    snapshots = (
        db.query(MatchSnapshot)
        .order_by(MatchSnapshot.snapshot_date.desc())
        .all()
    )

    # Parse all lineup JSON up-front so we can collect every player_id in one pass,
    # then load the entire Player set with a single query instead of one per snapshot.
    parsed = [(s, json.loads(s.lineup_json), json.loads(s.ratings_json)) for s in snapshots]
    all_player_ids = {pid for _, lineup_map, _ in parsed for pid in lineup_map.values() if pid}
    players = {
        p.id: p
        for p in db.query(Player).filter(Player.id.in_(all_player_ids)).all()
    } if all_player_ids else {}

    result = []
    for s, lineup_map, ratings_map in parsed:
        lineup = []
        for position_key, line, label in _LINEUP_MAP:
            player_id = lineup_map.get(position_key)
            if not player_id:
                continue
            p = players.get(player_id)
            name = f"{p.first_name} {p.last_name}" if p else f"#{player_id}"
            raw_rating = ratings_map.get(str(player_id), 0)
            lineup.append({
                "line": line,
                "position": label,
                "player_id": player_id,
                "name": name,
                "rating": raw_rating if raw_rating != 0 else None,
            })

        result.append({
            "snapshot_date": s.snapshot_date.strftime("%Y-%m-%d"),
            "season": s.season,
            "matchround": s.matchround,
            "lineup": lineup,
            "league": {
                "position": s.league_position,
                "points": s.league_points,
                "played": s.league_played,
                "goals_for": s.league_goals_for,
                "goals_against": s.league_goals_against,
            },
        })

    return result
