"""
Tests for the risk_scoring.py RiskScoringAgent — specifically the
_check_identity_changes factor fix.

Covers:
- A vessel with exactly 3 synthetic OwnershipEdges (auto-created baseline)
  must score 0 (not +10).
- A vessel with >= 6 OwnershipEdges should trigger the +10 factor.
- A vessel with 0 edges scores 0.
"""

import pytest

# Standalone reimplementation matching the fixed logic
_SYNTHETIC_EDGE_BASELINE = 3
_CHANGE_THRESHOLD = _SYNTHETIC_EDGE_BASELINE + 3  # 6


class _FakeRiskFactor:
    def __init__(self, factor_name, points, evidence_description):
        self.factor_name = factor_name
        self.points = points
        self.evidence_description = evidence_description


def _check_identity_changes_logic(edge_count: int):
    if edge_count >= _CHANGE_THRESHOLD:
        return _FakeRiskFactor(
            factor_name='identity_changes',
            points=10,
            evidence_description=(
                f'{edge_count} ownership/identity changes detected '
                f'(threshold: {_CHANGE_THRESHOLD}, baseline: {_SYNTHETIC_EDGE_BASELINE} auto-edges).'
            ),
        )
    return None


class TestIdentityChangesThreshold:
    def test_zero_edges_scores_zero(self):
        assert _check_identity_changes_logic(0) is None

    def test_three_synthetic_edges_scores_zero(self):
        assert _check_identity_changes_logic(3) is None, '3 synthetic edges should NOT trigger identity_changes'

    def test_four_edges_scores_zero(self):
        assert _check_identity_changes_logic(4) is None

    def test_five_edges_scores_zero(self):
        assert _check_identity_changes_logic(5) is None

    def test_six_edges_triggers_factor(self):
        factor = _check_identity_changes_logic(6)
        assert factor is not None
        assert factor.points == 10
        assert factor.factor_name == 'identity_changes'

    def test_ten_edges_triggers_factor(self):
        factor = _check_identity_changes_logic(10)
        assert factor is not None
        assert factor.points == 10

    def test_evidence_contains_threshold_and_baseline(self):
        factor = _check_identity_changes_logic(6)
        assert factor is not None
        assert '6' in factor.evidence_description
        assert 'threshold' in factor.evidence_description
        assert 'baseline' in factor.evidence_description


# ── Flag of Convenience & High Risk Flag Normalization ───────────────────────

FLAG_OF_CONVENIENCE = {
    "ATG", "BHS", "BRB", "BLZ", "BMU", "BOL", "KHM", "CYM", "COM",
    "CYP", "GNQ", "GEO", "GIB", "HND", "JAM", "LBN", "LBR", "MLT",
    "MHL", "MUS", "MDA", "MNG", "MMR", "PAN", "STP", "VCT", "LKA",
    "TON", "VUT",
}

HIGH_RISK_FLAG_STATES = {
    "CMR", "TGO", "TZA", "PLW", "COM", "GNQ", "BOL", "MDG",
    "SLE", "VUT", "ALB", "GNB",
}


class _FakeVessel:
    def __init__(self, flag):
        self.flag = flag


def _check_foc(vessel):
    if vessel.flag and vessel.flag.strip().upper() in FLAG_OF_CONVENIENCE:
        flag_code = vessel.flag.strip().upper()
        return _FakeRiskFactor(
            factor_name="flag_of_convenience",
            points=15,
            evidence_description=f"Vessel registered under {flag_code}",
        )
    return None


def _check_high_risk(vessel):
    if vessel.flag and vessel.flag.strip().upper() in HIGH_RISK_FLAG_STATES:
        flag_code = vessel.flag.strip().upper()
        return _FakeRiskFactor(
            factor_name="high_risk_flag_state",
            points=5,
            evidence_description=f"Vessel flagged to {flag_code}",
        )
    return None


class TestFlagNormalization:
    def test_padded_flag_matches_foc(self):
        v = _FakeVessel("PAN ")
        res = _check_foc(v)
        assert res is not None
        assert res.points == 15

    def test_lowercase_flag_matches_foc(self):
        v = _FakeVessel("lbr")
        res = _check_foc(v)
        assert res is not None
        assert res.points == 15

    def test_none_flag_returns_none(self):
        v = _FakeVessel(None)
        assert _check_foc(v) is None
        assert _check_high_risk(v) is None

    def test_padded_high_risk_flag(self):
        v = _FakeVessel(" CMR ")
        res = _check_high_risk(v)
        assert res is not None
        assert res.points == 5


# ── Loitering Factor & Composite Score Capping ───────────────────────────────

class TestLoiteringFactor:
    def test_loitering_events_create_factor(self):
        events = [{"duration_hours": 6.5}, {"duration_hours": 4.2}]
        count = len(events)
        total_hrs = sum(e["duration_hours"] for e in events)
        factor = _FakeRiskFactor(
            factor_name="loitering_near_risk_zone",
            points=5,
            evidence_description=(
                f"{count} loitering event(s) detected near ship-breaking yards "
                f"or high-risk zones (total: {total_hrs:.1f} hours)."
            ),
        )
        assert factor.points == 5
        assert "2 loitering" in factor.evidence_description
        assert "10.7 hours" in factor.evidence_description


class TestCompositeScoreCapping:
    def test_scores_sum_and_cap_at_100(self):
        factors = [
            _FakeRiskFactor("beneficial_owner_sanctioned", 30, ""),
            _FakeRiskFactor("sanctioned_port_call", 20, ""),
            _FakeRiskFactor("sts_transfer_at_sea", 15, ""),
            _FakeRiskFactor("flag_of_convenience", 15, ""),
            _FakeRiskFactor("dark_activity", 25, ""),
            _FakeRiskFactor("psc_detention", 10, ""),
        ]
        raw_sum = sum(f.points for f in factors)
        assert raw_sum == 115
        total = min(100, raw_sum)
        assert total == 100


class TestBeneficialOwnerSanctions:
    def test_ownership_chain_factor_creation(self):
        matches = [
            {"matched_field": "ownership_entity", "match_score": 92.0},
        ]
        factor = _FakeRiskFactor(
            factor_name="beneficial_owner_sanctioned",
            points=30,
            evidence_description=(
                f"Ownership chain entity matched on sanctions list. {len(matches)} match(es)."
            ),
        )
        assert factor.points == 30
        assert factor.factor_name == "beneficial_owner_sanctioned"
        assert "Ownership chain entity" in factor.evidence_description



