"""Watchlist REST endpoints: list, add, remove tickers."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import aiosqlite
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.db.database import get_connection

router = APIRouter()


class AddTickerRequest(BaseModel):
    ticker: str = Field(..., min_length=1)


@router.get("/watchlist")
async def get_watchlist(request: Request) -> list[dict]:
    async with get_connection() as conn:
        rows = await (
            await conn.execute(
                "SELECT ticker FROM watchlist WHERE user_id='default' ORDER BY added_at"
            )
        ).fetchall()
    price_cache = request.app.state.price_cache
    result: list[dict] = []
    for row in rows:
        ticker = row[0]
        update = price_cache.get(ticker)
        result.append(
            {
                "ticker": ticker,
                "price": update.price if update else None,
                "previous_price": update.previous_price if update else None,
                "direction": update.direction if update else "flat",
            }
        )
    return result


@router.post("/watchlist", status_code=201)
async def add_ticker(body: AddTickerRequest, request: Request) -> dict:
    ticker = body.ticker.upper().strip()
    if not ticker:
        raise HTTPException(status_code=422, detail="ticker cannot be empty")

    now = datetime.now(timezone.utc).isoformat()
    async with get_connection() as conn:
        existing = await (
            await conn.execute(
                "SELECT ticker FROM watchlist WHERE user_id='default' AND ticker=?",
                (ticker,),
            )
        ).fetchone()
        if existing:
            raise HTTPException(
                status_code=409, detail=f"{ticker} is already in your watchlist"
            )
        try:
            await conn.execute(
                "INSERT INTO watchlist VALUES (?,?,?,?)",
                (str(uuid.uuid4()), "default", ticker, now),
            )
            await conn.commit()
        except aiosqlite.IntegrityError as exc:
            # UNIQUE(user_id, ticker) — race with concurrent insert.
            raise HTTPException(
                status_code=409, detail=f"{ticker} is already in your watchlist"
            ) from exc

    await request.app.state.market_source.add_ticker(ticker)

    update = request.app.state.price_cache.get(ticker)
    return {
        "ticker": ticker,
        "price": update.price if update else None,
        "direction": "flat",
    }


@router.delete("/watchlist/{ticker}", status_code=204)
async def remove_ticker(ticker: str, request: Request) -> None:
    ticker = ticker.upper().strip()
    async with get_connection() as conn:
        await conn.execute(
            "DELETE FROM watchlist WHERE user_id='default' AND ticker=?",
            (ticker,),
        )
        await conn.commit()
    await request.app.state.market_source.remove_ticker(ticker)
    return None
