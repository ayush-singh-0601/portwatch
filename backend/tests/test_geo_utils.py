"""
Unit tests for app.utils.geo -- haversine distance and proximity helpers.

These tests run without any database or network access.
"""

import math
import pytest

from app.utils.geo import (
    NM_TO_KM,
    SHIP_BREAKING_YARDS,
    calculate_bearing,
    destination_point,
    haversine_distance,
    is_in_bbox,
    is_within_nm,
    nm_to_km,
)


# ---------------------------------------------------------------------------
# nm_to_km
# ---------------------------------------------------------------------------

class TestNmToKm:
    def test_zero(self):
        assert nm_to_km(0) == 0.0

    def test_one_nm(self):
        assert nm_to_km(1) == pytest.approx(1.852, rel=1e-6)

    def test_fifty_nm(self):
        assert nm_to_km(50) == pytest.approx(92.6, rel=1e-3)


# ---------------------------------------------------------------------------
# haversine_distance
# ---------------------------------------------------------------------------

class TestHaversineDistance:
    def test_same_point_returns_zero(self):
        """Identical coordinates must return exactly 0."""
        assert haversine_distance(1.35, 103.82, 1.35, 103.82) == pytest.approx(0.0, abs=1e-9)

    def test_singapore_to_rotterdam_within_1_percent(self):
        """Singapore -> Rotterdam is ~10,550 km; result must be within 1%."""
        # Singapore: 1.35 N, 103.82 E  |  Rotterdam: 51.95 N, 4.14 E
        dist = haversine_distance(1.35, 103.82, 51.95, 4.14)
        assert dist == pytest.approx(10_550.0, rel=0.01)

    def test_symmetry(self):
        """Distance A->B must equal B->A."""
        d1 = haversine_distance(48.85, 2.35, 51.51, -0.13)  # Paris -> London
        d2 = haversine_distance(51.51, -0.13, 48.85, 2.35)  # London -> Paris
        assert d1 == pytest.approx(d2, rel=1e-9)

    def test_known_paris_london(self):
        """Paris -> London is approximately 340 km by great-circle."""
        dist = haversine_distance(48.85, 2.35, 51.51, -0.13)
        assert dist == pytest.approx(340.0, rel=0.05)

    def test_antimeridian_crossing(self):
        """Points either side of the antimeridian should still give a sensible answer."""
        # Fiji (approx) -> Samoa (approx)
        dist = haversine_distance(-17.0, 179.0, -13.0, -172.0)
        assert 0.0 < dist < 2000.0

    def test_exact_antipodal_does_not_raise(self):
        """Antipodal points (opposite sides of globe) must not raise math domain error."""
        # Exact antipodes: (lat, lon) and (-lat, lon + 180)
        dist = haversine_distance(45.0, 10.0, -45.0, -170.0)
        # Half Earth circumference = pi * 6371 ~= 20015 km
        assert dist == pytest.approx(math.pi * 6371.0, rel=1e-3)


# ---------------------------------------------------------------------------
# is_within_nm
# ---------------------------------------------------------------------------

class TestIsWithinNm:
    def test_same_point_within_zero_nm(self):
        assert is_within_nm(0.0, 0.0, 0.0, 0.0, 0.0) is True

    def test_within_threshold(self):
        # Singapore port is well within 50 nm of itself
        assert is_within_nm(1.35, 103.82, 1.35, 103.82, 50.0) is True

    def test_outside_threshold(self):
        # Rotterdam to Singapore is ~10,300 km, far outside 50 nm
        assert is_within_nm(51.95, 4.14, 1.35, 103.82, 50.0) is False

    def test_borderline(self):
        # Approximately 92.6 km apart should be exactly at 50 nm boundary
        # Use a point ~92.6 km north of origin
        lat2 = 0.0 + (92.6 / 111.0)  # ~1 degree north at equator
        within = is_within_nm(0.0, 0.0, lat2, 0.0, 50.0)
        # Could be True or False at the boundary -- just ensure no crash
        assert isinstance(within, bool)


# ---------------------------------------------------------------------------
# SHIP_BREAKING_YARDS constants
# ---------------------------------------------------------------------------

class TestShipBreakingYards:
    def test_five_yards_defined(self):
        assert len(SHIP_BREAKING_YARDS) == 5

    def test_all_have_name_lat_lon(self):
        for entry in SHIP_BREAKING_YARDS:
            name, lat, lon = entry
            assert isinstance(name, str) and name
            assert -90.0 <= lat <= 90.0
            assert -180.0 <= lon <= 180.0

    def test_alang_coordinates_approximate(self):
        """Alang, India should be near 21.41 N, 72.18 E."""
        alang = next(y for y in SHIP_BREAKING_YARDS if "Alang" in y[0])
        _, lat, lon = alang
        assert lat == pytest.approx(21.41, abs=1.0)
        assert lon == pytest.approx(72.18, abs=1.0)

    def test_within_30nm_of_alang(self):
        """A point at Alang should be within 30 nm of the Alang yard."""
        _, yard_lat, yard_lon = next(y for y in SHIP_BREAKING_YARDS if "Alang" in y[0])
        assert is_within_nm(yard_lat, yard_lon, yard_lat, yard_lon, 30.0) is True

    def test_open_ocean_not_near_any_yard(self):
        """Gulf of Guinea open ocean (0, 0) should not be within 30 nm of any yard."""
        for _name, yard_lat, yard_lon in SHIP_BREAKING_YARDS:
            assert not is_within_nm(0.0, 0.0, yard_lat, yard_lon, 30.0)


# ---------------------------------------------------------------------------
# is_in_bbox
# ---------------------------------------------------------------------------

class TestIsInBbox:
    def test_point_inside_standard_bbox(self):
        bbox = [-10.0, 40.0, 10.0, 60.0]
        assert is_in_bbox(50.0, 0.0, bbox) is True

    def test_point_outside_standard_bbox(self):
        bbox = [-10.0, 40.0, 10.0, 60.0]
        assert is_in_bbox(70.0, 0.0, bbox) is False
        assert is_in_bbox(50.0, 20.0, bbox) is False

    def test_antimeridian_crossing_bbox(self):
        # Bbox spanning from 170 E to -170 W across 180th meridian
        bbox = [170.0, -20.0, -170.0, 20.0]
        assert is_in_bbox(0.0, 175.0, bbox) is True
        assert is_in_bbox(0.0, -175.0, bbox) is True
        assert is_in_bbox(0.0, 160.0, bbox) is False
        assert is_in_bbox(0.0, -160.0, bbox) is False


# ---------------------------------------------------------------------------
# calculate_bearing and destination_point
# ---------------------------------------------------------------------------

class TestBearingAndDestination:
    def test_due_north_bearing(self):
        bearing = calculate_bearing(0.0, 0.0, 10.0, 0.0)
        assert bearing == pytest.approx(0.0, abs=1e-3)

    def test_due_east_bearing(self):
        bearing = calculate_bearing(0.0, 0.0, 0.0, 10.0)
        assert bearing == pytest.approx(90.0, abs=1e-3)

    def test_due_south_bearing(self):
        bearing = calculate_bearing(10.0, 0.0, 0.0, 0.0)
        assert bearing == pytest.approx(180.0, abs=1e-3)

    def test_due_west_bearing(self):
        bearing = calculate_bearing(0.0, 10.0, 0.0, 0.0)
        assert bearing == pytest.approx(270.0, abs=1e-3)

    def test_destination_point_north(self):
        lat, lon = destination_point(0.0, 0.0, 111.19, 0.0)
        assert lat == pytest.approx(1.0, abs=0.01)
        assert lon == pytest.approx(0.0, abs=0.01)

    def test_destination_point_east_at_equator(self):
        lat, lon = destination_point(0.0, 0.0, 111.19, 90.0)
        assert lat == pytest.approx(0.0, abs=0.01)
        assert lon == pytest.approx(1.0, abs=0.01)


