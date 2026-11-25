"""Ligação à base de dados (SQLAlchemy 2.x). O URL vem do .env (DATABASE_URL)."""
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def make_engine(url: str | None = None, echo: bool | None = None) -> Engine:
    settings = get_settings()
    url = url or settings.database_url
    kwargs: dict = {"echo": settings.sql_echo if echo is None else echo, "future": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs["pool_pre_ping"] = True
        kwargs["pool_recycle"] = 1800
    eng = create_engine(url, **kwargs)
    if url.startswith("sqlite"):
        # SQLite não aplica chaves estrangeiras (ON DELETE CASCADE) por defeito.
        @event.listens_for(eng, "connect")
        def _fk_on(dbapi_conn, _):  # pragma: no cover
            dbapi_conn.execute("PRAGMA foreign_keys=ON")

    return eng


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
