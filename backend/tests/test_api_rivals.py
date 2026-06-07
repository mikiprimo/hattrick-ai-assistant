import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, configure_mappers
from sqlalchemy.pool import StaticPool
from app.database import Base

configure_mappers()


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def test_rival_tables_exist(db):
    inspector = inspect(db.bind)
    tables = inspector.get_table_names()
    assert "rival_team" in tables
    assert "rival_player" in tables
    assert "rival_ratings_manual" in tables


def test_seasonal_objective_has_strategy_changed_at(db):
    inspector = inspect(db.bind)
    cols = {c["name"] for c in inspector.get_columns("seasonal_objective")}
    assert "strategy_changed_at" in cols
