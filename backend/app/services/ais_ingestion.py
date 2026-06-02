"""
Real-time AIS telemetry ingestion service.

Listens to the live stream from aisstream.io, decodes position and vessel
identity records, commits them to the database, and broadcasts live position
updates to all connected frontend clients via WebSockets.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from app.config import settings
from app.database import async_session_factory
from app.models.position import VesselPosition
from app.models.vessel import Vessel
from app.routers.ws import manager
from app.services.ais_decoder import (
    decode_aisstream_message,
    extract_position,
    extract_vessel_identity,
)
from app.services.aisstream_client import AISStreamClient, AISStreamSubscription

logger = logging.getLogger(__name__)


class AISIngestionService:
    """Manages the background ingestion lifecycle of the real-time AIS feed."""

    def __init__(self) -> None:
        self.client: AISStreamClient | None = None
        self._running = False

    async def start(self) -> None:
        """Start the live ingestion client in the background."""
        if self._running:
            logger.warning("AISIngestionService is already running")
            return

        if not settings.AISSTREAM_API_KEY:
            logger.warning("AISSTREAM_API_KEY is not set. AIS Ingest will not start.")
            return

        self._running = True
        logger.info("Initializing AISIngestionService using configured API Key...")

        # Setup subscription: standard classes globally by default
        subscription = AISStreamSubscription()
        self.client = AISStreamClient(
            api_key=settings.AISSTREAM_API_KEY,
            on_message=self.handle_message,
            subscription=subscription,
        )
        await self.client.connect()
        logger.info("AISIngestionService background worker started successfully")

    async def stop(self) -> None:
        """Gracefully disconnect and stop the ingestion client."""
        self._running = False
        if self.client is not None:
            await self.client.disconnect()
            self.client = None
        logger.info("AISIngestionService background worker stopped")

    async def handle_message(self, raw_data: dict[str, Any]) -> None:
        """Process a decoded NMEA message received from the live feed."""
        try:
            # Decode the raw JSON structure from aisstream.io
            decoded = decode_aisstream_message(raw_data)
            if not decoded:
                return

            # ── 1. Handle Position Telemetry ───────────────────────────────
            pos_data = extract_position(decoded)
            if pos_data:
                # Resolve timestamp, fallback to current UTC datetime
                time_val = datetime.now(timezone.utc)
                if pos_data.timestamp:
                    try:
                        clean_ts = pos_data.timestamp.split(" UTC")[0].strip()
                        time_val = datetime.fromisoformat(clean_ts).replace(tzinfo=timezone.utc)
                    except Exception:
                        pass

                # Save position report to the database
                async with async_session_factory() as db:
                    position = VesselPosition(
                        time=time_val,
                        mmsi=pos_data.mmsi,
                        latitude=pos_data.latitude,
                        longitude=pos_data.longitude,
                        speed=pos_data.speed,
                        course=pos_data.course,
                        heading=pos_data.heading,
                        nav_status=pos_data.nav_status,
                        msg_type=pos_data.msg_type,
                    )
                    db.add(position)
                    await db.commit()

                # Broadcast current position live to Map WebSocket clients
                await manager.broadcast({
                    "type": "position_update",
                    "data": {
                        "mmsi": pos_data.mmsi,
                        "latitude": pos_data.latitude,
                        "longitude": pos_data.longitude,
                        "speed": pos_data.speed,
                        "course": pos_data.course,
                        "heading": pos_data.heading,
                        "nav_status": pos_data.nav_status,
                        "time": time_val.isoformat(),
                    }
                })

            # ── 2. Handle Vessel Static Identity Updates ──────────────────
            identity_data = extract_vessel_identity(decoded)
            if identity_data and identity_data.imo:
                async with async_session_factory() as db:
                    # Query if vessel already exists in the registry
                    stmt = select(Vessel).where(Vessel.imo == identity_data.imo)
                    res = await db.execute(stmt)
                    vessel = res.scalar_one_or_none()

                    if vessel:
                        # Update existing static properties
                        if identity_data.name:
                            vessel.name = identity_data.name
                        if identity_data.mmsi:
                            vessel.mmsi = identity_data.mmsi
                        if identity_data.call_sign:
                            vessel.call_sign = identity_data.call_sign
                        if identity_data.ship_type:
                            vessel.vessel_type = _map_ship_type(identity_data.ship_type)
                        vessel.updated_at = datetime.now(timezone.utc)
                    else:
                        # Register new vessel dynamically
                        vessel = Vessel(
                            imo=identity_data.imo,
                            mmsi=identity_data.mmsi,
                            name=identity_data.name or f"MMSI {identity_data.mmsi}",
                            call_sign=identity_data.call_sign,
                            vessel_type=_map_ship_type(identity_data.ship_type) if identity_data.ship_type else "Other",
                            created_at=datetime.now(timezone.utc),
                            updated_at=datetime.now(timezone.utc),
                        )
                        db.add(vessel)

                    await db.commit()

        except Exception as exc:
            logger.error("Error processing AIS message inside ingest service: %s", exc, exc_info=True)


def _map_ship_type(type_code: int) -> str:
    """Map standard international AIS ship type codes to simple UI categories."""
    if 30 <= type_code <= 39:
        return "Fishing"
    elif 70 <= type_code <= 79:
        return "Cargo"
    elif 80 <= type_code <= 89:
        return "Tanker"
    elif 60 <= type_code <= 69:
        return "Passenger"
    elif 50 <= type_code <= 59:
        return "Special / Tug"
    return "Other"


# Global singleton instance
ingestion_service = AISIngestionService()
