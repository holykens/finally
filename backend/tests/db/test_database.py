"""Tests for the SQLite database layer."""

from __future__ import annotations

from pathlib import Path

import aiosqlite
import pytest

from app.db import get_connection, get_db_path, init_db
from app.db.schema import (
    DEFAULT_CASH_BALANCE,
    DEFAULT_USER_ID,
    DEFAULT_WATCHLIST_TICKERS,
    TABLE_NAMES,
)


@pytest.fixture
def temp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect the database to a temp path for the duration of the test."""

    db_file = tmp_path / "test_finally.db"
    monkeypatch.setenv("FINALLY_DB_PATH", str(db_file))
    return db_file


async def test_get_db_path_uses_env_override(temp_db: Path) -> None:
    assert get_db_path() == temp_db


async def test_get_db_path_default_under_project_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FINALLY_DB_PATH", raising=False)
    path = get_db_path()
    assert path.name == "finally.db"
    assert path.parent.name == "db"
    # Project root layout: <root>/backend/app/db/database.py
    assert (path.parent.parent / "backend").exists(), (
        f"Expected backend dir at {path.parent.parent / 'backend'}"
    )


async def test_init_db_creates_file_and_parent_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_file = tmp_path / "nested" / "dir" / "finally.db"
    monkeypatch.setenv("FINALLY_DB_PATH", str(db_file))

    assert not db_file.exists()
    await init_db()
    assert db_file.exists()
    assert db_file.parent.is_dir()


async def test_init_db_creates_all_tables(temp_db: Path) -> None:
    await init_db()

    async with aiosqlite.connect(temp_db) as conn:
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        rows = await cursor.fetchall()
        names = {row[0] for row in rows}

    for expected in TABLE_NAMES:
        assert expected in names, f"Table {expected!r} missing after init_db"


async def test_init_db_seeds_default_user(temp_db: Path) -> None:
    await init_db()

    async with aiosqlite.connect(temp_db) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute(
            "SELECT id, cash_balance, created_at FROM users_profile"
        )
        rows = await cursor.fetchall()

    assert len(rows) == 1
    row = rows[0]
    assert row["id"] == DEFAULT_USER_ID
    assert row["cash_balance"] == pytest.approx(DEFAULT_CASH_BALANCE)
    assert row["created_at"]  # non-empty ISO timestamp


async def test_init_db_seeds_ten_watchlist_tickers(temp_db: Path) -> None:
    await init_db()

    async with aiosqlite.connect(temp_db) as conn:
        cursor = await conn.execute(
            "SELECT ticker FROM watchlist WHERE user_id = ? ORDER BY ticker",
            (DEFAULT_USER_ID,),
        )
        rows = await cursor.fetchall()

    tickers = {row[0] for row in rows}
    assert len(rows) == 10
    assert tickers == set(DEFAULT_WATCHLIST_TICKERS)


async def test_init_db_is_idempotent(temp_db: Path) -> None:
    await init_db()
    await init_db()
    await init_db()

    async with aiosqlite.connect(temp_db) as conn:
        users_cursor = await conn.execute("SELECT COUNT(*) FROM users_profile")
        users_count = (await users_cursor.fetchone())[0]

        watch_cursor = await conn.execute(
            "SELECT COUNT(*) FROM watchlist WHERE user_id = ?",
            (DEFAULT_USER_ID,),
        )
        watch_count = (await watch_cursor.fetchone())[0]

    assert users_count == 1
    assert watch_count == 10


async def test_init_db_preserves_existing_data(temp_db: Path) -> None:
    await init_db()

    async with aiosqlite.connect(temp_db) as conn:
        await conn.execute(
            "UPDATE users_profile SET cash_balance = ? WHERE id = ?",
            (5000.0, DEFAULT_USER_ID),
        )
        await conn.commit()

    await init_db()

    async with aiosqlite.connect(temp_db) as conn:
        cursor = await conn.execute(
            "SELECT cash_balance FROM users_profile WHERE id = ?",
            (DEFAULT_USER_ID,),
        )
        row = await cursor.fetchone()

    assert row[0] == pytest.approx(5000.0)


async def test_get_connection_yields_working_connection(temp_db: Path) -> None:
    await init_db()

    async with get_connection() as conn:
        cursor = await conn.execute("SELECT id, cash_balance FROM users_profile")
        row = await cursor.fetchone()

    assert row is not None
    assert row["id"] == DEFAULT_USER_ID
    assert row["cash_balance"] == pytest.approx(DEFAULT_CASH_BALANCE)


async def test_get_connection_commits_on_exit(temp_db: Path) -> None:
    await init_db()

    async with get_connection() as conn:
        await conn.execute(
            "UPDATE users_profile SET cash_balance = ? WHERE id = ?",
            (1234.0, DEFAULT_USER_ID),
        )

    async with aiosqlite.connect(temp_db) as conn:
        cursor = await conn.execute(
            "SELECT cash_balance FROM users_profile WHERE id = ?",
            (DEFAULT_USER_ID,),
        )
        row = await cursor.fetchone()

    assert row[0] == pytest.approx(1234.0)


async def test_watchlist_unique_constraint(temp_db: Path) -> None:
    await init_db()

    with pytest.raises(aiosqlite.IntegrityError):
        async with get_connection() as conn:
            await conn.execute(
                "INSERT INTO watchlist (id, user_id, ticker, added_at) "
                "VALUES (?, ?, ?, ?)",
                ("dup-1", DEFAULT_USER_ID, "AAPL", "2026-01-01T00:00:00+00:00"),
            )


async def test_positions_unique_constraint(temp_db: Path) -> None:
    await init_db()

    async with get_connection() as conn:
        await conn.execute(
            "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("pos-1", DEFAULT_USER_ID, "AAPL", 10.0, 150.0, "2026-01-01T00:00:00+00:00"),
        )

    with pytest.raises(aiosqlite.IntegrityError):
        async with get_connection() as conn:
            await conn.execute(
                "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                ("pos-2", DEFAULT_USER_ID, "AAPL", 5.0, 160.0, "2026-01-02T00:00:00+00:00"),
            )


async def test_trades_side_check_constraint(temp_db: Path) -> None:
    await init_db()

    with pytest.raises(aiosqlite.IntegrityError):
        async with get_connection() as conn:
            await conn.execute(
                "INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("t-1", DEFAULT_USER_ID, "AAPL", "hold", 1.0, 190.0, "2026-01-01T00:00:00+00:00"),
            )


async def test_chat_messages_role_check_constraint(temp_db: Path) -> None:
    await init_db()

    with pytest.raises(aiosqlite.IntegrityError):
        async with get_connection() as conn:
            await conn.execute(
                "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                ("m-1", DEFAULT_USER_ID, "system", "hi", None, "2026-01-01T00:00:00+00:00"),
            )
