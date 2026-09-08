"""
Unit tests for positions router endpoints and bounding box validation.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from app.main import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.mark.asyncio
async def test_get_current_positions_invalid_bbox_format(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/map/positions?bbox=invalid,bbox")
        assert response.status_code == 400
        assert "Invalid bbox" in response.json()["detail"] or "bbox must be" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_current_positions_inverted_latitude(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # min_lat (50) > max_lat (20)
        response = await client.get("/api/map/positions?bbox=-10,50,10,20")
        assert response.status_code == 400
        assert "min_lat cannot be greater than max_lat" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_current_positions_out_of_range_latitude(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/map/positions?bbox=-10,-95,10,20")
        assert response.status_code == 400
        assert "Latitude must be between -90 and 90" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_positions_start_time_after_end_time(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/vessels/9241061/positions?start_time=2026-03-01T00:00:00Z&end_time=2026-02-01T00:00:00Z")
        assert response.status_code == 400
        assert "start_time cannot be after end_time" in response.json()["detail"]

