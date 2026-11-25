from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from alembic import command
from alembic.config import Config
from app.db.session import create_db_engine, get_engine, get_session_factory
from app.settings import get_settings


@pytest.fixture
def db_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Session]:
    database_url = f"sqlite:///{tmp_path / 'test.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()

    engine: Engine | None = None
    try:
        alembic_config = Config(
            str(Path(__file__).resolve().parents[1] / "alembic.ini")
        )
        command.upgrade(alembic_config, "head")
        engine = create_db_engine(database_url)
        with Session(engine, expire_on_commit=False) as session:
            yield session
    finally:
        if engine is not None:
            engine.dispose()
        get_engine.cache_clear()
        get_session_factory.cache_clear()
        get_settings.cache_clear()
