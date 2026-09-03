"""
Unit tests for BehaviorAnalysisAgent.
"""

from unittest.mock import AsyncMock, MagicMock
import pytest

from app.agents.behavior import BehaviorAnalysisAgent


@pytest.mark.asyncio
class TestBehaviorAnalysisAgent:
    async def test_invalid_imo_returns_empty_results(self):
        db = AsyncMock()
        agent = BehaviorAnalysisAgent(db)
        res = await agent.analyze_vessel_behavior(0, 123456789)
        assert res["dark_events_detected"] == 0
        assert res["sts_events_detected"] == 0

    async def test_missing_mmsi_returns_early(self):
        db = AsyncMock()
        agent = BehaviorAnalysisAgent(db)
        res = await agent.analyze_vessel_behavior(9123456, None)
        assert res["dark_events_detected"] == 0
        assert res["loitering_events_detected"] == 0

    async def test_valid_analysis_flow(self):
        db = AsyncMock()
        agent = BehaviorAnalysisAgent(db)
        # Mock dark detector, anomaly detector, sts detector
        agent.dark_detector.detect_dark_events = AsyncMock(return_value=[])
        agent.anomaly_detector.detect_speed_spoofing = AsyncMock(return_value=[])
        agent.anomaly_detector.detect_loitering = AsyncMock(return_value=[])
        agent.sts_detector.detect_sts_transfers = AsyncMock(return_value=[])

        res = await agent.analyze_vessel_behavior(9123456, 123456789)
        assert res["vessel_imo"] == 9123456
        assert res["dark_events_detected"] == 0
        assert res["sts_events_detected"] == 0
        db.commit.assert_awaited_once()
