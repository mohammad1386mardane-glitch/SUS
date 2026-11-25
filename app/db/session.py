from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from app.settings import get_settings


def create_db_engine(database_url: str | None = None) -> Engine:
    url = make_url(database_url or get_settings().database_url)
    connect_args = (
        {"check_same_thread": False} if url.get_backend_name() == "sqlite" else {}
    )
    return create_engine(url, connect_args=connect_args)


@lru_cache
def get_engine() -> Engine:
    return create_db_engine()


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_session() -> Iterator[Session]:
    with get_session_factory()() as session:
        yield session
