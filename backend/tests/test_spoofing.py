"""
Unit tests for app.services.spoofing (AISAnomalyDetector).
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.services.spoofing import AISAnomalyDetector
from app.utils.geo import haversine_distance


class _FakePosition:
    def __init__(self, time, lat, lon):
        self.time = time
        self.latitude = lat
        self.longitude = lon


@pytest.mark.asyncio
class TestSpeedSpoofingDetection:
    async def test_normal_speed_no_anomaly(self):
        t0 = datetime(2026, 8, 26, 12, 0, 0, tzinfo=timezone.utc)
        # 10 nautical miles in 1 hour (~10 knots)
        p1 = _FakePosition(t0, 1.0, 103.0)
        p2 = _FakePosition(t0 + timedelta(hours=1), 1.15, 103.0)

        db = AsyncMock()
        exec_res = MagicMock()
        exec_res.scalars.return_value.all.return_value = [p1, p2]
        db.execute = AsyncMock(return_value=exec_res)

        detector = AISAnomalyDetector(db)
        anomalies = await detector.detect_speed_spoofing(mmsi=123456789, max_speed_knots=50.0)
        assert len(anomalies) == 0

    async def test_impossible_speed_jump_detected(self):
        t0 = datetime(2026, 8, 26, 12, 0, 0, tzinfo=timezone.utc)
        # 500 km in 10 minutes (~1600 knots)
        p1 = _FakePosition(t0, 1.0, 103.0)
        p2 = _FakePosition(t0 + timedelta(minutes=10), 5.0, 105.0)

        db = AsyncMock()
        exec_res = MagicMock()
        exec_res.scalars.return_value.all.return_value = [p1, p2]
        db.execute = AsyncMock(return_value=exec_res)

        detector = AISAnomalyDetector(db)
        anomalies = await detector.detect_speed_spoofing(mmsi=123456789, max_speed_knots=50.0)
        assert len(anomalies) == 1
        assert anomalies[0]["type"] == "impossible_speed"
        assert anomalies[0]["calculated_speed_knots"] > 50.0

    async def test_null_coordinates_skipped_safely(self):
        t0 = datetime(2026, 8, 26, 12, 0, 0, tzinfo=timezone.utc)
        p1 = _FakePosition(t0, None, 103.0)
        p2 = _FakePosition(t0 + timedelta(minutes=10), 5.0, 105.0)

        db = AsyncMock()
        exec_res = MagicMock()
        exec_res.scalars.return_value.all.return_value = [p1, p2]
        db.execute = AsyncMock(return_value=exec_res)

        detector = AISAnomalyDetector(db)
        anomalies = await detector.detect_speed_spoofing(mmsi=123456789, max_speed_knots=50.0)
        assert len(anomalies) == 0
