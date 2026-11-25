import os
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_unused.db")

from app import models  # noqa: E402,F401
from app.api.deps import get_clock  # noqa: E402
from app.core.clock import FixedClock  # noqa: E402
from app.database.base import Base  # noqa: E402
from app.database.init_db import seed  # noqa: E402
from app.database.session import get_db, make_engine  # noqa: E402

T0 = datetime(2026, 11, 14, 10, 0, 0)


@pytest.fixture()
def engine():
    url = os.environ.get("TEST_MYSQL_URL")
    if url:
        eng = make_engine(url)
    else:
        from sqlalchemy import create_engine, event

        eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

        @event.listens_for(eng, "connect")
        def _fk(dbapi_conn, _):
            dbapi_conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture()
def db(engine):
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with Session() as s:
        seed(s)
        yield s


@pytest.fixture()
def clock():
    return FixedClock(T0)


@pytest.fixture()
def client(engine, clock):
    from main import create_app

    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with Session() as s:
        seed(s)

    app = create_app()

    def _db():
        with Session() as s:
            yield s

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_clock] = lambda: clock
    return TestClient(app)
