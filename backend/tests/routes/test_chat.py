"""Tests for the chat endpoint.

These tests run with ``LLM_MOCK=true`` so they never hit OpenRouter. The mock
LLM client recognizes "buy <TICKER>" / "sell <TICKER>" / "add <TICKER> to
watchlist" / "remove <TICKER> from watchlist" patterns so we can drive the
auto-execution code paths from inside the test.
"""

from __future__ import annotations

import pytest

from app.db.database import get_connection


@pytest.fixture(autouse=True)
def _enable_llm_mock(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("LLM_MOCK", "true")


async def test_chat_returns_expected_shape(app_client) -> None:
    _, client, _ = app_client
    response = await client.post("/api/chat", json={"message": "hi"})
    assert response.status_code == 200

    data = response.json()
    for key in ("message", "trades", "watchlist_changes", "executed_trades", "errors"):
        assert key in data, f"missing key {key}"

    assert isinstance(data["message"], str) and data["message"]
    assert data["trades"] == []
    assert data["watchlist_changes"] == []
    assert data["executed_trades"] == []
    assert data["errors"] == []


async def test_chat_persists_messages(app_client) -> None:
    _, client, _ = app_client
    await client.post("/api/chat", json={"message": "hello there"})

    async with get_connection() as conn:
        rows = await (
            await conn.execute(
                "SELECT role, content FROM chat_messages WHERE user_id='default' "
                "ORDER BY created_at ASC"
            )
        ).fetchall()

    roles = [r[0] for r in rows]
    contents = [r[1] for r in rows]
    assert roles == ["user", "assistant"]
    assert contents[0] == "hello there"
    assert contents[1]  # non-empty assistant response


async def test_chat_auto_executes_buy_trade(app_client) -> None:
    _, client, _ = app_client
    response = await client.post(
        "/api/chat", json={"message": "buy AAPL"}
    )
    assert response.status_code == 200
    data = response.json()

    assert data["trades"] == [
        {"ticker": "AAPL", "side": "buy", "quantity": 1}
    ]
    assert len(data["executed_trades"]) == 1
    executed = data["executed_trades"][0]
    assert executed["ticker"] == "AAPL"
    assert executed["side"] == "buy"
    assert executed["quantity"] == 1
    assert data["errors"] == []

    # And the portfolio actually changed.
    portfolio = (await client.get("/api/portfolio")).json()
    aapl = next(p for p in portfolio["positions"] if p["ticker"] == "AAPL")
    assert aapl["quantity"] == 1


async def test_chat_records_errors_for_invalid_trade(app_client) -> None:
    _, client, _ = app_client
    # We don't own any AAPL yet, so "sell AAPL" should fail validation.
    response = await client.post("/api/chat", json={"message": "sell AAPL"})
    assert response.status_code == 200
    data = response.json()
    assert data["executed_trades"] == []
    assert data["errors"], "expected at least one error for impossible sell"
    assert "AAPL" in data["errors"][0]


async def test_chat_auto_executes_watchlist_add(app_client) -> None:
    _, client, _ = app_client
    response = await client.post(
        "/api/chat", json={"message": "add PYPL to watchlist"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["watchlist_changes"] == [
        {"ticker": "PYPL", "action": "add"}
    ]
    assert data["errors"] == []

    watchlist = (await client.get("/api/watchlist")).json()
    tickers = [w["ticker"] for w in watchlist]
    assert "PYPL" in tickers


async def test_chat_empty_message_returns_422(app_client) -> None:
    _, client, _ = app_client
    response = await client.post("/api/chat", json={"message": ""})
    assert response.status_code == 422


async def test_chat_history_round_trips(app_client) -> None:
    _, client, _ = app_client
    await client.post("/api/chat", json={"message": "first message"})
    await client.post("/api/chat", json={"message": "second message"})

    async with get_connection() as conn:
        rows = await (
            await conn.execute(
                "SELECT COUNT(*) FROM chat_messages WHERE user_id='default'"
            )
        ).fetchone()
    # Two turns -> 4 rows (2 user, 2 assistant).
    assert rows[0] == 4
