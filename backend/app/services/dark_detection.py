"""
Dark vessel detection service.

Implements algorithms to identify periods of AIS silence (dark events):
- Gaps in transmission > 6 hours (coastal, within 50nm of shore/ports)
- Gaps in transmission > 24 hours (open ocean)
- Excludes known terrestrial AIS dead zones (geofenced areas)
"""

from datetime import datetime, timedelta, timezone
import json
import logging
import os
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dark_event import DarkEvent
from app.models.port import Port
from app.models.position import VesselPosition as Position
from app.utils.geo import NM_TO_KM, haversine_distance

logger = logging.getLogger(__name__)

# Coastal proximity threshold: 50 nautical miles in km
_COASTAL_RADIUS_KM: float = 50.0 * NM_TO_KM

# Default dead zones if GeoJSON is not present
DEFAULT_DEAD_ZONES = []


def load_dead_zones() -> list[dict]:
    """Load dead zone polygons from data directory."""
    path = os.path.join("data", "dead_zones", "dead_zones.geojson")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("features", [])
        except Exception:
            return DEFAULT_DEAD_ZONES
    return DEFAULT_DEAD_ZONES


def is_in_dead_zone(lat: float, lon: float, dead_zones: list[dict]) -> bool:
    """Check if coordinates fall inside any configured AIS dead zone polygon.
    
    Uses a simple ray-casting algorithm for point-in-polygon checks.
    """
    for feature in dead_zones:
        geom = feature.get("geometry", {})
        if geom.get("type") == "Polygon":
            coordinates = geom.get("coordinates", [])
            for ring in coordinates:
                if point_in_polygon(lon, lat, ring):
                    return True
        elif geom.get("type") == "MultiPolygon":
            coordinates = geom.get("coordinates", [])
            for poly in coordinates:
                for ring in poly:
                    if point_in_polygon(lon, lat, ring):
                        return True
    return False


def point_in_polygon(x: float, y: float, poly: list[list[float]]) -> bool:
    """Ray casting algorithm for point-in-polygon test."""
    n = len(poly)
    inside = False
    p1x, p1y = poly[0]
    for i in range(n + 1):
        p2x, p2y = poly[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xints = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xints:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside


class DarkVesselDetector:
    """Detector for periods of suspicious AIS transmitter disabling."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.dead_zones = load_dead_zones()

    async def detect_dark_events(
        self, vessel_imo: int, mmsi: int
    ) -> list[DarkEvent]:
        """Analyze position history for a vessel to find transmission gaps.
        
        Saves new dark events and returns the list of detected events.
        """
        # Fetch all positions for the vessel sorted chronologically
        query = (
            select(Position)
            .where(Position.mmsi == mmsi)
            .order_by(Position.time.asc())
        )
        result = await self.db.execute(query)
        positions = list(result.scalars().all())

        if len(positions) < 2:
            return []

        dark_events: list[DarkEvent] = []

        for i in range(len(positions) - 1):
            pos_a = positions[i]
            pos_b = positions[i + 1]

            time_a = pos_a.time
            time_b = pos_b.time
            delta = time_b - time_a

            # Check if there is a gap
            hours_gap = delta.total_seconds() / 3600.0

            # Determine if coastal or open ocean
            # We can use a simple check: if we are close to a port (within 50nm).
            # If PostGIS is available, we can run a spatial query to find if the point
            # is near any land or port. As a fallback, we check if it is within 50nm
            # of any known ports/land, or we use a general 6 hour threshold for
            # conservative alerts, or 24 hours for open ocean.
            # Let's check distance to coast. For the MVP, we assume a gap > 6h is coastal
            # if within 50nm (approx 0.83 degrees) of any coast/port, otherwise > 24h.
            # Let's perform a fast check: we check if there are nearby ports using PostGIS.
            is_coastal = await self._is_coastal_position(pos_a.latitude, pos_a.longitude)
            threshold_hours = 6.0 if is_coastal else 24.0

            if hours_gap >= threshold_hours:
                # Check if the gap started in an AIS dead zone
                if is_in_dead_zone(pos_a.latitude, pos_a.longitude, self.dead_zones):
                    continue

                # Create the dark event record
                event = DarkEvent(
                    vessel_imo=vessel_imo,
                    start_time=time_a,
                    start_lat=pos_a.latitude,
                    start_lon=pos_a.longitude,
                    end_time=time_b,
                    end_lat=pos_b.latitude,
                    end_lon=pos_b.longitude,
                    duration_hours=hours_gap,
                    zone_type="coastal" if is_coastal else "open_ocean",
                )
                dark_events.append(event)

        # Check if the vessel is currently dark (i.e. last position was long ago and it's still missing)
        last_pos = positions[-1]
        now = datetime.now(timezone.utc)
        delta_now = now - last_pos.time
        hours_since_last = delta_now.total_seconds() / 3600.0

        is_coastal_last = await self._is_coastal_position(last_pos.latitude, last_pos.longitude)
        threshold_last = 6.0 if is_coastal_last else 24.0

        if hours_since_last >= threshold_last:
            if not is_in_dead_zone(last_pos.latitude, last_pos.longitude, self.dead_zones):
                current_dark_event = DarkEvent(
                    vessel_imo=vessel_imo,
                    start_time=last_pos.time,
                    start_lat=last_pos.latitude,
                    start_lon=last_pos.longitude,
                    end_time=None,  # Ongoing
                    end_lat=None,
                    end_lon=None,
                    duration_hours=hours_since_last,
                    zone_type="coastal" if is_coastal_last else "open_ocean",
                )
                dark_events.append(current_dark_event)

        return dark_events

    async def _is_coastal_position(self, lat: float, lon: float) -> bool:
        """Determine if a point is within 50 nm of any known port.

        Algorithm:
        1. Try PostGIS ST_DWithin on the ports table (fast, index-backed).
        2. If PostGIS is unavailable, fall back to a Python haversine scan.
        3. If the ports table is empty, log a warning and return True (the
           original conservative default) so no dark events are silently lost.

        Args:
            lat: WGS-84 latitude of the position.
            lon: WGS-84 longitude of the position.

        Returns:
            True if within 50 nm of any port, False otherwise.
        """
        try:
            # ── Attempt PostGIS geography query (metres) ───────────────────
            from sqlalchemy import text as sa_text
            radius_m = _COASTAL_RADIUS_KM * 1000.0
            postgis_q = sa_text(
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
            # PostGIS returned a result (even None) — query succeeded.
            # Check count to distinguish "no nearby port" from "empty table".
            count_result = await self.db.execute(select(func.count()).select_from(Port))
            count = count_result.scalar() or 0
            if count == 0:
                logger.warning(
                    "_is_coastal_position: ports table is empty — defaulting to True (coastal). "
                    "Populate the ports table for accurate open-ocean dark event detection."
                )
                return True
            return False

        except Exception:
            # PostGIS not available — fall back to Python haversine scan
            pass

        try:
            ports_result = await self.db.execute(select(Port.latitude, Port.longitude))
            port_coords = ports_result.all()
        except Exception as exc:
            logger.error("_is_coastal_position: failed to query ports table: %s", exc)
            return True  # safe default

        if not port_coords:
            logger.warning(
                "_is_coastal_position: ports table is empty — defaulting to True (coastal). "
                "Populate the ports table for accurate open-ocean dark event detection."
            )
            return True

        for (p_lat, p_lon) in port_coords:
            if haversine_distance(lat, lon, p_lat, p_lon) <= _COASTAL_RADIUS_KM:
                return True
        return False
