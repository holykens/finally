"""Chat endpoint: routes a user message to the LLM and auto-executes any
trades or watchlist changes it returns.

The LLM is wired in :mod:`app.llm.client`. This module is responsible for
gathering portfolio + conversation context, dispatching to the LLM, applying
the side effects it requests (trades, watchlist adds/removes), and persisting
the conversation to the ``chat_messages`` table.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.db.database import get_connection
from app.llm import ChatResponse, generate_chat_response
from app.routes.portfolio import TradeRequest, execute_trade, get_portfolio_data
from app.routes.watchlist import AddTickerRequest, add_ticker, remove_ticker

router = APIRouter()

HISTORY_LIMIT = 20

SYSTEM_PROMPT = (
    "You are FinAlly, an AI trading assistant for a simulated trading "
    "workstation with $10,000 in virtual money.\n"
    "Help users analyze their portfolio, suggest trades, and execute them on "
    "request.\n"
    "Always respond with valid JSON matching exactly this schema:\n"
    "{\n"
    '  "message": "your conversational response to the user",\n'
    '  "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 10}],\n'
    '  "watchlist_changes": [{"ticker": "PYPL", "action": "add"}]\n'
    "}\n"
    "The trades and watchlist_changes arrays should be empty [] if no action "
    "is needed.\n"
    "Be concise, data-driven, and helpful. Use real financial reasoning."
)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)


async def _load_history(limit: int = HISTORY_LIMIT) -> list[dict[str, str]]:
    """Return the most recent ``limit`` chat messages in chronological order."""
    async with get_connection() as conn:
        rows = await (
            await conn.execute(
                "SELECT role, content FROM chat_messages "
                "WHERE user_id='default' ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
        ).fetchall()
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]


def _format_portfolio_context(portfolio: dict, watchlist: list[dict]) -> str:
    """Render the portfolio + watchlist as a compact textual block for the LLM."""
    lines: list[str] = []
    lines.append(f"Cash balance: ${portfolio['cash_balance']:.2f}")
    lines.append(f"Total portfolio value: ${portfolio['total_value']:.2f}")
    lines.append(f"Total unrealized P&L: ${portfolio['total_pnl']:.2f}")

    if portfolio["positions"]:
        lines.append("Positions:")
        for p in portfolio["positions"]:
            lines.append(
                f"  - {p['ticker']}: qty={p['quantity']} avg_cost=${p['avg_cost']:.2f} "
                f"current=${p['current_price']:.2f} "
                f"pnl=${p['unrealized_pnl']:.2f} ({p['pnl_pct']:.2f}%)"
            )
    else:
        lines.append("Positions: (none)")

    if watchlist:
        lines.append("Watchlist:")
        for w in watchlist:
            price = w.get("price")
            price_str = f"${price:.2f}" if price is not None else "n/a"
            lines.append(f"  - {w['ticker']}: {price_str}")
    else:
        lines.append("Watchlist: (empty)")

    return "\n".join(lines)


async def _load_watchlist_with_prices(price_cache) -> list[dict]:
    async with get_connection() as conn:
        rows = await (
            await conn.execute(
                "SELECT ticker FROM watchlist WHERE user_id='default' ORDER BY added_at"
            )
        ).fetchall()
    out: list[dict] = []
    for row in rows:
        ticker = row[0]
        update = price_cache.get(ticker)
        out.append({"ticker": ticker, "price": update.price if update else None})
    return out


async def _store_messages(
    user_message: str, assistant_message: str, actions_json: str | None
) -> None:
    """Append a (user, assistant) turn to the chat_messages table."""
    now = datetime.now(timezone.utc).isoformat()
    async with get_connection() as conn:
        await conn.execute(
            "INSERT INTO chat_messages VALUES (?,?,?,?,?,?)",
            (str(uuid.uuid4()), "default", "user", user_message, None, now),
        )
        await conn.execute(
            "INSERT INTO chat_messages VALUES (?,?,?,?,?,?)",
            (
                str(uuid.uuid4()),
                "default",
                "assistant",
                assistant_message,
                actions_json,
                now,
            ),
        )
        await conn.commit()


async def _auto_execute_trade(
    trade: dict[str, Any], request: Request
) -> tuple[dict[str, Any] | None, str | None]:
    """Run a single LLM-proposed trade through the portfolio trade path.

    Returns ``(executed_trade, error)``. Exactly one of the two is non-None.
    """
    try:
        ticker = str(trade.get("ticker", "")).upper().strip()
        side = str(trade.get("side", "")).lower().strip()
        quantity = float(trade.get("quantity", 0))
    except (TypeError, ValueError) as exc:
        return None, f"Invalid trade payload: {exc}"

    if side not in ("buy", "sell"):
        return None, f"Invalid side {side!r} for {ticker}"
    if quantity <= 0:
        return None, f"Invalid quantity {quantity} for {ticker}"

    try:
        body = TradeRequest(ticker=ticker, quantity=quantity, side=side)
        await execute_trade(body, request)
    except HTTPException as exc:
        return None, f"Trade {side} {quantity} {ticker} failed: {exc.detail}"
    except Exception as exc:  # pragma: no cover - defensive
        return None, f"Trade {side} {quantity} {ticker} errored: {exc}"

    price_cache = request.app.state.price_cache
    price = price_cache.get_price(ticker)
    return (
        {"ticker": ticker, "side": side, "quantity": quantity, "price": price},
        None,
    )


async def _auto_execute_watchlist_change(
    change: dict[str, Any], request: Request
) -> tuple[dict[str, Any] | None, str | None]:
    """Apply a single LLM-proposed watchlist change."""
    ticker = str(change.get("ticker", "")).upper().strip()
    action = str(change.get("action", "")).lower().strip()

    if not ticker:
        return None, "Watchlist change missing ticker"
    if action not in ("add", "remove"):
        return None, f"Invalid watchlist action {action!r}"

    try:
        if action == "add":
            await add_ticker(AddTickerRequest(ticker=ticker), request)
        else:
            await remove_ticker(ticker, request)
    except HTTPException as exc:
        return None, f"Watchlist {action} {ticker} failed: {exc.detail}"
    except Exception as exc:  # pragma: no cover - defensive
        return None, f"Watchlist {action} {ticker} errored: {exc}"

    return {"ticker": ticker, "action": action}, None


@router.post("/chat")
async def chat(body: ChatRequest, request: Request) -> dict:
    user_message = body.message

    price_cache = request.app.state.price_cache
    portfolio = await get_portfolio_data(price_cache)
    watchlist = await _load_watchlist_with_prices(price_cache)
    history = await _load_history()

    context_block = _format_portfolio_context(portfolio, watchlist)

    messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.append(
        {"role": "system", "content": f"Current portfolio context:\n{context_block}"}
    )
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    llm_response: ChatResponse = await generate_chat_response(messages)

    executed_trades: list[dict[str, Any]] = []
    errors: list[str] = []

    for trade in llm_response.trades:
        executed, err = await _auto_execute_trade(trade, request)
        if executed is not None:
            executed_trades.append(executed)
        if err is not None:
            errors.append(err)

    applied_watchlist_changes: list[dict[str, Any]] = []
    for change in llm_response.watchlist_changes:
        applied, err = await _auto_execute_watchlist_change(change, request)
        if applied is not None:
            applied_watchlist_changes.append(applied)
        if err is not None:
            errors.append(err)

    actions_payload = {
        "executed_trades": executed_trades,
        "watchlist_changes": applied_watchlist_changes,
        "errors": errors,
    }
    actions_json = (
        json.dumps(actions_payload)
        if (executed_trades or applied_watchlist_changes or errors)
        else None
    )
    await _store_messages(user_message, llm_response.message, actions_json)

    return {
        "message": llm_response.message,
        "trades": llm_response.trades,
        "watchlist_changes": llm_response.watchlist_changes,
        "executed_trades": executed_trades,
        "errors": errors,
    }
