"""FinAlly FastAPI application entry point."""

from __future__ import annotations

import asyncio
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

# Load .env from project root before importing modules that read env vars.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from app.db import get_connection, init_db  # noqa: E402
from app.market import PriceCache, create_market_data_source, create_stream_router  # noqa: E402
from app.routes import chat as chat_router  # noqa: E402
from app.routes import portfolio as portfolio_router  # noqa: E402
from app.routes import watchlist as watchlist_router  # noqa: E402

# Single shared PriceCache instance for the app lifetime.
# Created at module scope so the SSE router (which closes over it) can be
# registered before app startup.
price_cache = PriceCache()


async def _snapshot_loop(app: FastAPI) -> None:
    """Background task: write a portfolio snapshot every 30 seconds."""
    while True:
        try:
            await asyncio.sleep(30)
            async with get_connection() as conn:
                cash_row = await (
                    await conn.execute(
                        "SELECT cash_balance FROM users_profile WHERE id='default'"
                    )
                ).fetchone()
                cash = cash_row[0] if cash_row else 10000.0
                pos_rows = await (
                    await conn.execute(
                        "SELECT ticker, quantity FROM positions WHERE user_id='default'"
                    )
                ).fetchall()
                total = cash + sum(
                    (app.state.price_cache.get_price(row[0]) or 0) * row[1]
                    for row in pos_rows
                )
                now = datetime.now(timezone.utc).isoformat()
                await conn.execute(
                    "INSERT INTO portfolio_snapshots VALUES (?,?,?,?)",
                    (str(uuid.uuid4()), "default", total, now),
                )
                await conn.commit()
        except asyncio.CancelledError:
            raise
        except Exception:
            # Don't let a snapshot failure kill the loop.
            pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    async with get_connection() as conn:
        rows = await (
            await conn.execute(
                "SELECT ticker FROM watchlist WHERE user_id='default'"
            )
        ).fetchall()
        tickers = [r[0] for r in rows]

    source = create_market_data_source(price_cache)
    await source.start(tickers)

    app.state.price_cache = price_cache
    app.state.market_source = source

    snapshot_task = asyncio.create_task(_snapshot_loop(app), name="snapshot-loop")

    try:
        yield
    finally:
        snapshot_task.cancel()
        try:
            await snapshot_task
        except (asyncio.CancelledError, Exception):
            pass
        await source.stop()


app = FastAPI(title="FinAlly", lifespan=lifespan)

# create_stream_router bakes in prefix="/api/stream"; include without extra prefix.
app.include_router(create_stream_router(price_cache))
app.include_router(portfolio_router.router, prefix="/api")
app.include_router(watchlist_router.router, prefix="/api")
app.include_router(chat_router.router, prefix="/api")


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
