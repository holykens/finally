"""LLM client: calls OpenRouter via LiteLLM with Cerebras as the inference provider.

Supports an ``LLM_MOCK=true`` mode that returns a deterministic response without
making a network call. This mode is used by unit tests and E2E tests so they
run fast, free, and reproducibly.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

MODEL = "openrouter/openai/gpt-oss-120b"
EXTRA_BODY = {"provider": {"order": ["cerebras"]}}


class _Trade(BaseModel):
    ticker: str
    side: str
    quantity: float


class _WatchlistChange(BaseModel):
    ticker: str
    action: str


class _StructuredOutput(BaseModel):
    """Pydantic schema describing the expected LLM JSON response."""

    message: str = Field(..., description="Conversational response to the user")
    trades: list[_Trade] = Field(default_factory=list)
    watchlist_changes: list[_WatchlistChange] = Field(default_factory=list)


@dataclass
class ChatResponse:
    """Parsed LLM response.

    Always carries a ``message`` (even if the LLM returned malformed JSON we
    fall back to an apology). ``trades`` and ``watchlist_changes`` are lists of
    plain dicts so callers can pass them directly through to the trade /
    watchlist code paths.
    """

    message: str
    trades: list[dict[str, Any]] = field(default_factory=list)
    watchlist_changes: list[dict[str, Any]] = field(default_factory=list)


MOCK_RESPONSE_TEXT = (
    "I'm FinAlly, your AI trading assistant. I can see your portfolio "
    "and help you trade. What would you like to do?"
)


def _is_mock_mode() -> bool:
    return os.environ.get("LLM_MOCK", "").lower() == "true"


def _mock_response(user_message: str) -> ChatResponse:
    """Deterministic mock used when ``LLM_MOCK=true``.

    Recognizes a few keywords so tests can exercise the trade and watchlist
    auto-execution paths without needing a real LLM:

    - "buy <TICKER>" -> emits a buy trade for 1 share
    - "sell <TICKER>" -> emits a sell trade for 1 share
    - "add <TICKER> to watchlist" -> emits a watchlist add
    - "remove <TICKER>" -> emits a watchlist remove
    """
    text = user_message.lower().strip()
    trades: list[dict[str, Any]] = []
    watchlist_changes: list[dict[str, Any]] = []

    words = user_message.replace(",", " ").replace(".", " ").split()
    upper_tokens = [w.upper().strip() for w in words if w.isalpha() and w.isupper()]

    if "buy" in text and upper_tokens:
        trades.append({"ticker": upper_tokens[0], "side": "buy", "quantity": 1})
    elif "sell" in text and upper_tokens:
        trades.append({"ticker": upper_tokens[0], "side": "sell", "quantity": 1})

    if "watchlist" in text and "add" in text and upper_tokens:
        watchlist_changes.append({"ticker": upper_tokens[0], "action": "add"})
    elif "watchlist" in text and "remove" in text and upper_tokens:
        watchlist_changes.append({"ticker": upper_tokens[0], "action": "remove"})

    return ChatResponse(
        message=MOCK_RESPONSE_TEXT,
        trades=trades,
        watchlist_changes=watchlist_changes,
    )


def _parse_llm_content(content: str) -> ChatResponse:
    """Parse the LLM's structured JSON output into a ``ChatResponse``.

    Tolerates JSON wrapped in markdown fences and gracefully degrades when
    the response isn't valid JSON.
    """
    if not content:
        return ChatResponse(message="(no response from model)")

    cleaned = content.strip()
    if cleaned.startswith("```"):
        # Strip ```json ... ``` fences
        lines = cleaned.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    try:
        parsed = _StructuredOutput.model_validate_json(cleaned)
    except Exception as exc:
        logger.warning("Failed to parse LLM JSON response: %s; raw=%r", exc, content[:500])
        return ChatResponse(message=content.strip() or "(model returned malformed JSON)")

    return ChatResponse(
        message=parsed.message,
        trades=[t.model_dump() for t in parsed.trades],
        watchlist_changes=[w.model_dump() for w in parsed.watchlist_changes],
    )


async def generate_chat_response(messages: list[dict[str, str]]) -> ChatResponse:
    """Call the LLM with the given message list and return a parsed response.

    ``messages`` follows the OpenAI chat completion shape: a list of dicts with
    ``role`` and ``content`` keys.

    In mock mode the most recent user message is fed to the deterministic mock
    so tests can drive trade / watchlist behavior. In live mode the call goes
    out to OpenRouter via LiteLLM using Cerebras as the inference provider.
    """
    if _is_mock_mode():
        last_user = next(
            (m["content"] for m in reversed(messages) if m.get("role") == "user"),
            "",
        )
        return _mock_response(last_user)

    from litellm import acompletion

    try:
        response = await acompletion(
            model=MODEL,
            messages=messages,
            response_format={"type": "json_object"},
            reasoning_effort="low",
            extra_body=EXTRA_BODY,
        )
        content = response.choices[0].message.content or ""
    except Exception as exc:
        logger.exception("LLM call failed")
        return ChatResponse(
            message=f"I hit an error talking to the model: {exc}",
        )

    return _parse_llm_content(content)


__all__ = ["ChatResponse", "generate_chat_response"]
