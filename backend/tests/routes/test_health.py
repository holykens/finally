"""Health endpoint smoke test."""

from __future__ import annotations


async def test_health_returns_ok(app_client) -> None:
    _, client, _ = app_client
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
