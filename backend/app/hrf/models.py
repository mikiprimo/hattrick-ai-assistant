from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class HRFPlayer:
    player_id: int
    first_name: str
    last_name: str
    age: int
    age_days: int
    salary: int
    injury_days: int
    form: int
    stamina: int
    speed: int
    scoring: int
    passing: int
    winger: int
    defending: int
    playmaking: int
    goalkeeper: int
    set_pieces: int
    leadership: int
    experience: int
    loyalty: int
    market_value: int
    speciality: Optional[str]
    last_match_rating: Optional[float]
    transfer_listed: bool
    country_id: Optional[int]
    homegrown: bool


@dataclass
class HRFMatchData:
    season: int
    matchround: int
    league_position: int
    league_points: int
    league_played: int
    league_goals_for: int
    league_goals_against: int
    league_series: str       # NUOVO
    tactictype: int          # NUOVO
    installning: int         # NUOVO
    lineup: dict[str, int]
    ratings: dict[int, int]


@dataclass
class HRFSnapshot:
    team_id: int
    snapshot_date: datetime
    file_path: str
    players: list[HRFPlayer] = field(default_factory=list)
    match_data: Optional[HRFMatchData] = None
