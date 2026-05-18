"""Tests for portfolio + trade endpoints."""

from __future__ import annotations


async def test_get_portfolio_initial_shape(app_client) -> None:
    _, client, _ = app_client
    response = await client.get("/api/portfolio")
    assert response.status_code == 200
    data = response.json()

    assert data["cash_balance"] == 10000.0
    assert data["positions"] == []
    assert data["total_value"] == 10000.0
    assert data["total_pnl"] == 0.0


async def test_buy_creates_position_and_decreases_cash(app_client) -> None:
    _, client, _ = app_client
    response = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 5, "side": "buy"},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["cash_balance"] == 10000.0 - 5 * 100.0  # AAPL seeded at $100
    assert len(data["positions"]) == 1
    pos = data["positions"][0]
    assert pos["ticker"] == "AAPL"
    assert pos["quantity"] == 5
    assert pos["avg_cost"] == 100.0


async def test_buy_then_buy_more_averages_cost(app_client) -> None:
    _, client, _ = app_client
    # First buy at $100 (seeded), then mutate the cache so the second buy
    # happens at a different price.
    app, _, _ = app_client
    await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 10, "side": "buy"},
    )

    app.state.price_cache.update(ticker="AAPL", price=120.0)

    response = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 10, "side": "buy"},
    )
    assert response.status_code == 200
    pos = next(p for p in response.json()["positions"] if p["ticker"] == "AAPL")
    # Avg = (10*100 + 10*120) / 20 = 110
    assert pos["avg_cost"] == 110.0
    assert pos["quantity"] == 20


async def test_buy_with_insufficient_cash_returns_400(app_client) -> None:
    _, client, _ = app_client
    response = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 1_000_000, "side": "buy"},
    )
    assert response.status_code == 400
    assert "Insufficient cash" in response.json()["detail"]


async def test_buy_unknown_ticker_returns_400(app_client) -> None:
    _, client, _ = app_client
    response = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "ZZZZ", "quantity": 1, "side": "buy"},
    )
    # Either "no price" (cache miss) or "not in watchlist". With our seeded
    # cache only the 10 default tickers are present, so we get "no price" first.
    assert response.status_code == 400


async def test_sell_decreases_position_and_increases_cash(app_client) -> None:
    _, client, _ = app_client
    await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 10, "side": "buy"},
    )
    response = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 4, "side": "sell"},
    )
    assert response.status_code == 200
    data = response.json()
    pos = next(p for p in data["positions"] if p["ticker"] == "AAPL")
    assert pos["quantity"] == 6
    # Bought 10 at 100 = -1000, sold 4 at 100 = +400 -> net cash 9400
    assert data["cash_balance"] == 9400.0


async def test_sell_full_position_removes_row(app_client) -> None:
    _, client, _ = app_client
    await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 3, "side": "buy"},
    )
    response = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 3, "side": "sell"},
    )
    assert response.status_code == 200
    assert response.json()["positions"] == []


async def test_sell_more_than_owned_returns_400(app_client) -> None:
    _, client, _ = app_client
    response = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 1, "side": "sell"},
    )
    assert response.status_code == 400


async def test_invalid_side_returns_422(app_client) -> None:
    _, client, _ = app_client
    response = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 1, "side": "hold"},
    )
    assert response.status_code == 422


async def test_side_invalid_keyword_returns_422_not_500(app_client) -> None:
    """E2E contract: 'invalid' must surface as 422, not bleed through to a DB CHECK 500."""
    _, client, _ = app_client
    response = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 1, "side": "invalid"},
    )
    assert response.status_code == 422


async def test_trade_returns_full_portfolio_shape(app_client) -> None:
    """E2E contract: trade response shape == GET /api/portfolio shape."""
    _, client, _ = app_client
    response = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 2, "side": "buy"},
    )
    assert response.status_code == 200
    data = response.json()
    assert {"cash_balance", "positions", "total_value", "total_pnl"} <= set(data.keys())
    assert isinstance(data["positions"], list)


async def test_zero_quantity_returns_422(app_client) -> None:
    _, client, _ = app_client
    response = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 0, "side": "buy"},
    )
    assert response.status_code == 422


async def test_history_is_bare_array(app_client) -> None:
    """E2E contract: GET /api/portfolio/history returns a JSON array, not an object."""
    _, client, _ = app_client
    response = await client.get("/api/portfolio/history")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


async def test_portfolio_history_records_trade_snapshots(app_client) -> None:
    _, client, _ = app_client
    history_before = (await client.get("/api/portfolio/history")).json()
    assert history_before == []

    await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 2, "side": "buy"},
    )

    history_after = (await client.get("/api/portfolio/history")).json()
    assert len(history_after) == 1
    snapshot = history_after[0]
    assert "total_value" in snapshot
    assert "recorded_at" in snapshot


async def test_pnl_reflects_price_movement(app_client) -> None:
    app, client, _ = app_client
    await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "quantity": 10, "side": "buy"},
    )
    # AAPL was $100; bump to $110
    app.state.price_cache.update(ticker="AAPL", price=110.0)

    data = (await client.get("/api/portfolio")).json()
    pos = next(p for p in data["positions"] if p["ticker"] == "AAPL")
    assert pos["current_price"] == 110.0
    assert pos["unrealized_pnl"] == (110.0 - 100.0) * 10
    assert data["total_pnl"] == 100.0
