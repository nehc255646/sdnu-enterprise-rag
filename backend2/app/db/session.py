"""SQLAlchemy engine / session factory."""

from __future__ import annotations

import logging
from collections.abc import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import get_settings

logger = logging.getLogger(__name__)

Base = declarative_base()

_engine = None
_SessionLocal = None


def _make_engine(url: str):
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    engine = create_engine(url, pool_pre_ping=True, connect_args=connect_args)
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _fk(dbapi_conn, _):  # noqa: ANN001
            dbapi_conn.execute("PRAGMA foreign_keys=ON")

    return engine


def get_engine():
    global _engine, _SessionLocal
    if _engine is not None:
        return _engine
    settings = get_settings()
    url = settings.database_url
    try:
        engine = _make_engine(url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        _engine = engine
        logger.info("database connected: %s", url.split("@")[-1] if "@" in url else url)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"database unreachable: {url.split('@')[-1] if '@' in url else url}: {exc}") from exc
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return _engine


def get_session_factory():
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal


def init_db() -> None:
    from app.db import models  # noqa: F401
    from app.db.schema import ensure_shared_schema

    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    ensure_shared_schema(engine)


def get_db() -> Generator[Session, None, None]:
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
