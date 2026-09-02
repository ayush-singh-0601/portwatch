"""
Unit tests for vessels router endpoints and search queries.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from app.main import create_app
from app.routers.vessels import _escape_like


def test_escape_like_helper():
    assert _escape_like("100%") == "100\\%"
    assert _escape_like("Vessel_A") == "Vessel\\_A"
    assert _escape_like("Back\\slash") == "Back\\\\slash"
    assert _escape_like("Normal Name") == "Normal Name"


@pytest.mark.asyncio
async def test_get_vessel_not_found():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/vessels/999999999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_vessels_pagination_validation():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Invalid per_page > 100
        res = await client.get("/api/vessels?per_page=500")
        assert res.status_code == 422  # validation error
