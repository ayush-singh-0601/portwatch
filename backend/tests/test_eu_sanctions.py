"""
Unit tests for app.services.eu_sanctions.
"""

from xml.etree.ElementTree import Element, SubElement
from app.services.eu_sanctions import _normalize, _find_text


class TestEUSanctionsParser:
    def test_normalize_whitespace(self):
        assert _normalize("  EU   SANCTIONS   ENTRY  ") == "EU SANCTIONS ENTRY"
        assert _normalize(None) == ""

    def test_find_text_helper(self):
        root = Element("entity")
        child = SubElement(root, "name")
        child.text = "  SOVCOMFLOT  "
        assert _find_text(root, "name") == "SOVCOMFLOT"
        assert _find_text(root, "missing") == ""
