"""
Unit tests for ownership router endpoints.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from app.main import create_app


@pytest.mark.asyncio
async def test_get_ownership_graph_not_found():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/ownership/vessel/999999999")
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_entity_not_found():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/ownership/entity/999999999")
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()
