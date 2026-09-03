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

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.port import Port
from app.models.sts_event import STSEvent
from app.utils.geo import haversine_distance

logger = logging.getLogger(__name__)

# Port-limit proximity threshold: 5 km
_PORT_LIMIT_RADIUS_KM: float = 5.0


class STSTransferDetector:
    """Detector for suspicious Ship-to-Ship transfer events using spatial queries.

    Port-limit check (``_check_in_port_limits``) uses a 5 km radius around
    each entry in the ``ports`` reference table.  PostGIS ``ST_DWithin`` is
    tried first; a Python haversine scan is used as fallback when PostGIS is
    unavailable.  When the ``ports`` table is empty, all STS events are
    conservatively reported as off-port-limits and a warning is logged.
    """

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
            select(Vessel.imo).where(Vessel.mmsi == mmsi).limit(1)
        )
        return result.scalar_one_or_none()

    async def _check_in_port_limits(self, lat: float, lon: float) -> bool:
        """Determine if coordinates are within designated port limits (5 km).

        Algorithm:
        1. Try PostGIS ST_DWithin on the ports table for speed.
        2. Fall back to a Python haversine scan if PostGIS is unavailable.
        3. If the ports table is empty, log a warning and return False (the
           original conservative default) — STS events are then assumed to
           be off-port-limits, which errs on the side of higher risk.

        Args:
            lat: WGS-84 latitude.
            lon: WGS-84 longitude.

        Returns:
            True if within 5 km of any known port, False otherwise.
        """
        if lat is None or lon is None:
            return False

        radius_m = _PORT_LIMIT_RADIUS_KM * 1000.0

        try:
            # ── Attempt PostGIS geography query ────────────────────────────
            postgis_q = text(
                """
                SELECT 1 FROM ports
                WHERE ST_DWithin(
                    ST_SetSRID(ST_Point(longitude, latitude), 4326)::geography,
                    ST_SetSRID(ST_Point(:lon, :lat), 4326)::geography,
                    :radius_m
                )
                LIMIT 1
                """
            )
            result = await self.db.execute(postgis_q, {"lat": lat, "lon": lon, "radius_m": radius_m})
            row = result.fetchone()
            if row is not None:
                return True
            # Query succeeded — confirm table isn't just empty
            count_result = await self.db.execute(select(func.count()).select_from(Port))
            count = count_result.scalar() or 0
            if count == 0:
                logger.warning(
                    "_check_in_port_limits: ports table is empty — defaulting to False "
                    "(off-port-limits). Populate the ports table for accurate STS filtering."
                )
                return False
            return False

        except Exception:
            # PostGIS unavailable — fall back to haversine scan
            pass

        try:
            ports_result = await self.db.execute(select(Port.latitude, Port.longitude))
            port_coords = ports_result.all()
        except Exception as exc:
            logger.error("_check_in_port_limits: failed to query ports table: %s", exc)
            return False

        if not port_coords:
            logger.warning(
                "_check_in_port_limits: ports table is empty — defaulting to False "
                "(off-port-limits). Populate the ports table for accurate STS filtering."
            )
            return False

        # Fast bounding-box pre-filtering (1 deg latitude ≈ 111 km)
        dlat_max = _PORT_LIMIT_RADIUS_KM / 110.0
        for (p_lat, p_lon) in port_coords:
            if p_lat is None or p_lon is None:
                continue
            if abs(p_lat - lat) > dlat_max:
                continue
            if haversine_distance(lat, lon, p_lat, p_lon) <= _PORT_LIMIT_RADIUS_KM:
                return True
        return False

