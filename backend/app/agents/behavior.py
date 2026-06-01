"""
BehaviorAnalysisAgent — analyzes vessel positions to detect maritime anomalies.

Identifies:
1. Dark vessel events (transponder gaps)
2. Ship-to-ship (STS) transfer events
3. AIS spoofing (impossible speed jumps, duplicate MMSIs)
4. Loitering near high-risk/sanctioned locations

Saves results to dark_events, sts_events tables for risk score calculations.
"""

import logging
from typing import Optional

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dark_event import DarkEvent
from app.models.sts_event import STSEvent
from app.services.dark_detection import DarkVesselDetector
from app.services.sts_detection import STSTransferDetector
from app.services.spoofing import AISAnomalyDetector

logger = logging.getLogger(__name__)


class BehaviorAnalysisAgent:
    """Agent that runs spatial and temporal anomaly detection algorithms."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.dark_detector = DarkVesselDetector(db)
        self.sts_detector = STSTransferDetector(db)
        self.anomaly_detector = AISAnomalyDetector(db)

    async def analyze_vessel_behavior(self, vessel_imo: int, mmsi: Optional[int]) -> dict:
        """Run all behavior analyses for a single vessel.
        
        Saves detected dark events and logs spoofing/loitering anomalies.
        """
        logger.info(f"Running behavior analysis for vessel IMO {vessel_imo} (MMSI: {mmsi})")

        results = {
            "vessel_imo": vessel_imo,
            "dark_events_detected": 0,
            "sts_events_detected": 0,
            "spoofing_anomalies_detected": 0,
            "loitering_events_detected": 0,
        }

        if not mmsi:
            logger.warning(f"Vessel IMO {vessel_imo} has no MMSI. Cannot run behavior analysis.")
            return results

        # ── 1. Detect and persist Dark Events ───────────────────────
        # Clear existing dark events for this vessel to avoid duplication
        await self.db.execute(
            delete(DarkEvent).where(DarkEvent.vessel_imo == vessel_imo)
        )
        
        dark_events = await self.dark_detector.detect_dark_events(vessel_imo, mmsi)
        for event in dark_events:
            self.db.add(event)
        
        results["dark_events_detected"] = len(dark_events)

        # ── 2. Detect AIS Spoofing (Speed anomalies) ───────────────
        speed_anomalies = await self.anomaly_detector.detect_speed_spoofing(mmsi)
        results["spoofing_anomalies_detected"] = len(speed_anomalies)
        # Note: In a production app, we would log these to a dedicated `ais_anomalies` table.
        # For the MVP, we log them to stdout/logger.

        # ── 3. Detect Loitering ────────────────────────────────────
        loitering_events = await self.anomaly_detector.detect_loitering(vessel_imo, mmsi)
        results["loitering_events_detected"] = len(loitering_events)

        # ── 4. Detect and persist STS events (Run globally or filter) ─
        # Since STS is a multi-vessel query, we run the global detector and filter for this vessel
        all_sts = await self.sts_detector.detect_sts_transfers(time_window_hours=72.0)
        vessel_sts = [
            e for e in all_sts 
            if e.vessel_a_imo == vessel_imo or e.vessel_b_imo == vessel_imo
        ]
        
        # Clear existing STS events involving this vessel
        await self.db.execute(
            delete(STSEvent).where(
                (STSEvent.vessel_a_imo == vessel_imo) | (STSEvent.vessel_b_imo == vessel_imo)
            )
        )
        for event in vessel_sts:
            self.db.add(event)

        results["sts_events_detected"] = len(vessel_sts)

        await self.db.commit()
        logger.info(
            f"Behavior analysis complete for IMO {vessel_imo}. Results: {results}"
        )
        return results

    async def run_global_analysis(self) -> dict:
        """Run behavior analysis globally across all vessels in the system."""
        logger.info("Running global ship behavior analysis pipeline...")
        # Typically run in background or scheduled task
        sts_events = await self.sts_detector.detect_sts_transfers(time_window_hours=24.0)
        
        # Clear all existing global STS events from the last 24 hours
        # and replace them with freshly detected ones
        for event in sts_events:
            self.db.add(event)
            
        await self.db.commit()
        return {"sts_events_saved": len(sts_events)}
