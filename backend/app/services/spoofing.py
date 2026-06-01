"""
AIS spoofing and loitering detection services.

Implements maritime anomaly detection:
- Impossible speed jumps (> 50 knots) between consecutive positions.
- Duplicate MMSI transmissions (same MMSI > 1000 km apart within 1 minute).
- Loitering near sanctioned ports or ship-breaking yards for > 4 hours at low speed (< 2 knots).
"""

from datetime import datetime, timedelta
import math
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.position import Position
from app.models.vessel import Vessel


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points in kilometers.
    
    Uses the Haversine formula.
    """
    R = 6371.0  # Earth radius in km
    
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    
    return R * c


class AISAnomalyDetector:
    """Detector for AIS spoofing, duplicate MMSIs, and vessel loitering."""

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
                ST_Distance(pa.location, pb.location) AS distance_m
            FROM vessel_positions pa
            JOIN vessel_positions pb
              ON pa.mmsi = pb.mmsi
              AND pa.time < pb.time
              AND pb.time - pa.time <= CAST(:window_interval AS INTERVAL)
              -- Distances greater than 1,000,000 meters (1000 km)
              AND NOT ST_DWithin(pa.location, pb.location, 1000000)
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
            print(f"Error checking duplicate MMSI: {e}")

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
        """Check if coordinates are near high-risk/sanctioned ports or ship breaking yards."""
        # Simple geofence check. In a production app, we would query the database
        # for port coordinates matching sanctioned countries or known yards.
        # For the MVP, we assume any slow speed near a port call in a high-risk area is risk loitering.
        try:
            query = text(
                """
                SELECT EXISTS(
                    SELECT 1 FROM port_calls
                    WHERE ST_DWithin(
                        ST_SetSRID(ST_Point(:lon, :lat), 4326)::geography,
                        ST_SetSRID(ST_Point(longitude, latitude), 4326)::geography,
                        5000
                    )
                    AND (psc_detention = TRUE OR psc_deficiencies > 3)
                    LIMIT 1
                )
                """
            )
            res = await self.db.execute(query, {"lat": lat, "lon": lon})
            return res.scalar() or False
        except Exception:
            return False
