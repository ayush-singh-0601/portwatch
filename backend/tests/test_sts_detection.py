"""
Unit tests for app.services.sts_detection (STSTransferDetector).
"""

from unittest.mock import AsyncMock, MagicMock
import pytest

from app.services.sts_detection import STSTransferDetector, _PORT_LIMIT_RADIUS_KM
from app.utils.geo import haversine_distance


@pytest.mark.asyncio
class TestSTSDetectionHelpers:
    async def test_null_coordinates_return_false(self):
        db = AsyncMock()
        detector = STSTransferDetector(db)
        assert await detector._check_in_port_limits(None, 103.0) is False
        assert await detector._check_in_port_limits(1.0, None) is False

    async def test_haversine_fallback_inside_port(self):
        db = AsyncMock()
        # Mock PostGIS failing (raises Exception)
        async def mock_execute(stmt, *args, **kwargs):
            # If checking ports coordinates fallback
            mock_res = MagicMock()
            mock_res.all.return_value = [(1.2644, 103.822)]  # Singapore port coords
            return mock_res

        db.execute = AsyncMock(side_effect=[Exception("PostGIS not installed"), MagicMock(all=lambda: [(1.2644, 103.822)])])

        detector = STSTransferDetector(db)
        # Position 2 km from Singapore port
        is_inside = await detector._check_in_port_limits(1.27, 103.82)
        assert is_inside is True

    async def test_haversine_fallback_outside_port(self):
        db = AsyncMock()
        # Position 50 km from port
        db.execute = AsyncMock(side_effect=[Exception("PostGIS not installed"), MagicMock(all=lambda: [(1.2644, 103.822)])])

        detector = STSTransferDetector(db)
        is_inside = await detector._check_in_port_limits(1.80, 104.20)
        assert is_inside is False

    async def test_empty_ports_table_defaults_to_false(self):
        db = AsyncMock()
        db.execute = AsyncMock(side_effect=[Exception("PostGIS not installed"), MagicMock(all=lambda: [])])
        detector = STSTransferDetector(db)
        is_inside = await detector._check_in_port_limits(1.27, 103.82)
        assert is_inside is False

