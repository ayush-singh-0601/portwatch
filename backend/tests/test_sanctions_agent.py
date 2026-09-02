"""
Unit tests for app.agents.sanctions (SanctionsScreeningAgent).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.agents.sanctions import FUZZY_THRESHOLD, SanctionsScreeningAgent
from app.models.sanctions import SanctionsEntry


class _FakeSanctionsEntry:
    def __init__(self, eid, name, source="OFAC", imo=None, program="SDGT"):
        self.id = eid
        self.entity_name = name
        self.source = source
        self.imo_number = imo
        self.program = program


class _FakeVessel:
    def __init__(self, imo=9123456, name="SEPAHAN STAR"):
        self.imo = imo
        self.name = name


class _FakeOwnershipEntity:
    def __init__(self, eid, name):
        self.id = eid
        self.name = name


class _FakeEdge:
    def __init__(self, sid, tid, vessel_imo=9123456):
        self.source_entity_id = sid
        self.target_entity_id = tid
        self.vessel_imo = vessel_imo


@pytest.mark.asyncio
class TestSanctionsScreeningAgent:
    async def test_make_match_structure(self):
        db = AsyncMock()
        agent = SanctionsScreeningAgent(db)
        entry = _FakeSanctionsEntry(1, "SEPAHAN OIL CO", "OFAC", "9123456")
        match = agent._make_match(
            entry=entry,
            score=100.0,
            match_type="exact_imo",
            matched_field="imo_number",
            matched_name="SEPAHAN STAR",
        )
        assert match["sanctions_entry_id"] == 1
        assert match["sanctions_name"] == "SEPAHAN OIL CO"
        assert match["match_score"] == 100.0
        assert match["match_type"] == "exact_imo"

    async def test_find_entry_by_name(self):
        db = AsyncMock()
        agent = SanctionsScreeningAgent(db)
        entries = [
            _FakeSanctionsEntry(1, "SEPAHAN OIL CO"),
            _FakeSanctionsEntry(2, "NATIONAL IRANIAN TANKER CO"),
        ]
        found = agent._find_entry_by_name(entries, "Sepahan Oil Co")
        assert found is not None
        assert found.id == 1

        not_found = agent._find_entry_by_name(entries, "Nonexistent Corp")
        assert not_found is None

    async def test_cache_invalidation(self):
        db = AsyncMock()
        agent = SanctionsScreeningAgent(db)
        agent._sanctions_cache = [_FakeSanctionsEntry(1, "TEST")]
        assert agent._sanctions_cache is not None
        agent.invalidate_cache()
        assert agent._sanctions_cache is None

    async def test_make_match_with_entity_id(self):
        db = AsyncMock()
        agent = SanctionsScreeningAgent(db)
        entry = _FakeSanctionsEntry(2, "NATIONAL IRANIAN TANKER CO", "OFAC")
        match = agent._make_match(
            entry=entry,
            score=95.0,
            match_type="fuzzy",
            matched_field="ownership_entity",
            matched_name="National Iranian Tanker Corp",
            entity_id=42,
        )
        assert match["matched_entity_id"] == 42
        assert match["matched_field"] == "ownership_entity"
        assert match["match_type"] == "fuzzy"

    async def test_make_match_score_clamping(self):
        db = AsyncMock()
        agent = SanctionsScreeningAgent(db)
        entry = _FakeSanctionsEntry(1, "SAMPLE SANCTION")
        
        # Test out of range float rounding/clamping
        match1 = agent._make_match(entry, 105.0, "exact", "name", "sample")
        assert match1["match_score"] == 100.0

        match2 = agent._make_match(entry, 87.6543, "fuzzy", "name", "sample")
        assert match2["match_score"] == 87.65


