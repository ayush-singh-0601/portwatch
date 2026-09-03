"""
Unit tests for app.services.ofac_parser.
"""

from app.services.ofac_parser import normalize_text, _strip_ns, SDNEntity


class TestOFACParser:
    def test_normalize_text_whitespace(self):
        assert normalize_text("  OCEAN   MARITIME  LTD  ") == "OCEAN MARITIME LTD"
        assert normalize_text(None) == ""
        assert normalize_text("") == ""

    def test_strip_ns_tag(self):
        tag = "{https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/ENHANCED}sdnEntry"
        assert _strip_ns(tag) == "sdnEntry"
        assert _strip_ns("simpleTag") == "simpleTag"

    def test_sdn_entity_defaults(self):
        entity = SDNEntity(source_id="123", entity_name="TEST SHIP", entity_type="vessel")
        assert entity.source_id == "123"
        assert entity.aliases == []
        assert entity.imo_number is None
