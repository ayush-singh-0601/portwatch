"""
Unit tests for app.services.name_matcher — Unicode normalization and fuzzy matching.
"""

import pytest

from app.services.name_matcher import (
    MatchResult,
    NameMatcher,
    batch_match,
    match_entity,
    normalize_name,
)


class TestNormalizeName:
    def test_basic_lowercase(self):
        assert normalize_name("OCEAN EXPLORER") == "ocean explorer"

    def test_unicode_accents_stripped(self):
        assert (
            normalize_name("SOCIÉTÉ MARITIME D'INVESTISSEMENT")
            == "societe maritime dinvestissement"
        )

    def test_punctuation_and_symbols_stripped(self):
        assert normalize_name("Al-Quds Corp., Ltd.") == "alquds corp ltd"

    def test_multiple_spaces_collapsed(self):
        assert normalize_name("  PACIFIC   SHIPPING   CO  ") == "pacific shipping co"

    def test_empty_and_none_handled(self):
        assert normalize_name("") == ""
        assert normalize_name(None) == ""

    def test_ligature_nfkd_decomposition(self):
        # 'ﬁ' ligature decomposes to 'fi'
        assert normalize_name("Pacific Transport ﬁ") == "pacific transport fi"

    def test_strip_legal_suffixes(self):
        from app.services.name_matcher import strip_legal_suffixes
        assert strip_legal_suffixes("Oceanic Shipping Ltd") == "Oceanic Shipping"
        assert strip_legal_suffixes("Meridian Tankers Corp.") == "Meridian Tankers"
        assert strip_legal_suffixes("Pacific Carriers LLC") == "Pacific Carriers"
        assert strip_legal_suffixes("Global Logistics S.A.") == "Global Logistics"
        assert strip_legal_suffixes("Singapore Marine Pte Ltd") == "Singapore Marine"

    def test_normalize_with_strip_suffixes(self):
        assert normalize_name("Oceanic Shipping Ltd", strip_suffixes=True) == "oceanic shipping"
        assert normalize_name("Meridian Tankers Corp.", strip_suffixes=True) == "meridian tankers"



class TestMatchEntity:
    def test_exact_match(self):
        sanctions = ["SEPAHAN OIL CO", "NATIONAL IRANIAN TANKER CO", "ISLAMIC REPUBLIC OF IRAN SHIPPING LINES"]
        results = match_entity("Sepahan Oil Co", sanctions, threshold=85.0)
        assert len(results) >= 1
        assert results[0].matched_name == "SEPAHAN OIL CO"
        assert results[0].score >= 99.0
        assert results[0].match_type == "exact"

    def test_fuzzy_match(self):
        sanctions = ["PETROCHEMICAL COMMERCIAL COMPANY INTERNATIONAL LTD"]
        results = match_entity("Petrochemical Commercial Co Intl Ltd", sanctions, threshold=75.0)
        assert len(results) >= 1
        assert results[0].matched_name == "PETROCHEMICAL COMMERCIAL COMPANY INTERNATIONAL LTD"
        assert results[0].score >= 75.0
        assert results[0].match_type in ("exact", "fuzzy")

    def test_no_match_below_threshold(self):
        sanctions = ["SEPAHAN OIL CO"]
        results = match_entity("EVERGREEN MARINE CORP", sanctions, threshold=85.0)
        assert len(results) == 0

    def test_empty_inputs_return_empty_list(self):
        assert match_entity("", ["SANCTIONED INC"]) == []
        assert match_entity("VESSEL", []) == []


class TestBatchMatch:
    def test_batch_match_multiple_entities(self):
        queries = ["Sepahan Oil", "Random Cargo Co"]
        sanctions = ["SEPAHAN OIL CO", "OTHER SANCTIONED ENTITY"]
        results = batch_match(queries, sanctions, threshold=80.0)
        assert "Sepahan Oil" in results
        assert len(results["Sepahan Oil"]) >= 1
        assert results["Sepahan Oil"][0].matched_name == "SEPAHAN OIL CO"

    def test_batch_match_empty_inputs(self):
        assert batch_match([], ["SANCTIONED"]) == {}
        assert batch_match(["QUERY"], []) == {}


class TestNameMatcherClass:
    def test_instance_methods(self):
        matcher = NameMatcher(threshold=85.0)
        sanctions = ["SEPAHAN OIL CO"]
        res = matcher.match_entity("Sepahan Oil Co", sanctions)
        assert len(res) >= 1

        exact = NameMatcher.exact_match("Sepahan Oil Co", sanctions)
        assert "SEPAHAN OIL CO" in exact
