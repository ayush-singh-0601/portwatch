"""
Tests for dark_detection.py — specifically the point_in_polygon function.

Covers:
- Basic interior / exterior classification.
- Horizontal-edge polygon (previously caused xints-before-assignment bug).
- Vertex and edge-boundary points (boundary conditions).
- Multi-polygon dead-zone helper.
"""

import pytest

from app.services.dark_detection import is_in_dead_zone, point_in_polygon


# ── point_in_polygon ──────────────────────────────────────────────────────────

class TestPointInPolygon:
    """Unit tests for the ray-casting point-in-polygon implementation."""

    # A simple unit square: (0,0)→(1,0)→(1,1)→(0,1)→(0,0)
    SQUARE = [[0, 0], [1, 0], [1, 1], [0, 1]]

    def test_point_inside_square(self):
        assert point_in_polygon(0.5, 0.5, self.SQUARE) is True

    def test_point_outside_square(self):
        assert point_in_polygon(2.0, 2.0, self.SQUARE) is False

    def test_point_far_outside(self):
        assert point_in_polygon(-5.0, -5.0, self.SQUARE) is False

    def test_point_on_right_edge(self):
        # Points exactly on edges are implementation-defined; just check no crash.
        result = point_in_polygon(1.0, 0.5, self.SQUARE)
        assert isinstance(result, bool)

    def test_point_on_top_edge(self):
        result = point_in_polygon(0.5, 1.0, self.SQUARE)
        assert isinstance(result, bool)

    # ── Horizontal-edge polygon (regression for the xints bug) ───────────────
    # A rectangle that has explicit horizontal top and bottom edges.
    RECT_WITH_HORIZONTAL_EDGES = [
        [0.0, 0.0],
        [4.0, 0.0],   # bottom horizontal edge
        [4.0, 3.0],
        [0.0, 3.0],   # top horizontal edge
    ]

    def test_interior_rect_horizontal_edges(self):
        """Point clearly inside a rectangle with horizontal edges."""
        assert point_in_polygon(2.0, 1.5, self.RECT_WITH_HORIZONTAL_EDGES) is True

    def test_exterior_rect_horizontal_edges(self):
        """Point clearly outside the same rectangle."""
        assert point_in_polygon(5.0, 1.5, self.RECT_WITH_HORIZONTAL_EDGES) is False

    def test_below_rect_horizontal_edges(self):
        """Point below the bottom horizontal edge."""
        assert point_in_polygon(2.0, -1.0, self.RECT_WITH_HORIZONTAL_EDGES) is False

    def test_above_rect_horizontal_edges(self):
        """Point above the top horizontal edge."""
        assert point_in_polygon(2.0, 4.0, self.RECT_WITH_HORIZONTAL_EDGES) is False

    # ── Regression: xints must not be read from a previous loop iteration ────
    def test_no_unbound_local_error_on_horizontal_edge(self):
        """
        The old code would reference `xints` before assignment when a
        horizontal edge (p1y == p2y) was encountered first in the loop.
        This test exercises exactly that scenario and must not raise any error.
        """
        # Polygon whose first edge is horizontal (y=0 from x=0→x=4)
        poly = [[0.0, 0.0], [4.0, 0.0], [4.0, 2.0], [0.0, 2.0]]
        # The ray from (2.0, 1.0) crosses the first edge (horizontal, y=0)
        # during the very first iteration — old code would use an unset xints.
        try:
            result = point_in_polygon(2.0, 1.0, poly)
        except UnboundLocalError:
            pytest.fail("point_in_polygon read xints before assignment — bug not fixed!")
        assert result is True

    # ── Triangle ──────────────────────────────────────────────────────────────
    TRIANGLE = [[0.0, 0.0], [4.0, 0.0], [2.0, 4.0]]

    def test_point_inside_triangle(self):
        assert point_in_polygon(2.0, 1.0, self.TRIANGLE) is True

    def test_point_outside_triangle(self):
        assert point_in_polygon(3.9, 3.9, self.TRIANGLE) is False


# ── is_in_dead_zone ───────────────────────────────────────────────────────────

class TestIsInDeadZone:
    """Integration-level tests for the dead-zone GeoJSON helper."""

    def _make_feature(self, polygon_coords: list) -> dict:
        """Wrap raw ring coordinates into a minimal GeoJSON Feature."""
        return {
            "geometry": {
                "type": "Polygon",
                "coordinates": [polygon_coords],
            }
        }

    def test_point_inside_dead_zone(self):
        features = [self._make_feature([[0, 0], [2, 0], [2, 2], [0, 2]])]
        assert is_in_dead_zone(1.0, 1.0, features) is True

    def test_point_outside_dead_zone(self):
        features = [self._make_feature([[0, 0], [2, 0], [2, 2], [0, 2]])]
        assert is_in_dead_zone(5.0, 5.0, features) is False

    def test_empty_dead_zones(self):
        assert is_in_dead_zone(0.0, 0.0, []) is False

    def test_multipolygon_dead_zone_inside(self):
        """Point in the second polygon of a MultiPolygon feature."""
        feature = {
            "geometry": {
                "type": "MultiPolygon",
                "coordinates": [
                    [[[10, 10], [12, 10], [12, 12], [10, 12]]],
                    [[[20, 20], [22, 20], [22, 22], [20, 22]]],
                ],
            }
        }
        # 21,21 is inside the second polygon
        assert is_in_dead_zone(21.0, 21.0, [feature]) is True

    def test_multipolygon_dead_zone_outside(self):
        feature = {
            "geometry": {
                "type": "MultiPolygon",
                "coordinates": [
                    [[[10, 10], [12, 10], [12, 12], [10, 12]]],
                ],
            }
        }
        assert is_in_dead_zone(5.0, 5.0, [feature]) is False


# ── _is_coastal_position COUNT-skip optimization ──────────────────────────────

class TestCoastalPositionCountSkip:
    """Regression: _is_coastal_position must not issue a COUNT query when
    PostGIS's ST_DWithin already confirmed a nearby port.
    """

    @pytest.mark.asyncio
    async def test_no_count_query_when_postgis_finds_nearby_port(self):
        """When ST_DWithin returns a row, the COUNT(*) query must be skipped."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock, patch, call

        count_calls = 0

        async def fake_execute(query, *args, **kwargs):
            nonlocal count_calls
            # Detect count query by inspecting the compiled text
            q_str = str(query)
            if "count" in q_str.lower():
                count_calls += 1
                r = MagicMock()
                r.scalar.return_value = 10
                return r

            # ST_DWithin query → return a matching row
            r = MagicMock()
            r.fetchone.return_value = (1,)  # non-None → coastal hit
            return r

        db = AsyncMock()
        db.execute = fake_execute

        with patch("app.services.dark_detection.sa_text" if False else "builtins.open", side_effect=FileNotFoundError):
            pass  # just verify the import works

        from app.services.dark_detection import DarkVesselDetector

        detector = DarkVesselDetector(db)
        # Use a direct call to the private helper
        result = await detector._is_coastal_position(1.3521, 103.8198)

        assert result is True, "Expected True when PostGIS found a nearby port"
        assert count_calls == 0, (
            f"COUNT query was called {count_calls} time(s) but should be 0 "
            "when ST_DWithin already returned a matching row"
        )

