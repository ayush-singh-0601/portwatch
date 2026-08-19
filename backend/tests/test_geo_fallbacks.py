"""
Unit tests for the empty-table fallback behaviour of the three geospatial
proximity methods.

Uses unittest.mock to stub out AsyncSession so no real database is needed.
Each test verifies:
  - the method does NOT crash when the ports table is empty
  - it returns the correct documented fallback value
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_empty_db() -> AsyncMock:
    """Return a minimal mock AsyncSession that simulates an empty ports table.

    - execute() returns a mock whose fetchone() / scalar() / all() all return
      empty / None results.
    """
    db = AsyncMock()
    exec_result = MagicMock()
    exec_result.fetchone.return_value = None   # no PostGIS hit
    exec_result.scalar.return_value = 0        # COUNT(*) = 0
    exec_result.all.return_value = []          # no rows
    exec_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=exec_result)
    return db


# ---------------------------------------------------------------------------
# DarkVesselDetector._is_coastal_position — empty table -> True
# ---------------------------------------------------------------------------

class TestIsCoastalPositionEmptyTable:
    @pytest.mark.asyncio
    async def test_returns_true_when_table_empty(self):
        """Empty ports table should cause _is_coastal_position to return True."""
        from app.services.dark_detection import DarkVesselDetector

        db = _make_empty_db()
        detector = DarkVesselDetector(db)

        result = await detector._is_coastal_position(0.0, 0.0)
        assert result is True

    @pytest.mark.asyncio
    async def test_logs_warning_when_table_empty(self, caplog):
        """A warning should be logged when the ports table is empty."""
        import logging
        from app.services.dark_detection import DarkVesselDetector

        db = _make_empty_db()
        detector = DarkVesselDetector(db)

        with caplog.at_level(logging.WARNING, logger="app.services.dark_detection"):
            await detector._is_coastal_position(0.0, 0.0)

        assert any("ports table is empty" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# AISAnomalyDetector._is_near_risk_zone — empty table -> False for open ocean
# ---------------------------------------------------------------------------

class TestIsNearRiskZoneEmptyTable:
    @pytest.mark.asyncio
    async def test_open_ocean_returns_false_when_table_empty(self):
        """Open ocean (0, 0) with empty ports table should return False."""
        from app.services.spoofing import AISAnomalyDetector

        db = _make_empty_db()
        detector = AISAnomalyDetector(db)

        # Gulf of Guinea — far from any ship-breaking yard or sanctioned port
        result = await detector._is_near_risk_zone(0.0, 0.0)
        assert result is False

    @pytest.mark.asyncio
    async def test_near_alang_returns_true_even_when_table_empty(self):
        """A position at Alang yard must return True even with empty ports table
        because yard coordinates are hard-coded constants."""
        from app.services.spoofing import AISAnomalyDetector

        db = _make_empty_db()
        detector = AISAnomalyDetector(db)

        # Alang, India coordinates
        result = await detector._is_near_risk_zone(21.41, 72.18)
        assert result is True


# ---------------------------------------------------------------------------
# STSTransferDetector._check_in_port_limits — empty table -> False
# ---------------------------------------------------------------------------

class TestCheckInPortLimitsEmptyTable:
    @pytest.mark.asyncio
    async def test_returns_false_when_table_empty(self):
        """Empty ports table should cause _check_in_port_limits to return False."""
        from app.services.sts_detection import STSTransferDetector

        db = _make_empty_db()
        detector = STSTransferDetector(db)

        result = await detector._check_in_port_limits(0.0, 0.0)
        assert result is False

    @pytest.mark.asyncio
    async def test_logs_warning_when_table_empty(self, caplog):
        """A warning should be logged when the ports table is empty."""
        import logging
        from app.services.sts_detection import STSTransferDetector

        db = _make_empty_db()
        detector = STSTransferDetector(db)

        with caplog.at_level(logging.WARNING, logger="app.services.sts_detection"):
            await detector._check_in_port_limits(0.0, 0.0)

        assert any("ports table is empty" in r.message for r in caplog.records)
