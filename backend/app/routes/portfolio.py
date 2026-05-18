"""Portfolio REST endpoints: positions, trade execution, value history."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.db.database import get_connection

router = APIRouter()


class TradeRequest(BaseModel):
    ticker: str = Field(..., min_length=1)
    quantity: float = Field(..., gt=0)
    side: Literal["buy", "sell"]


async def get_portfolio_data(price_cache) -> dict:
    """Compute the user's full portfolio view from DB + live price cache."""
    async with get_connection() as conn:
        cash_row = await (
            await conn.execute(
                "SELECT cash_balance FROM users_profile WHERE id='default'"
            )
        ).fetchone()
        cash = cash_row[0] if cash_row else 10000.0
        pos_rows = await (
            await conn.execute(
                "SELECT ticker, quantity, avg_cost FROM positions WHERE user_id='default'"
            )
        ).fetchall()

    positions = []
    total_pos_value = 0.0
    for row in pos_rows:
        ticker, qty, avg_cost = row[0], row[1], row[2]
        price = price_cache.get_price(ticker) or avg_cost
        market_value = qty * price
        unrealized_pnl = (price - avg_cost) * qty
        pnl_pct = ((price - avg_cost) / avg_cost * 100) if avg_cost > 0 else 0.0
        total_pos_value += market_value
        positions.append(
            {
                "ticker": ticker,
                "quantity": qty,
                "avg_cost": avg_cost,
                "current_price": price,
                "market_value": market_value,
                "unrealized_pnl": unrealized_pnl,
                "pnl_pct": pnl_pct,
            }
        )

    total_value = cash + total_pos_value
    total_pnl = sum(p["unrealized_pnl"] for p in positions)
    return {
        "cash_balance": cash,
        "positions": positions,
        "total_value": total_value,
        "total_pnl": total_pnl,
    }


@router.get("/portfolio")
async def get_portfolio(request: Request) -> dict:
    return await get_portfolio_data(request.app.state.price_cache)


@router.post("/portfolio/trade")
async def execute_trade(body: TradeRequest, request: Request) -> dict:
    ticker = body.ticker.upper().strip()
    quantity = body.quantity
    side = body.side  # Already validated to "buy" | "sell" by Pydantic

    if not ticker:
        raise HTTPException(status_code=422, detail="ticker cannot be empty")

    price_cache = request.app.state.price_cache
    price = price_cache.get_price(ticker)
    if not price:
        raise HTTPException(status_code=400, detail=f"No price available for {ticker}")

    now = datetime.now(timezone.utc).isoformat()

    async with get_connection() as conn:
        wl = await (
            await conn.execute(
                "SELECT ticker FROM watchlist WHERE user_id='default' AND ticker=?",
                (ticker,),
            )
        ).fetchone()
        if not wl:
            raise HTTPException(
                status_code=400, detail=f"{ticker} is not in your watchlist"
            )

        cash_row = await (
            await conn.execute(
                "SELECT cash_balance FROM users_profile WHERE id='default'"
            )
        ).fetchone()
        cash = cash_row[0]

        if side == "buy":
            cost = quantity * price
            if cost > cash:
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient cash: need ${cost:.2f}, have ${cash:.2f}",
                )
            existing = await (
                await conn.execute(
                    "SELECT quantity, avg_cost FROM positions WHERE user_id='default' AND ticker=?",
                    (ticker,),
                )
            ).fetchone()
            if existing:
                new_qty = existing[0] + quantity
                new_avg = (existing[0] * existing[1] + quantity * price) / new_qty
                await conn.execute(
                    "UPDATE positions SET quantity=?, avg_cost=?, updated_at=? "
                    "WHERE user_id='default' AND ticker=?",
                    (new_qty, new_avg, now, ticker),
                )
            else:
                await conn.execute(
                    "INSERT INTO positions VALUES (?,?,?,?,?,?)",
                    (str(uuid.uuid4()), "default", ticker, quantity, price, now),
                )
            await conn.execute(
                "UPDATE users_profile SET cash_balance=? WHERE id='default'",
                (cash - cost,),
            )

        else:  # sell
            existing = await (
                await conn.execute(
                    "SELECT quantity FROM positions WHERE user_id='default' AND ticker=?",
                    (ticker,),
                )
            ).fetchone()
            if not existing or existing[0] < quantity - 0.0001:
                have = existing[0] if existing else 0
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient shares: need {quantity}, have {have:.4f}",
                )
            new_qty = existing[0] - quantity
            if new_qty < 0.0001:
                await conn.execute(
                    "DELETE FROM positions WHERE user_id='default' AND ticker=?",
                    (ticker,),
                )
            else:
                await conn.execute(
                    "UPDATE positions SET quantity=?, updated_at=? "
                    "WHERE user_id='default' AND ticker=?",
                    (new_qty, now, ticker),
                )
            await conn.execute(
                "UPDATE users_profile SET cash_balance=? WHERE id='default'",
                (cash + quantity * price,),
            )

        await conn.execute(
            "INSERT INTO trades VALUES (?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), "default", ticker, side, quantity, price, now),
        )

        portfolio = await get_portfolio_data(price_cache)
        await conn.execute(
            "INSERT INTO portfolio_snapshots VALUES (?,?,?,?)",
            (str(uuid.uuid4()), "default", portfolio["total_value"], now),
        )

        await conn.commit()

    return await get_portfolio_data(price_cache)


@router.get("/portfolio/history")
async def portfolio_history() -> list[dict]:
    async with get_connection() as conn:
        rows = await (
            await conn.execute(
                "SELECT total_value, recorded_at FROM portfolio_snapshots "
                "WHERE user_id='default' ORDER BY recorded_at ASC LIMIT 500"
            )
        ).fetchall()
    return [{"total_value": r[0], "recorded_at": r[1]} for r in rows]
