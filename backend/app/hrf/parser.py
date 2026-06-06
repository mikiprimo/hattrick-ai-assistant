import re
import configparser
from datetime import datetime
from pathlib import Path
from typing import Optional
from app.hrf.models import HRFPlayer, HRFMatchData, HRFSnapshot

_FILENAME_RE = re.compile(r'^(\d+)-(\d{4}-\d{2}-\d{2})\.hrf$')
_PLAYER_SECTION_RE = re.compile(r'^player(\d+)$')

_LINEUP_KEYS = [
    "keeper", "rightBack", "insideBack1", "insideBack2", "insideBack3", "leftBack",
    "rightWinger", "insideMid1", "insideMid2", "insideMid3", "leftWinger",
    "forward1", "forward2", "forward3",
    "substBack", "substInsideMid", "substWinger", "substKeeper", "substForward",
]


def _extract_filename_metadata(filename: str) -> tuple[int, datetime]:
    m = _FILENAME_RE.match(filename)
    if not m:
        raise ValueError(f"Invalid HRF filename: {filename}")
    return int(m.group(1)), datetime.strptime(m.group(2), "%Y-%m-%d")


def _parse_basics(cfg: configparser.ConfigParser) -> tuple[int, int]:
    if "basics" not in cfg:
        return 0, 0
    sec = cfg["basics"]
    try:
        season = int(sec.get("season", "0"))
    except (ValueError, TypeError):
        season = 0
    try:
        matchround = int(sec.get("matchround", "0"))
    except (ValueError, TypeError):
        matchround = 0
    return season, matchround


def _parse_lastlineup(cfg: configparser.ConfigParser) -> dict[str, int]:
    if "lastlineup" not in cfg:
        return {}
    sec = cfg["lastlineup"]
    lineup: dict[str, int] = {}
    for key in _LINEUP_KEYS:
        val_str = sec.get(key, "0").strip()
        try:
            val = int(val_str)
        except (ValueError, TypeError):
            continue
        if val > 0:
            lineup[key] = val
    return lineup


def _parse_league(cfg: configparser.ConfigParser) -> dict[str, int]:
    if "league" not in cfg:
        return {}
    sec = cfg["league"]

    def i(k: str) -> int:
        try:
            return int(sec.get(k, "0"))
        except (ValueError, TypeError):
            return 0

    return {
        "position": i("placering"),
        "points": i("poang"),
        "played": i("spelade"),
        "goals_for": i("gjorda"),
        "goals_against": i("inslappta"),
    }


def parse_hrf_file(file_path: str) -> HRFSnapshot:
    path = Path(file_path)
    team_id, snapshot_date = _extract_filename_metadata(path.name)

    cfg = configparser.ConfigParser()
    cfg.optionxform = str
    try:
        cfg.read(str(path), encoding="utf-8")
    except UnicodeDecodeError:
        cfg.clear()
        cfg.read(str(path), encoding="latin-1")

    players = []
    ratings: dict[int, int] = {}
    for section in cfg.sections():
        m = _PLAYER_SECTION_RE.match(section)
        if not m:
            continue
        pid = int(m.group(1))
        sec = cfg[section]
        try:
            ratings[pid] = int(sec.get("rating", "0").strip())
        except (ValueError, TypeError):
            ratings[pid] = 0
        if not sec.get("firstname", "").strip():
            continue
        players.append(_parse_player(pid, sec))

    season, matchround = _parse_basics(cfg)
    lineup = _parse_lastlineup(cfg)
    league = _parse_league(cfg)

    match_data = HRFMatchData(
        season=season,
        matchround=matchround,
        league_position=league.get("position", 0),
        league_points=league.get("points", 0),
        league_played=league.get("played", 0),
        league_goals_for=league.get("goals_for", 0),
        league_goals_against=league.get("goals_against", 0),
        lineup=lineup,
        ratings=ratings,
    )

    return HRFSnapshot(team_id=team_id, snapshot_date=snapshot_date,
                       file_path=str(path), players=players, match_data=match_data)


def _parse_player(player_id: int, sec: configparser.SectionProxy) -> HRFPlayer:
    def i(key: str, default: int = 0) -> int:
        raw = sec.get(key, "").strip()
        if not raw:
            return default
        try:
            return int(raw)
        except (ValueError, TypeError):
            return default

    def f(key: str) -> Optional[float]:
        try:
            v = sec.get(key, "").strip()
            return float(v) if v else None
        except (ValueError, TypeError):
            return None

    def b(key: str) -> bool:
        return sec.get(key, "False").strip().lower() == "true"

    return HRFPlayer(
        player_id=player_id,
        first_name=sec.get("firstname", "").strip(),
        last_name=sec.get("lastname", "").strip(),
        age=i("ald"),
        age_days=i("agedays"),
        salary=i("sal"),
        injury_days=i("ska", -1),
        form=i("for"),
        stamina=i("uth"),
        speed=i("spe"),
        scoring=i("mal"),
        passing=i("fra"),
        winger=i("ytt"),
        defending=i("fas"),
        playmaking=i("bac"),
        goalkeeper=i("mlv"),
        set_pieces=i("rut"),
        leadership=i("led"),
        experience=i("gev"),
        loyalty=i("loy"),
        market_value=i("mkt"),
        speciality=sec.get("specialityLabel", "").strip() or None,
        last_match_rating=f("LastMatch_Rating"),
        transfer_listed=b("TransferListed"),
        country_id=i("CountryID") or None,
        homegrown=b("homegr"),
    )
