"""
SanctionsScreeningAgent — screens vessels and ownership chains against
OFAC, EU, UN, and OFSI sanctions lists using multi-stage matching.

Matching stages:
    1. Exact IMO number match (instant, zero false positives)
    2. Exact normalized vessel/entity name match
    3. Fuzzy match via rapidfuzz token_sort_ratio ≥ 85%
    4. Ownership chain entity screening
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sanctions import SanctionsEntry, SanctionsMatch
from app.models.vessel import Vessel
from app.models.ownership import OwnershipEntity, OwnershipEdge
from app.services.name_matcher import NameMatcher, MatchResult

logger = logging.getLogger(__name__)

# Threshold for fuzzy matching — per PRD spec, defensible to regulators
FUZZY_THRESHOLD = 85.0


class SanctionsScreeningAgent:
    """Screens vessels and their ownership chains against sanctions lists.

    Usage::

        agent = SanctionsScreeningAgent(db_session)
        results = await agent.screen_vessel(imo=9811000)
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.matcher = NameMatcher(threshold=FUZZY_THRESHOLD)
        self._sanctions_cache: list[SanctionsEntry] | None = None

    async def _load_sanctions_list(self) -> list[SanctionsEntry]:
        """Load all sanctions entries from the database (cached)."""
        if self._sanctions_cache is None:
            result = await self.db.execute(select(SanctionsEntry))
            self._sanctions_cache = list(result.scalars().all())
            logger.info("Loaded %d sanctions entries", len(self._sanctions_cache))
        return self._sanctions_cache

    def invalidate_cache(self) -> None:
        """Force reload of sanctions list on next screening."""
        self._sanctions_cache = None

    async def screen_vessel(self, imo: int) -> list[dict]:
        """Run full sanctions screening on a vessel and its ownership chain.

        Args:
            imo: IMO number of the vessel to screen.

        Returns:
            List of match dicts with keys: sanctions_entry_id, match_score,
            match_type, matched_field, matched_entity_name, sanctions_name,
            sanctions_source.
        """
        # Load vessel
        vessel = await self.db.get(Vessel, imo)
        if not vessel:
            logger.warning("Vessel IMO %d not found", imo)
            return []

        sanctions = await self._load_sanctions_list()
        if not sanctions:
            logger.warning("No sanctions entries loaded — screening skipped")
            return []

        all_matches: list[dict] = []

        # ── Stage 1: Exact IMO match ─────────────────────────────
        imo_str = str(vessel.imo)
        for entry in sanctions:
            if entry.imo_number and str(entry.imo_number).strip() == imo_str:
                all_matches.append(self._make_match(
                    entry=entry,
                    score=100.0,
                    match_type="exact_imo",
                    matched_field="imo_number",
                    matched_name=vessel.name,
                ))

        # ── Stage 2: Exact name match ────────────────────────────
        sanctions_names = [e.entity_name for e in sanctions]
        exact_matches = self.matcher.exact_match(vessel.name, sanctions_names)
        for matched_name in exact_matches:
            entry = self._find_entry_by_name(sanctions, matched_name)
            if entry:
                all_matches.append(self._make_match(
                    entry=entry,
                    score=100.0,
                    match_type="exact_name",
                    matched_field="vessel_name",
                    matched_name=vessel.name,
                ))

        # ── Stage 3: Fuzzy name match on vessel ──────────────────
        fuzzy_results = self.matcher.match_entity(vessel.name, sanctions_names)
        for result in fuzzy_results:
            # Skip if already matched exactly
            if any(m["match_type"] in ("exact_imo", "exact_name")
                   and m["sanctions_name"] == result.matched_name
                   for m in all_matches):
                continue
            entry = self._find_entry_by_name(sanctions, result.matched_name)
            if entry:
                all_matches.append(self._make_match(
                    entry=entry,
                    score=result.score,
                    match_type="fuzzy",
                    matched_field="vessel_name",
                    matched_name=vessel.name,
                ))

        # ── Stage 4: Ownership chain screening ───────────────────
        ownership_matches = await self._screen_ownership_chain(imo, sanctions)
        all_matches.extend(ownership_matches)

        # Deduplicate by (sanctions_entry_id, matched_field)
        seen = set()
        unique_matches = []
        for m in all_matches:
            key = (m["sanctions_entry_id"], m["matched_field"], m.get("matched_entity_name"))
            if key not in seen:
                seen.add(key)
                unique_matches.append(m)

        logger.info(
            "Vessel IMO %d: %d sanctions match(es) found",
            imo, len(unique_matches),
        )

        return unique_matches

    async def _screen_ownership_chain(
        self, vessel_imo: int, sanctions: list[SanctionsEntry]
    ) -> list[dict]:
        """Screen all entities in the vessel's ownership chain."""
        matches = []

        # Get ownership edges for this vessel
        result = await self.db.execute(
            select(OwnershipEdge).where(OwnershipEdge.vessel_imo == vessel_imo)
        )
        edges = list(result.scalars().all())

        if not edges:
            return matches

        # Collect all entity IDs
        entity_ids = set()
        for edge in edges:
            entity_ids.add(edge.source_entity_id)
            entity_ids.add(edge.target_entity_id)

        # Load entities
        result = await self.db.execute(
            select(OwnershipEntity).where(OwnershipEntity.id.in_(entity_ids))
        )
        entities = list(result.scalars().all())

        sanctions_names = [e.entity_name for e in sanctions]

        # Screen each ownership entity
        for entity in entities:
            fuzzy_results = self.matcher.match_entity(entity.name, sanctions_names)
            for result_match in fuzzy_results:
                entry = self._find_entry_by_name(sanctions, result_match.matched_name)
                if entry:
                    matches.append(self._make_match(
                        entry=entry,
                        score=result_match.score,
                        match_type=result_match.match_type,
                        matched_field="ownership_entity",
                        matched_name=entity.name,
                        entity_id=entity.id,
                    ))

        return matches

    async def save_matches(self, vessel_imo: int, matches: list[dict]) -> list[SanctionsMatch]:
        """Persist screening results to the database.

        Clears previous matches for the vessel before inserting new ones.
        """
        # Clear old matches
        from sqlalchemy import delete
        await self.db.execute(
            delete(SanctionsMatch).where(SanctionsMatch.vessel_imo == vessel_imo)
        )

        db_matches = []
        for m in matches:
            db_match = SanctionsMatch(
                vessel_imo=vessel_imo,
                matched_entity_id=m.get("matched_entity_id"),
                sanctions_entry_id=m["sanctions_entry_id"],
                match_score=m["match_score"],
                match_type=m["match_type"],
                matched_field=m["matched_field"],
            )
            self.db.add(db_match)
            db_matches.append(db_match)

        await self.db.commit()
        logger.info("Saved %d sanctions matches for vessel IMO %d", len(db_matches), vessel_imo)
        return db_matches

    def _make_match(
        self,
        entry: SanctionsEntry,
        score: float,
        match_type: str,
        matched_field: str,
        matched_name: str,
        entity_id: int | None = None,
    ) -> dict:
        """Build a standardized match result dict."""
        return {
            "sanctions_entry_id": entry.id,
            "sanctions_name": entry.entity_name,
            "sanctions_source": entry.source,
            "sanctions_program": entry.program,
            "match_score": score,
            "match_type": match_type,
            "matched_field": matched_field,
            "matched_entity_name": matched_name,
            "matched_entity_id": entity_id,
        }

    def _find_entry_by_name(
        self, sanctions: list[SanctionsEntry], name: str
    ) -> SanctionsEntry | None:
        """Find a sanctions entry by exact entity name."""
        for entry in sanctions:
            if entry.entity_name == name:
                return entry
        return None
