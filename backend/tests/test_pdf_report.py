"""
Unit tests for app.services.pdf_report.
"""

from app.services.pdf_report import _risk_class, _format_num, _jinja_env


class TestPDFReportService:
    def test_risk_class_filter(self):
        assert _risk_class(15) == "risk-low"
        assert _risk_class(45) == "risk-med"
        assert _risk_class(85) == "risk-high"
        assert _risk_class(None) == "risk-unknown"

    def test_format_num_filter(self):
        assert _format_num(12500) == "12,500"
        assert _format_num(None) == "—"
        assert _format_num(0) == "0"

    def test_jinja_filters_registered(self):
        assert "risk_class" in _jinja_env.filters
        assert "format_num" in _jinja_env.filters
