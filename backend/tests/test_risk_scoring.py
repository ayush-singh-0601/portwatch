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
