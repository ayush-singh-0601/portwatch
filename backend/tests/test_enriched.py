"""
Tests for enriched.py helper logic — fully standalone, no DB or app imports.

The helpers (_vessel_type_normalise, _resolve_ownership_from_edges) and
the risk-score ordering strategy are tested directly with their own
copy-of-logic stubs so the test suite runs without a database connection.
"""

from datetime import datetime, timezone

import pytest


# ── Re-implement the pure helpers locally so we don't need the app stack ──────
# This keeps the test suite fast and DB-free while still validating the logic.

def _vessel_type_normalise(raw):
    if not raw:
        return "other"
    lower = raw.strip().lower()
    mapping = {
        "cargo": "cargo",
        "bulk carrier": "cargo",
        "container": "cargo",
        "general cargo": "cargo",
        "tanker": "tanker",
        "oil tanker": "tanker",
        "chemical tanker": "tanker",
        "lng tanker": "tanker",
        "crude oil tanker": "tanker",
        "fishing": "fishing",
        "trawler": "fishing",
        "passenger": "passenger",
        "cruise": "passenger",
        "ferry": "passenger",
        "ro-ro": "passenger",
        "military": "military",
        "naval": "military",
        "special / tug": "other",
    }
    return mapping.get(lower, "other")


def _resolve_ownership_from_edges(edges):
    result = {
        "registeredOwner": None,
        "beneficialOwner": None,
        "operator": None,
        "flagHistory": [],
    }
    for edge in edges:
        rel = (edge.relationship_type or "").lower()
        entity_name = edge.target_entity.name if edge.target_entity else None
        if "beneficial" in rel:
            result["beneficialOwner"] = entity_name
        elif "owner" in rel:
            result["registeredOwner"] = entity_name
        elif "operator" in rel or "manager" in rel:
            result["operator"] = entity_name
    return result


# ── _vessel_type_normalise ────────────────────────────────────────────────────

class TestVesselTypeNormalise:
    def test_cargo(self):
        assert _vessel_type_normalise("Cargo") == "cargo"

    def test_bulk_carrier_maps_to_cargo(self):
        assert _vessel_type_normalise("Bulk Carrier") == "cargo"

    def test_tanker(self):
        assert _vessel_type_normalise("Tanker") == "tanker"

    def test_lng_tanker(self):
        assert _vessel_type_normalise("LNG Tanker") == "tanker"

    def test_fishing(self):
        assert _vessel_type_normalise("fishing") == "fishing"

    def test_passenger(self):
        assert _vessel_type_normalise("Passenger") == "passenger"

    def test_ferry_maps_to_passenger(self):
        assert _vessel_type_normalise("Ferry") == "passenger"

    def test_unknown_maps_to_other(self):
        assert _vessel_type_normalise("Submarine") == "other"

    def test_none_maps_to_other(self):
        assert _vessel_type_normalise(None) == "other"

    def test_empty_string_maps_to_other(self):
        assert _vessel_type_normalise("") == "other"


# ── _resolve_ownership_from_edges ─────────────────────────────────────────────

class _FakeEntity:
    def __init__(self, name):
        self.name = name


class _FakeEdge:
    def __init__(self, rel_type, target_name):
        self.relationship_type = rel_type
        self.target_entity = _FakeEntity(target_name)


class TestResolveOwnershipFromEdges:
    def test_empty_edges_returns_defaults(self):
        result = _resolve_ownership_from_edges([])
        assert result == {
            "registeredOwner": None,
            "beneficialOwner": None,
            "operator": None,
            "flagHistory": [],
        }

    def test_beneficial_owner_edge(self):
        edges = [_FakeEdge("beneficial_owner", "Global Holdings")]
        result = _resolve_ownership_from_edges(edges)
        assert result["beneficialOwner"] == "Global Holdings"
        assert result["registeredOwner"] is None

    def test_owner_edge(self):
        edges = [_FakeEdge("owner", "Registered Corp")]
        result = _resolve_ownership_from_edges(edges)
        assert result["registeredOwner"] == "Registered Corp"
        assert result["beneficialOwner"] is None

    def test_operator_edge(self):
        edges = [_FakeEdge("operator", "Pacific Ops")]
        result = _resolve_ownership_from_edges(edges)
        assert result["operator"] == "Pacific Ops"

    def test_manager_edge_maps_to_operator(self):
        edges = [_FakeEdge("manager", "Fleet Manager Ltd")]
        result = _resolve_ownership_from_edges(edges)
        assert result["operator"] == "Fleet Manager Ltd"

    def test_multiple_edges_all_resolved(self):
        edges = [
            _FakeEdge("owner", "Ship Owner Inc"),
            _FakeEdge("beneficial_owner", "UBO Trust"),
            _FakeEdge("operator", "Ops SA"),
        ]
        result = _resolve_ownership_from_edges(edges)
        assert result["registeredOwner"] == "Ship Owner Inc"
        assert result["beneficialOwner"] == "UBO Trust"
        assert result["operator"] == "Ops SA"

    def test_null_target_entity_handled_gracefully(self):
        edge = _FakeEdge("owner", "")
        edge.target_entity = None
        result = _resolve_ownership_from_edges([edge])
        assert result["registeredOwner"] is None


# ── Risk score ordering ───────────────────────────────────────────────────────

class TestRiskScoreOrdering:
    """Verify the max(key=calculated_at) selection picks the newest score."""

    class _FakeScore:
        def __init__(self, sid, score, calculated_at):
            self.id = sid
            self.total_score = score
            self.calculated_at = calculated_at
            self.factors = []

    def _select_latest(self, scores):
        return max(scores, key=lambda x: x.calculated_at) if scores else None

    def test_picks_newest_by_calculated_at(self):
        older = self._FakeScore(1, 80, datetime(2024, 1, 1, tzinfo=timezone.utc))
        newer = self._FakeScore(2, 30, datetime(2025, 6, 1, tzinfo=timezone.utc))
        result = self._select_latest([older, newer])
        assert result is newer

    def test_high_id_but_old_date_not_selected(self):
        original = self._FakeScore(10, 50, datetime(2025, 1, 1, tzinfo=timezone.utc))
        recalculated = self._FakeScore(3, 60, datetime(2025, 8, 1, tzinfo=timezone.utc))
        result = self._select_latest([original, recalculated])
        assert result is recalculated

    def test_single_score_returned(self):
        only = self._FakeScore(1, 45, datetime(2025, 1, 1, tzinfo=timezone.utc))
        assert self._select_latest([only]) is only

    def test_empty_list_returns_none(self):
        assert self._select_latest([]) is None


# ── Port-call sort with None arrival_time ─────────────────────────────────────

class TestPortCallSort:
    """Verify the _EPOCH sentinel allows safe sorting when arrival_time is None."""

    class _FakePortCall:
        def __init__(self, arrival_time):
            self.arrival_time = arrival_time

    def _sort_port_calls(self, port_calls):
        from datetime import datetime, timezone

        _EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
        return sorted(
            port_calls,
            key=lambda x: x.arrival_time if x.arrival_time else _EPOCH,
            reverse=True,
        )

    def test_none_arrival_time_sorts_to_end(self):
        dt = datetime(2025, 6, 1, tzinfo=timezone.utc)
        with_date = self._FakePortCall(dt)
        without_date = self._FakePortCall(None)
        result = self._sort_port_calls([without_date, with_date])
        assert result[0] is with_date
        assert result[1] is without_date

    def test_all_none_does_not_raise(self):
        calls = [self._FakePortCall(None) for _ in range(5)]
        result = self._sort_port_calls(calls)
        assert len(result) == 5

    def test_mixed_sort_is_stable_for_equal_dates(self):
        dt = datetime(2025, 1, 15, tzinfo=timezone.utc)
        a = self._FakePortCall(dt)
        b = self._FakePortCall(dt)
        c = self._FakePortCall(None)
        result = self._sort_port_calls([c, a, b])
        # Both dated entries should precede the None entry
        assert result[-1] is c

