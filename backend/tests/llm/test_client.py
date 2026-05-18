"""Unit tests for app.llm.client.

These exercise the mock-mode path and the JSON parsing helpers without hitting
the network. The live LiteLLM call path is intentionally not covered here —
it's covered indirectly by the route tests and would require either real
credentials or substantial mocking of the LiteLLM SDK.
"""

from __future__ import annotations

import pytest

from app.llm.client import (
    MOCK_RESPONSE_TEXT,
    ChatResponse,
    _parse_llm_content,
    generate_chat_response,
)


@pytest.fixture(autouse=True)
def _mock_mode(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("LLM_MOCK", "true")


async def test_mock_mode_returns_canned_message() -> None:
    response = await generate_chat_response(
        [{"role": "user", "content": "hello"}]
    )
    assert isinstance(response, ChatResponse)
    assert response.message == MOCK_RESPONSE_TEXT
    assert response.trades == []
    assert response.watchlist_changes == []


async def test_mock_mode_detects_buy_intent() -> None:
    response = await generate_chat_response(
        [{"role": "user", "content": "please buy AAPL"}]
    )
    assert response.trades == [{"ticker": "AAPL", "side": "buy", "quantity": 1}]


async def test_mock_mode_detects_watchlist_add() -> None:
    response = await generate_chat_response(
        [{"role": "user", "content": "add PYPL to my watchlist"}]
    )
    assert response.watchlist_changes == [{"ticker": "PYPL", "action": "add"}]


def test_parse_llm_content_plain_json() -> None:
    raw = '{"message": "hi", "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 2.5}], "watchlist_changes": []}'
    parsed = _parse_llm_content(raw)
    assert parsed.message == "hi"
    assert parsed.trades == [{"ticker": "AAPL", "side": "buy", "quantity": 2.5}]
    assert parsed.watchlist_changes == []


def test_parse_llm_content_strips_markdown_fence() -> None:
    raw = '```json\n{"message": "hi", "trades": [], "watchlist_changes": []}\n```'
    parsed = _parse_llm_content(raw)
    assert parsed.message == "hi"
    assert parsed.trades == []
    assert parsed.watchlist_changes == []


def test_parse_llm_content_handles_malformed_json() -> None:
    parsed = _parse_llm_content("not valid json at all")
    assert "not valid json" in parsed.message
    assert parsed.trades == []
    assert parsed.watchlist_changes == []


def test_parse_llm_content_handles_empty_string() -> None:
    parsed = _parse_llm_content("")
    assert parsed.message
    assert parsed.trades == []
    assert parsed.watchlist_changes == []
