"""
Unit tests for app.routers.sanctions.
"""

from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi import HTTPException

from app.routers.sanctions import get_sanctions, screen_vessel


@pytest.mark.asyncio
class TestSanctionsRouter:
    async def test_get_sanctions_404_for_missing_vessel(self):
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: None))
        with pytest.raises(HTTPException) as exc_info:
            await get_sanctions(9999999, db=db)
        assert exc_info.value.status_code == 404

    async def test_screen_vessel_404_for_missing_vessel(self):
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: None))
        with pytest.raises(HTTPException) as exc_info:
            await screen_vessel(9999999, db=db)
        assert exc_info.value.status_code == 404
