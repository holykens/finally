"""Tests for watchlist endpoints."""

from __future__ import annotations


async def test_get_watchlist_returns_seeded_tickers(app_client) -> None:
    _, client, _ = app_client
    response = await client.get("/api/watchlist")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)  # E2E contract: bare array, not wrapped object

    tickers = [item["ticker"] for item in data]
    assert set(tickers) == {
        "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA",
        "NVDA", "META", "JPM", "V", "NFLX",
    }
    # Every entry should carry the live price from the cache
    for item in data:
        assert item["price"] is not None
        assert "direction" in item


async def test_add_ticker_succeeds(app_client) -> None:
    _, client, market_source = app_client
    response = await client.post("/api/watchlist", json={"ticker": "pypl"})
    assert response.status_code == 201
    body = response.json()
    assert body["ticker"] == "PYPL"

    # The market source should have been told about the new ticker
    assert "PYPL" in market_source.added

    # Subsequent GET should include the new ticker
    listing = (await client.get("/api/watchlist")).json()
    assert "PYPL" in [item["ticker"] for item in listing]


async def test_add_ticker_duplicate_returns_409(app_client) -> None:
    _, client, _ = app_client
    response = await client.post("/api/watchlist", json={"ticker": "AAPL"})
    assert response.status_code == 409


async def test_add_ticker_rejects_empty(app_client) -> None:
    _, client, _ = app_client
    response = await client.post("/api/watchlist", json={"ticker": "   "})
    assert response.status_code == 422


async def test_remove_ticker_succeeds(app_client) -> None:
    _, client, market_source = app_client
    response = await client.delete("/api/watchlist/AAPL")
    assert response.status_code == 204
    assert "AAPL" in market_source.removed

    listing = (await client.get("/api/watchlist")).json()
    assert "AAPL" not in [item["ticker"] for item in listing]


async def test_remove_ticker_uppercases_input(app_client) -> None:
    _, client, market_source = app_client
    response = await client.delete("/api/watchlist/googl")
    assert response.status_code == 204
    assert "GOOGL" in market_source.removed
