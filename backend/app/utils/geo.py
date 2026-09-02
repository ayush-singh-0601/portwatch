"""
Geospatial utility functions for PortWatch detection services.

Provides:
- haversine_distance: great-circle distance between two WGS-84 points (km)
- nm_to_km: nautical miles to kilometres conversion
- SHIP_BREAKING_YARDS: hard-coded coordinates of the five major
  ship-breaking yards used by the loitering risk-zone check.
"""

import math

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Earth mean radius in kilometres (WGS-84 approximation).
_EARTH_RADIUS_KM: float = 6371.0

#: 1 nautical mile in kilometres (exact by definition since 1954).
NM_TO_KM: float = 1.852

# Major ship-breaking yards: (name, latitude, longitude).
# Used by _is_near_risk_zone without requiring any database rows.
SHIP_BREAKING_YARDS: list[tuple[str, float, float]] = [
    ("Alang, India",          21.41,  72.18),
    ("Gadani, Pakistan",      25.12,  66.73),
    ("Chattogram, Bangladesh", 22.23, 91.78),
    ("Aliaga, Turkey",        38.80,  26.97),
    ("Zhoushan, China",       29.99, 122.21),
]


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------

def nm_to_km(nautical_miles: float) -> float:
    """Convert nautical miles to kilometres."""
    return nautical_miles * NM_TO_KM


def haversine_distance(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """Return the great-circle distance in kilometres between two WGS-84 points.

    Uses the Haversine formula, which is accurate to within ~0.5% for
    distances up to a few thousand kilometres.

    Args:
        lat1: Latitude of point A in decimal degrees.
        lon1: Longitude of point A in decimal degrees.
        lat2: Latitude of point B in decimal degrees.
        lon2: Longitude of point B in decimal degrees.

    Returns:
        Distance in kilometres (>= 0).
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2.0) ** 2
    )
    # Clamp a to [0.0, 1.0] to prevent math domain errors for antipodal points
    # caused by floating-point roundoff (e.g. 1.0000000000000002 -> ValueError in sqrt(1 - a))
    a = min(1.0, max(0.0, a))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return _EARTH_RADIUS_KM * c


def is_within_nm(
    lat1: float, lon1: float, lat2: float, lon2: float, radius_nm: float
) -> bool:
    """Return True if two WGS-84 points are within *radius_nm* nautical miles.

    Args:
        lat1: Latitude of point A.
        lon1: Longitude of point A.
        lat2: Latitude of point B.
        lon2: Longitude of point B.
        radius_nm: Proximity threshold in nautical miles.

    Returns:
        True if the haversine distance is <= radius_nm nautical miles.
    """
    return haversine_distance(lat1, lon1, lat2, lon2) <= nm_to_km(radius_nm)


def is_in_bbox(lat: float, lon: float, bbox: list[float] | tuple[float, float, float, float]) -> bool:
    """Check if coordinates fall inside a bounding box [min_lon, min_lat, max_lon, max_lat].

    Handles antimeridian (180th meridian) crossing when min_lon > max_lon.
    """
    if len(bbox) != 4 or lat is None or lon is None:
        return False
    min_lon, min_lat, max_lon, max_lat = bbox
    in_lat = min_lat <= lat <= max_lat
    if min_lon <= max_lon:
        in_lon = min_lon <= lon <= max_lon
    else:
        in_lon = lon >= min_lon or lon <= max_lon
    return in_lat and in_lon


def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the initial great-circle bearing (forward azimuth) from point A to B.

    Args:
        lat1: Origin latitude in degrees.
        lon1: Origin longitude in degrees.
        lat2: Destination latitude in degrees.
        lon2: Destination longitude in degrees.

    Returns:
        Bearing in degrees normalized to [0, 360).
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_lam = math.radians(lon2 - lon1)

    y = math.sin(d_lam) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(d_lam)

    bearing = math.degrees(math.atan2(y, x))
    return (bearing + 360.0) % 360.0


def destination_point(lat: float, lon: float, distance_km: float, bearing_deg: float) -> tuple[float, float]:
    """Calculate destination coordinates given an origin, distance, and bearing.

    Args:
        lat: Origin latitude in degrees.
        lon: Origin longitude in degrees.
        distance_km: Distance to travel in kilometres.
        bearing_deg: Travel bearing in degrees [0, 360).

    Returns:
        Tuple of (destination_latitude, destination_longitude) in degrees.
    """
    delta = distance_km / _EARTH_RADIUS_KM
    theta = math.radians(bearing_deg)
    phi1 = math.radians(lat)
    lambda1 = math.radians(lon)

    phi2 = math.asin(
        math.sin(phi1) * math.cos(delta) + math.cos(phi1) * math.sin(delta) * math.cos(theta)
    )
    lambda2 = lambda1 + math.atan2(
        math.sin(theta) * math.sin(delta) * math.cos(phi1),
        math.cos(delta) - math.sin(phi1) * math.sin(phi2),
    )

    dest_lat = math.degrees(phi2)
    dest_lon = (math.degrees(lambda2) + 540.0) % 360.0 - 180.0
    return dest_lat, dest_lon


