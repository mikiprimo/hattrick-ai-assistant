from sqlalchemy import create_engine, inspect
from sqlalchemy.pool import StaticPool
from app.database import Base


def test_run_migrations_adds_hrf_columns():
    from app.models.player import Player  # noqa: F401
    from app.models.player_skill_history import PlayerSkillHistory  # noqa: F401
    from app.models.hrf_settings import HRFSettings  # noqa: F401
    from app.migrations import run_migrations

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Simulate existing DB without HRF columns
    from sqlalchemy import text
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE players (
                id INTEGER PRIMARY KEY,
                first_name TEXT DEFAULT '',
                last_name TEXT DEFAULT '',
                age INTEGER DEFAULT 0,
                age_days INTEGER DEFAULT 0,
                tsi INTEGER DEFAULT 0,
                form INTEGER DEFAULT 0,
                stamina INTEGER DEFAULT 0,
                injury_days INTEGER DEFAULT -1,
                salary INTEGER DEFAULT 0,
                goalkeeper INTEGER DEFAULT 0,
                defending INTEGER DEFAULT 0,
                playmaking INTEGER DEFAULT 0,
                winger INTEGER DEFAULT 0,
                passing INTEGER DEFAULT 0,
                scoring INTEGER DEFAULT 0,
                set_pieces INTEGER DEFAULT 0
            )
        """))
        conn.execute(text("CREATE TABLE sync_log (id INTEGER PRIMARY KEY, entity TEXT UNIQUE, last_sync_at DATETIME, status TEXT DEFAULT 'ok')"))

    run_migrations(engine)

    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("players")}
    assert "speed" in cols
    assert "leadership" in cols
    assert "experience" in cols
    assert "loyalty" in cols
    assert "market_value" in cols
    assert "speciality" in cols
    assert "last_match_rating" in cols
    assert "transfer_listed" in cols
    assert "country_id" in cols
    assert "homegrown" in cols
    assert "data_source" in cols
    tables = inspector.get_table_names()
    assert "player_skill_history" in tables
    assert "hrf_settings" in tables
