"""
Unit tests for app.agents.intel_report (IntelReportAgent) and report template rendering.
"""

from unittest.mock import AsyncMock
import pytest

from app.agents.intel_report import IntelReportAgent
from app.services.pdf_report import render_html


class _FakeVessel:
    def __init__(self):
        self.imo = 9988776
        self.mmsi = 123456789
        self.name = "NORDIC GLORY"
        self.flag = "PAN"
        self.vessel_type = "Tanker"
        self.gross_tonnage = 50000
        self.dwt = 85000
        self.year_built = 2012
        self.call_sign = "ABCD"


class _FakeRiskScore:
    def __init__(self, score=65):
        self.total_score = score
        self.factors = []


class TestIntelReportAgentLogic:
    def test_risk_classification(self):
        assert IntelReportAgent._classify_risk(10) == "low"
        assert IntelReportAgent._classify_risk(25) == "medium"
        assert IntelReportAgent._classify_risk(50) == "high"
        assert IntelReportAgent._classify_risk(75) == "critical"
        assert IntelReportAgent._classify_risk(100) == "critical"

    def test_render_html_template_with_context(self):
        vessel = _FakeVessel()
        risk_score = _FakeRiskScore(40)
        context = {
            "vessel": vessel,
            "report_id": "test-uuid-1234",
            "generated_at": "2026-08-26 12:00 UTC",
            "sections": [
                "executive_summary",
                "vessel_profile",
                "ownership_structure",
                "sanctions_screening",
                "risk_assessment",
                "dark_activity",
                "port_history",
            ],
            "ownership_entities": [],
            "sanctions_matches": [],
            "risk_score": risk_score,
            "risk_level": "medium",
            "dark_events": [],
            "port_calls": [],
            "narrative_summary": "Vessel operating normally in coastal waters.",
            "narrative_actions": "Maintain routine quarterly review.",
        }

        html = render_html("intel_report.html", context)
        assert "NORDIC GLORY" in html
        assert "9988776" in html
        assert "MEDIUM" in html
        assert "Executive Summary" in html
