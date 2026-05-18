"""SQLite database connection and lazy initialization."""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

from .schema import (
    ALL_TABLES,
    DEFAULT_CASH_BALANCE,
    DEFAULT_USER_ID,
    DEFAULT_WATCHLIST_TICKERS,
)

_DB_PATH_OVERRIDE_ENV = "FINALLY_DB_PATH"


def get_db_path() -> Path:
    """Return the absolute path to the SQLite database file.

    Resolution order:
    1. ``FINALLY_DB_PATH`` environment variable (used by tests to redirect).
    2. ``<project_root>/db/finally.db`` — three levels up from this file
       (``backend/app/db/database.py`` -> ``backend/app/db`` -> ``backend/app``
       -> ``backend`` -> project root).
    """

    override = os.environ.get(_DB_PATH_OVERRIDE_ENV)
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[3] / "db" / "finally.db"


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def init_db() -> None:
    """Create the database file, tables, and seed default data.

    Idempotent: safe to call repeatedly. Uses ``CREATE TABLE IF NOT EXISTS``
    and ``INSERT OR IGNORE`` so existing data is preserved.
    """

    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(db_path) as conn:
        await conn.execute("PRAGMA foreign_keys = ON")
        for ddl in ALL_TABLES:
            await conn.execute(ddl)

        now = _utcnow_iso()
        await conn.execute(
            "INSERT OR IGNORE INTO users_profile (id, cash_balance, created_at) "
            "VALUES (?, ?, ?)",
            (DEFAULT_USER_ID, DEFAULT_CASH_BALANCE, now),
        )

        for ticker in DEFAULT_WATCHLIST_TICKERS:
            await conn.execute(
                "INSERT OR IGNORE INTO watchlist (id, user_id, ticker, added_at) "
                "VALUES (?, ?, ?, ?)",
                (str(uuid.uuid4()), DEFAULT_USER_ID, ticker, now),
            )

        await conn.commit()


@asynccontextmanager
async def get_connection() -> AsyncIterator[aiosqlite.Connection]:
    """Async context manager yielding an aiosqlite connection.

    The connection has ``row_factory = aiosqlite.Row`` set so callers can
    access columns by name. Pending changes are committed when the context
    exits normally; the connection is always closed.
    """

    db_path = get_db_path()
    conn = await aiosqlite.connect(db_path)
    conn.row_factory = aiosqlite.Row
    try:
        await conn.execute("PRAGMA foreign_keys = ON")
        yield conn
        await conn.commit()
    finally:
        await conn.close()
