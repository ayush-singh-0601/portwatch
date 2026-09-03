"""
Unit tests for the /health endpoint.
"""

from httpx import ASGITransport, AsyncClient
import pytest

from app.main import create_app


@pytest.mark.asyncio
async def test_health_check_endpoint():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "portwatch-api"
        assert "version" in data
        assert "environment" in data
