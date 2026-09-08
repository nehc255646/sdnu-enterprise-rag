"""Ensure shared Postgres tables stay compatible across services."""

from __future__ import annotations

import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def ensure_shared_schema(engine: Engine) -> None:
    """Add missing shared columns after create_all (idempotent)."""
    dialect = engine.dialect.name
    if dialect == "postgresql":
        with engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE IF EXISTS users "
                    "ADD COLUMN IF NOT EXISTS hashed_password VARCHAR(255)"
                )
            )
            conn.execute(
                text(
                    "UPDATE users SET hashed_password = '!' "
                    "WHERE hashed_password IS NULL OR hashed_password = ''"
                )
            )
        logger.info("shared schema ensured (postgresql users.hashed_password)")
        return

    if dialect == "sqlite":
        insp = inspect(engine)
        if "users" not in insp.get_table_names():
            return
        cols = {c["name"] for c in insp.get_columns("users")}
        if "hashed_password" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN hashed_password VARCHAR(255) DEFAULT '!'"))
            logger.info("shared schema ensured (sqlite users.hashed_password)")
