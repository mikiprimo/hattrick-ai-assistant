from sqlalchemy import inspect, text


def run_migrations(engine) -> None:
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    if "players" in tables:
        existing = {c["name"] for c in inspector.get_columns("players")}
        new_cols = [
            ("speed",             "INTEGER DEFAULT 0"),
            ("leadership",        "INTEGER DEFAULT 0"),
            ("experience",        "INTEGER DEFAULT 0"),
            ("loyalty",           "INTEGER DEFAULT 0"),
            ("market_value",      "INTEGER DEFAULT 0"),
            ("speciality",        "TEXT"),
            ("last_match_rating", "REAL"),
            ("transfer_listed",   "BOOLEAN DEFAULT 0"),
            ("country_id",        "INTEGER"),
            ("homegrown",         "BOOLEAN DEFAULT 0"),
            ("data_source",       "TEXT DEFAULT 'HRF'"),
        ]
        with engine.begin() as conn:
            for col_name, col_def in new_cols:
                if col_name not in existing:
                    conn.execute(text(f"ALTER TABLE players ADD COLUMN {col_name} {col_def}"))

    # Drop formation_xp and match_prep if they have old incompatible schemas
    if "formation_xp" in tables:
        cols = {c["name"] for c in inspector.get_columns("formation_xp")}
        if "formation_name" not in cols:
            with engine.begin() as conn:
                conn.execute(text("DROP TABLE formation_xp"))

    if "match_prep" in tables:
        cols = {c["name"] for c in inspector.get_columns("match_prep")}
        if "my_formation" not in cols:
            with engine.begin() as conn:
                conn.execute(text("DROP TABLE match_prep"))

    from app.database import Base
    Base.metadata.create_all(bind=engine, checkfirst=True)
