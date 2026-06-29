"""
Ship-to-Ship (STS) transfer detection service.

Identifies potential Ship-to-Ship cargo transfers at sea:
- Two vessels in close proximity (<= 500 meters)
- Both vessels traveling at low speed (<= 2 knots)
- In proximity for a sustained period (>= 30 minutes)
- Occurs outside designated port limits (off-port-limits)
"""

from datetime import datetime, timedelta, timezone
import logging
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sts_event import STSEvent

logger = logging.getLogger(__name__)


class STSTransferDetector:
    """Detector for suspicious Ship-to-Ship transfer events using spatial queries."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def detect_sts_transfers(
        self, time_window_hours: float = 24.0
    ) -> list[STSEvent]:
        """Detect STS transfer events occurring within the last time window.
        
        Uses PostGIS ST_DWithin on geography location columns for high performance.
        """
        # Raw PostGIS query to find pairs of positions within 500m at the same time (within 1 min gap)
        # where both are moving at <= 2.0 knots.
        # We join positions on time matching within 1 minute, and distance <= 500 meters.
        query = text(
            """
            WITH position_pairs AS (
                SELECT 
                    pa.mmsi AS mmsi_a,
                    pb.mmsi AS mmsi_b,
                    pa.time AS time_a,
                    pb.time AS time_b,
                    pa.latitude AS lat_a,
                    pa.longitude AS lon_a,
                    ST_Distance(
                        ST_SetSRID(ST_Point(pa.longitude, pa.latitude), 4326)::geography,
                        ST_SetSRID(ST_Point(pb.longitude, pb.latitude), 4326)::geography
                    ) AS distance_m
                FROM vessel_positions pa
                JOIN vessel_positions pb
                  ON pa.mmsi < pb.mmsi
                  AND pa.time BETWEEN pb.time - INTERVAL '1 minute' AND pb.time + INTERVAL '1 minute'
                  AND ST_DWithin(
                        ST_SetSRID(ST_Point(pa.longitude, pa.latitude), 4326)::geography,
                        ST_SetSRID(ST_Point(pb.longitude, pb.latitude), 4326)::geography,
                        500
                  )
                WHERE pa.speed <= 2.0 
                  AND pb.speed <= 2.0
                  AND pa.time > NOW() - CAST(:window_interval AS INTERVAL)
            )
            SELECT 
                mmsi_a,
                mmsi_b,
                MIN(time_a) AS start_time,
                MAX(time_a) AS end_time,
                AVG(lat_a) AS latitude,
                AVG(lon_a) AS longitude,
                MIN(distance_m) AS min_distance_m
            FROM position_pairs
            GROUP BY mmsi_a, mmsi_b, date_trunc('hour', time_a)
            HAVING (MAX(time_a) - MIN(time_a)) >= INTERVAL '30 minutes'
            """
        )

        sts_events: list[STSEvent] = []
        try:
            window_str = f"{time_window_hours} hours"
            result = await self.db.execute(query, {"window_interval": window_str})
            rows = result.fetchall()

            for row in rows:
                mmsi_a, mmsi_b, start_time, end_time, lat, lon, min_dist = row

                # Resolve MMSIs to IMOs (vessel IDs)
                vessel_a_imo = await self._get_vessel_imo(mmsi_a)
                vessel_b_imo = await self._get_vessel_imo(mmsi_b)

                if not vessel_a_imo or not vessel_b_imo:
                    continue

                duration = (end_time - start_time).total_seconds() / 60.0

                # Check if this occurred within port limits
                in_port = await self._check_in_port_limits(lat, lon)

                event = STSEvent(
                    vessel_a_imo=vessel_a_imo,
                    vessel_b_imo=vessel_b_imo,
                    start_time=start_time,
                    end_time=end_time,
                    latitude=lat,
                    longitude=lon,
                    min_distance_m=float(min_dist) if min_dist is not None else None,
                    duration_minutes=duration,
                    in_port_limits=in_port,
                )
                sts_events.append(event)

        except Exception as e:
            # Fallback if PostGIS tables or database is empty / not initialized with proper functions
            logger.error(f"Error executing STS detection query: {e}")

        return sts_events

    async def _get_vessel_imo(self, mmsi: int) -> Optional[int]:
        """Look up the IMO number of a vessel by its MMSI."""
        result = await self.db.execute(
            text("SELECT imo FROM vessels WHERE mmsi = :mmsi LIMIT 1"),
            {"mmsi": mmsi}
        )
        row = result.fetchone()
        return row[0] if row else None

    async def _check_in_port_limits(self, lat: float, lon: float) -> bool:
        """Determine if the coordinates are within designated port limits."""
        # port_calls table has no longitude/latitude columns; returning False
        # until a proper ports/geofence table with coordinates is available.
        return False
