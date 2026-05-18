"""Shared fixtures for route tests.

Each test gets a fresh app with:
- A temp SQLite DB (FINALLY_DB_PATH env override + init_db seed)
- A real PriceCache pre-populated with prices for the seeded watchlist
- A stubbed market_source (records add/remove calls; never starts real tasks)
"""

from __future__ import annotations

from pathlib import Path

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.db import init_db
from app.market import PriceCache
from app.routes import chat as chat_router
from app.routes import portfolio as portfolio_router
from app.routes import watchlist as watchlist_router


class StubMarketSource:
    """No-op market source that records ticker management calls."""

    def __init__(self) -> None:
        self.added: list[str] = []
        self.removed: list[str] = []

    async def add_ticker(self, ticker: str) -> None:
        self.added.append(ticker)

    async def remove_ticker(self, ticker: str) -> None:
        self.removed.append(ticker)

    async def start(self, tickers: list[str]) -> None:  # pragma: no cover
        pass

    async def stop(self) -> None:  # pragma: no cover
        pass

    def get_tickers(self) -> list[str]:  # pragma: no cover
        return []


SEEDED_TICKERS = ("AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX")
SEED_PRICE_MAP = {t: 100.0 + i * 10 for i, t in enumerate(SEEDED_TICKERS)}


@pytest_asyncio.fixture
async def app_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Yield (app, client) with an initialized temp DB and seeded price cache.

    Does NOT use the production `lifespan`; we wire app.state manually so tests
    are deterministic and don't start the simulator background task.
    """
    db_file = tmp_path / "test_finally.db"
    monkeypatch.setenv("FINALLY_DB_PATH", str(db_file))

    await init_db()

    price_cache = PriceCache()
    for ticker, price in SEED_PRICE_MAP.items():
        price_cache.update(ticker=ticker, price=price)

    market_source = StubMarketSource()

    app = FastAPI()
    app.state.price_cache = price_cache
    app.state.market_source = market_source

    app.include_router(portfolio_router.router, prefix="/api")
    app.include_router(watchlist_router.router, prefix="/api")
    app.include_router(chat_router.router, prefix="/api")

    @app.get("/api/health")
    async def health() -> dict:
        return {"status": "ok"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield app, client, market_source
