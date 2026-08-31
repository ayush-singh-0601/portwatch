"""
AIS spoofing and loitering detection services.

Implements maritime anomaly detection:
- Impossible speed jumps (> 50 knots) between consecutive positions.
- Duplicate MMSI transmissions (same MMSI > 1000 km apart within 1 minute).
- Loitering near sanctioned ports or ship-breaking yards for > 4 hours at low speed (< 2 knots).
"""

from datetime import datetime, timedelta
import logging
from typing import Optional

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.port import Port
from app.models.position import VesselPosition as Position
from app.models.vessel import Vessel
from app.utils.geo import NM_TO_KM, SHIP_BREAKING_YARDS, haversine_distance

logger = logging.getLogger(__name__)

# Sanctioned port countries (mirrors risk_scoring.py — single source of truth
# kept here to avoid a circular import)
_SANCTIONED_PORT_COUNTRIES: frozenset[str] = frozenset({
    "IRN", "PRK", "CUB", "SYR", "VEN", "RUS",
})

# Default loitering risk-zone radius: 30 nautical miles
_RISK_ZONE_RADIUS_KM: float = 30.0 * NM_TO_KM


class AISAnomalyDetector:
    """Detector for AIS spoofing, duplicate MMSIs, and vessel loitering.

    Detection methods:
    - ``detect_speed_spoofing``: impossible speed jumps (> 50 kts default).
    - ``detect_duplicate_mmsi``: same MMSI appearing > 1,000 km apart within
      a short time window — requires PostGIS on the database.
    - ``detect_loitering``: sustained low speed (≤ 2 kts, ≥ 4 h) near a
      sanctioned port or ship-breaking yard.  Risk-zone proximity is evaluated
      by ``_is_near_risk_zone``, which checks five hard-coded ship-breaking
      yard constants plus any ports in the ``ports`` reference table whose
      country is in the sanctioned list.
    """


    def __init__(self, db: AsyncSession):
        self.db = db

    async def detect_speed_spoofing(
        self, mmsi: int, max_speed_knots: float = 50.0
    ) -> list[dict]:
        """Detect impossible speed jumps between consecutive positions for a vessel.
        
        Returns a list of anomaly details.
        """
        # Get last 100 positions sorted by time ascending
        query = (
            select(Position)
            .where(Position.mmsi == mmsi)
            .order_by(Position.time.asc())
            .limit(100)
        )
        result = await self.db.execute(query)
        positions = list(result.scalars().all())

        anomalies = []
        if len(positions) < 2:
            return anomalies

        for i in range(len(positions) - 1):
            pos_a = positions[i]
            pos_b = positions[i + 1]

            if (
                pos_a.time is None
                or pos_b.time is None
                or pos_a.latitude is None
                or pos_a.longitude is None
                or pos_b.latitude is None
                or pos_b.longitude is None
            ):
                continue

            time_diff = (pos_b.time - pos_a.time).total_seconds()
            if time_diff <= 0:
                continue

            # Calculate distance in km
            dist_km = haversine_distance(
                pos_a.latitude, pos_a.longitude, pos_b.latitude, pos_b.longitude
            )
            
            # Speed = distance / time (in hours)
            hours = time_diff / 3600.0
            calculated_speed_kmh = dist_km / hours
            calculated_speed_knots = calculated_speed_kmh / 1.852

            if calculated_speed_knots > max_speed_knots:
                anomalies.append({
                    "mmsi": mmsi,
                    "time_start": pos_a.time,
                    "time_end": pos_b.time,
                    "distance_km": dist_km,
                    "duration_seconds": time_diff,
                    "calculated_speed_knots": calculated_speed_knots,
                    "pos_a": (pos_a.latitude, pos_a.longitude),
                    "pos_b": (pos_b.latitude, pos_b.longitude),
                    "type": "impossible_speed"
                })

        return anomalies

    async def detect_duplicate_mmsi(self, window_minutes: float = 5.0) -> list[dict]:
        """Detect the same MMSI appearing in two widely separate places almost simultaneously.
        
        Threshold: > 1000 km apart in less than 1 minute (or within the window_minutes).
        """
        query = text(
            """
            SELECT 
                pa.mmsi,
                pa.time AS time_a,
                pb.time AS time_b,
                pa.latitude AS lat_a,
                pa.longitude AS lon_a,
                pb.latitude AS lat_b,
                pb.longitude AS lon_b,
                ST_Distance(
                    ST_SetSRID(ST_Point(pa.longitude, pa.latitude), 4326)::geography,
                    ST_SetSRID(ST_Point(pb.longitude, pb.latitude), 4326)::geography
                ) AS distance_m
            FROM vessel_positions pa
            JOIN vessel_positions pb
              ON pa.mmsi = pb.mmsi
              AND pa.time < pb.time
              AND pb.time - pa.time <= CAST(:window_interval AS INTERVAL)
              -- Distances greater than 1,000,000 meters (1000 km)
              AND NOT ST_DWithin(
                    ST_SetSRID(ST_Point(pa.longitude, pa.latitude), 4326)::geography,
                    ST_SetSRID(ST_Point(pb.longitude, pb.latitude), 4326)::geography,
                    1000000
              )
            WHERE pa.time > NOW() - INTERVAL '1 hour'
            """
        )

        anomalies = []
        try:
            window_str = f"{window_minutes} minutes"
            result = await self.db.execute(query, {"window_interval": window_str})
            rows = result.fetchall()

            for row in rows:
                mmsi, time_a, time_b, lat_a, lon_a, lat_b, lon_b, dist_m = row
                anomalies.append({
                    "mmsi": mmsi,
                    "time_a": time_a,
                    "time_b": time_b,
                    "pos_a": (lat_a, lon_a),
                    "pos_b": (lat_b, lon_b),
                    "distance_km": dist_m / 1000.0,
                    "type": "duplicate_mmsi"
                })
        except Exception as e:
            logger.error(f"Error checking duplicate MMSI: {e}")

        return anomalies

    async def detect_loitering(self, vessel_imo: int, mmsi: int) -> list[dict]:
        """Detect vessel loitering (low speed near high-risk/sanctioned ports or ship-breaking yards).
        
        Threshold: low speed (< 2 knots) near sanctioned port for > 4 hours.
        """
        # Query positions where speed is low
        query = (
            select(Position)
            .where(Position.mmsi == mmsi)
            .order_by(Position.time.asc())
        )
        result = await self.db.execute(query)
        positions = list(result.scalars().all())

        loitering_events = []
        if len(positions) < 2:
            return loitering_events

        # Identify contiguous periods of speed <= 2.0 knots
        start_pos = None
        current_loitering = []

        for pos in positions:
            is_slow = pos.speed is not None and pos.speed <= 2.0
            
            if is_slow:
                if start_pos is None:
                    start_pos = pos
                current_loitering.append(pos)
            else:
                if start_pos is not None and len(current_loitering) > 1:
                    if pos.time and start_pos.time:
                        duration = (pos.time - start_pos.time).total_seconds() / 3600.0
                        if duration >= 4.0:
                            # Check if near a sanctioned port or ship breaking yard
                            is_near_risk = await self._is_near_risk_zone(
                                start_pos.latitude, start_pos.longitude
                            )
                            if is_near_risk:
                                loitering_events.append({
                                    "vessel_imo": vessel_imo,
                                    "start_time": start_pos.time,
                                    "end_time": pos.time,
                                    "duration_hours": duration,
                                    "latitude": start_pos.latitude,
                                    "longitude": start_pos.longitude,
                                    "type": "loitering_near_risk_zone"
                                })
                start_pos = None
                current_loitering = []

        # Handle ongoing loitering
        if start_pos is not None and len(current_loitering) > 1:
            last_pos = current_loitering[-1]
            if last_pos.time and start_pos.time:
                duration = (last_pos.time - start_pos.time).total_seconds() / 3600.0
                if duration >= 4.0:
                    is_near_risk = await self._is_near_risk_zone(
                        start_pos.latitude, start_pos.longitude
                    )
                if is_near_risk:
                    loitering_events.append({
                        "vessel_imo": vessel_imo,
                        "start_time": start_pos.time,
                        "end_time": last_pos.time,
                        "duration_hours": duration,
                        "latitude": start_pos.latitude,
                        "longitude": start_pos.longitude,
                        "type": "loitering_near_risk_zone"
                    })

        return loitering_events

    async def _is_near_risk_zone(self, lat: float, lon: float) -> bool:
        """Check if coordinates are near a high-risk/sanctioned port or ship-breaking yard.

        Two independent checks are performed (either is sufficient to return True):

        1. **Ship-breaking yards** — five hard-coded yard coordinates stored as
           constants in ``utils.geo.SHIP_BREAKING_YARDS``.  No database query
           required; always works even when the ports table is empty.
        2. **Sanctioned ports** — any port in the ``ports`` table whose
           ``country`` is in the ``_SANCTIONED_PORT_COUNTRIES`` set and is
           within *_RISK_ZONE_RADIUS_KM* of the supplied coordinates.

        If the ports table is empty, only check (1) is performed and a warning
        is logged so operators know to populate the table for full coverage.

        Args:
            lat: WGS-84 latitude.
            lon: WGS-84 longitude.

        Returns:
            True if within range of any known risk zone, False otherwise.
        """
        # ── 1. Ship-breaking yards (always checked, no DB) ────────────────
        for _yard_name, yard_lat, yard_lon in SHIP_BREAKING_YARDS:
            if haversine_distance(lat, lon, yard_lat, yard_lon) <= _RISK_ZONE_RADIUS_KM:
                return True

        # ── 2. Sanctioned ports from the ports reference table ─────────────
        try:
            result = await self.db.execute(
                select(Port.latitude, Port.longitude)
                .where(Port.country.in_(_SANCTIONED_PORT_COUNTRIES))
            )
            sanctioned_ports = result.all()
        except Exception as exc:
            logger.error("_is_near_risk_zone: failed to query ports table: %s", exc)
            return False

        if not sanctioned_ports:
            count_result = await self.db.execute(select(func.count()).select_from(Port))
            total = count_result.scalar() or 0
            if total == 0:
                logger.warning(
                    "_is_near_risk_zone: ports table is empty — only ship-breaking yard "
                    "constants were checked. Populate the ports table for sanctioned-port "
                    "proximity detection."
                )
            return False

        for (p_lat, p_lon) in sanctioned_ports:
            if haversine_distance(lat, lon, p_lat, p_lon) <= _RISK_ZONE_RADIUS_KM:
                return True
        return False

