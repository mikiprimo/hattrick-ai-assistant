from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import all models BEFORE create_all so Base.metadata knows about all tables
from app.models.player import Player  # noqa: F401
from app.models.player_skill_history import PlayerSkillHistory  # noqa: F401
from app.models.hrf_settings import HRFSettings  # noqa: F401
from app.models.match_snapshot import MatchSnapshot  # noqa: F401
from app.models.match_prep import MatchPrep  # noqa: F401
from app.models.formation_xp import FormationXP  # noqa: F401
from app.models.seasonal_objective import SeasonalObjective  # noqa: F401

from app.database import engine, Base

Base.metadata.create_all(bind=engine)

from app.migrations import run_migrations
run_migrations(engine)

app = FastAPI(title="Hattrick Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api import settings as settings_router
from app.api import squad as squad_router
from app.api import hrf as hrf_router
from app.api import players as players_router
from app.api import matches as matches_router
from app.api import pre_partita as pre_partita_router
from app.api import seasonal as seasonal_router

app.include_router(settings_router.router, prefix="/api")
app.include_router(squad_router.router, prefix="/api")
app.include_router(hrf_router.router, prefix="/api")
app.include_router(players_router.router, prefix="/api")
app.include_router(matches_router.router, prefix="/api")
app.include_router(pre_partita_router.router, prefix="/api")
app.include_router(seasonal_router.router, prefix="/api")
