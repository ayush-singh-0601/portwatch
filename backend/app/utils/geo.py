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
