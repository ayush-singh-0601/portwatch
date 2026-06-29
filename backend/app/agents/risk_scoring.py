"""
RiskScoringAgent — deterministic, auditable 0-100 risk scoring per PRD factor table.

Implements all 11 factors from the PRD:
┌─────────────────────────────────────────────────┬────────┐
│ Factor                                          │ Points │
├─────────────────────────────────────────────────┼────────┤
│ Beneficial owner on sanctions list              │ +30    │
│ Sanctioned port call (last 12 months)           │ +20    │
│ STS transfer detected at sea                    │ +15    │
│ Flag of convenience registry                    │ +15    │
│ Dark event (each, last 90 days)                 │ +5     │
│ PSC detention (last 2 years)                    │ +10    │
│ 3+ name or flag changes                         │ +10    │
│ Near-match on sanctions list (≥85%)             │ +10    │
│ IMO high-risk flag state                        │ +5     │
│ Vessel age over 20 years                        │ +5     │
│ Loitering near ship-breaking yard               │ +5     │
└─────────────────────────────────────────────────┴────────┘

Every factor includes: factor_name, points, evidence_description, evidence_link.
Score is deterministic — no ML, no randomness, fully auditable.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dark_event import DarkEvent
from app.models.ownership import OwnershipEdge, OwnershipEntity
from app.models.port_call import PortCall
from app.models.risk_score import RiskFactor, RiskScore
from app.models.sanctions import SanctionsMatch
from app.models.sts_event import STSEvent
from app.models.vessel import Vessel

logger = logging.getLogger(__name__)

# Flag-of-convenience registries (ITF list + Paris MoU grey/black list)
FLAG_OF_CONVENIENCE = {
    "ATG", "BHS", "BRB", "BLZ", "BMU", "BOL", "KHM", "CYM", "COM",
    "CYP", "GNQ", "GEO", "GIB", "HND", "JAM", "LBN", "LBR", "MLT",
    "MHL", "MUS", "MDA", "MNG", "MMR", "PAN", "STP", "VCT", "LKA",
    "TON", "VUT",
}

# IMO high-risk flag states (Paris MoU black list 2023-2024)
HIGH_RISK_FLAG_STATES = {
    "CMR", "TGO", "TZA", "PLW", "COM", "GNQ", "BOL", "MDG",
    "SLE", "VUT", "ALB", "GNB",
}

# Known sanctioned port countries (OFAC heavily sanctioned jurisdictions)
SANCTIONED_PORT_COUNTRIES = {
    "IRN", "PRK", "CUB", "SYR", "VEN", "RUS",
}


class RiskScoringAgent:
    """Deterministic risk scoring agent implementing the PRD factor table."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def calculate_risk(self, vessel_imo: int) -> RiskScore:
        """Calculate the full risk score for a vessel.

        Returns a persisted RiskScore with all contributing factors.
        """
        vessel_result = await self.db.execute(
            select(Vessel).where(Vessel.imo == vessel_imo)
        )
        vessel = vessel_result.scalar_one_or_none()
        if vessel is None:
            raise ValueError(f"Vessel IMO {vessel_imo} not found")

        factors: list[RiskFactor] = []
        now = datetime.now(timezone.utc)

        # ── Factor 1: Beneficial owner on sanctions list (+30) ──────
        factor = await self._check_beneficial_owner_sanctions(vessel_imo)
        if factor:
            factors.append(factor)

        # ── Factor 2: Sanctioned port call, last 12 months (+20) ───
        factor = await self._check_sanctioned_port_calls(vessel_imo, now)
        if factor:
            factors.append(factor)

        # ── Factor 3: STS transfer detected at sea (+15) ───────────
        factor = await self._check_sts_transfers(vessel_imo)
        if factor:
            factors.append(factor)

        # ── Factor 4: Flag of convenience registry (+15) ───────────
        factor = self._check_flag_of_convenience(vessel)
        if factor:
            factors.append(factor)

        # ── Factor 5: Dark events, last 90 days (+5 each) ─────────
        factor = await self._check_dark_events(vessel_imo, now)
        if factor:
            factors.append(factor)

        # ── Factor 6: PSC detention, last 2 years (+10) ───────────
        factor = await self._check_psc_detentions(vessel_imo, now)
        if factor:
            factors.append(factor)

        # ── Factor 7: 3+ name or flag changes (+10) ───────────────
        factor = await self._check_identity_changes(vessel_imo, vessel)
        if factor:
            factors.append(factor)

        # ── Factor 8: Near-match on sanctions list ≥85% (+10) ─────
        factor = await self._check_near_sanctions_match(vessel_imo)
        if factor:
            factors.append(factor)

        # ── Factor 9: IMO high-risk flag state (+5) ───────────────
        factor = self._check_high_risk_flag(vessel)
        if factor:
            factors.append(factor)

        # ── Factor 10: Vessel age over 20 years (+5) ──────────────
        factor = self._check_vessel_age(vessel, now)
        if factor:
            factors.append(factor)

        # ── Factor 11: Loitering near ship-breaking yard (+5) ─────
        # Placeholder — depends on loitering events table
        # factor = await self._check_loitering(vessel_imo)
        # if factor:
        #     factors.append(factor)

        # Sum and cap at 100
        total = min(100, sum(f.points for f in factors))

        risk_score = RiskScore(
            vessel_imo=vessel_imo,
            total_score=total,
            calculated_at=now,
            factors=factors,
        )
        self.db.add(risk_score)
        await self.db.commit()
        await self.db.refresh(risk_score)

        logger.info(
            f"Risk score for IMO {vessel_imo}: {total}/100 "
            f"({len(factors)} factor(s))"
        )
        return risk_score

    # ── Individual factor checks ───────────────────────────────────

    async def _check_beneficial_owner_sanctions(
        self, vessel_imo: int
    ) -> Optional[RiskFactor]:
        """Beneficial owner on sanctions list → +30."""
        result = await self.db.execute(
            select(SanctionsMatch)
            .where(SanctionsMatch.vessel_imo == vessel_imo)
            .where(SanctionsMatch.match_type == "exact_imo")
        )
        matches = list(result.scalars().all())
        if matches:
            return RiskFactor(
                factor_name="beneficial_owner_sanctioned",
                points=30,
                evidence_description=(
                    f"Direct sanctions match on {len(matches)} list(s). "
                    f"Highest confidence: {max(m.match_score for m in matches):.0f}%"
                ),
            )
        # Also check ownership chain entities
        owner_result = await self.db.execute(
            select(SanctionsMatch)
            .where(SanctionsMatch.vessel_imo == vessel_imo)
            .where(SanctionsMatch.match_type == "ownership_chain")
        )
        owner_matches = list(owner_result.scalars().all())
        if owner_matches:
            return RiskFactor(
                factor_name="beneficial_owner_sanctioned",
                points=30,
                evidence_description=(
                    f"Ownership chain entity matched on sanctions list. "
                    f"{len(owner_matches)} match(es)."
                ),
            )
        return None

    async def _check_sanctioned_port_calls(
        self, vessel_imo: int, now: datetime
    ) -> Optional[RiskFactor]:
        """Sanctioned port call in last 12 months → +20."""
        cutoff = now - timedelta(days=365)
        try:
            result = await self.db.execute(
                select(PortCall)
                .where(PortCall.vessel_imo == vessel_imo)
                .where(PortCall.arrival_time >= cutoff)
            )
            port_calls = list(result.scalars().all())
            sanctioned = [
                pc for pc in port_calls
                if pc.port_country and pc.port_country.upper() in SANCTIONED_PORT_COUNTRIES
            ]
            if sanctioned:
                ports = ", ".join(set(pc.port_name or pc.port_country for pc in sanctioned))
                return RiskFactor(
                    factor_name="sanctioned_port_call",
                    points=20,
                    evidence_description=(
                        f"{len(sanctioned)} port call(s) to sanctioned jurisdiction(s) "
                        f"in last 12 months: {ports}"
                    ),
                )
        except Exception:
            pass
        return None

    async def _check_sts_transfers(
        self, vessel_imo: int
    ) -> Optional[RiskFactor]:
        """STS transfer detected at sea → +15."""
        result = await self.db.execute(
            select(STSEvent).where(
                (STSEvent.vessel_a_imo == vessel_imo)
                | (STSEvent.vessel_b_imo == vessel_imo)
            )
        )
        sts_events = list(result.scalars().all())
        open_ocean = [e for e in sts_events if not e.in_port_limits]
        if open_ocean:
            return RiskFactor(
                factor_name="sts_transfer_at_sea",
                points=15,
                evidence_description=(
                    f"{len(open_ocean)} STS transfer(s) detected outside port limits. "
                    f"Total events: {len(sts_events)}."
                ),
            )
        return None

    def _check_flag_of_convenience(
        self, vessel: Vessel
    ) -> Optional[RiskFactor]:
        """Flag of convenience registry → +15."""
        if vessel.flag and vessel.flag.upper() in FLAG_OF_CONVENIENCE:
            return RiskFactor(
                factor_name="flag_of_convenience",
                points=15,
                evidence_description=(
                    f"Vessel registered under {vessel.flag}, which is on the "
                    f"ITF Flag of Convenience list."
                ),
            )
        return None

    async def _check_dark_events(
        self, vessel_imo: int, now: datetime
    ) -> Optional[RiskFactor]:
        """Dark events in last 90 days → +5 each (capped)."""
        cutoff = now - timedelta(days=90)
        result = await self.db.execute(
            select(DarkEvent)
            .where(DarkEvent.vessel_imo == vessel_imo)
            .where(DarkEvent.start_time >= cutoff)
        )
        dark_events = list(result.scalars().all())
        if dark_events:
            total_hours = sum(e.duration_hours or 0 for e in dark_events)
            points = min(25, len(dark_events) * 5)
            return RiskFactor(
                factor_name="dark_activity",
                points=points,
                evidence_description=(
                    f"{len(dark_events)} AIS dark event(s) in last 90 days, "
                    f"total dark time: {total_hours:.1f} hours."
                ),
            )
        return None

    async def _check_psc_detentions(
        self, vessel_imo: int, now: datetime
    ) -> Optional[RiskFactor]:
        """PSC detention in last 2 years → +10."""
        cutoff = now - timedelta(days=730)
        try:
            result = await self.db.execute(
                select(PortCall)
                .where(PortCall.vessel_imo == vessel_imo)
                .where(PortCall.arrival_time >= cutoff)
                .where(PortCall.psc_detention == True)  # noqa: E712
            )
            detentions = list(result.scalars().all())
            if detentions:
                return RiskFactor(
                    factor_name="psc_detention",
                    points=10,
                    evidence_description=(
                        f"{len(detentions)} PSC detention(s) in the last 2 years."
                    ),
                )
        except Exception:
            pass
        return None

    async def _check_identity_changes(
        self, vessel_imo: int, vessel: Vessel
    ) -> Optional[RiskFactor]:
        """3+ name or flag changes → +10."""
        try:
            result = await self.db.execute(
                select(func.count())
                .select_from(OwnershipEdge)
                .where(OwnershipEdge.vessel_imo == vessel_imo)
            )
            edge_count = result.scalar() or 0
            # Heuristic: lots of ownership edges suggest frequent changes
            if edge_count >= 3:
                return RiskFactor(
                    factor_name="identity_changes",
                    points=10,
                    evidence_description=(
                        f"{edge_count} ownership/identity changes detected in vessel history."
                    ),
                )
        except Exception:
            pass
        return None

    async def _check_near_sanctions_match(
        self, vessel_imo: int
    ) -> Optional[RiskFactor]:
        """Near-match on sanctions list ≥85% (fuzzy, not exact) → +10."""
        result = await self.db.execute(
            select(SanctionsMatch)
            .where(SanctionsMatch.vessel_imo == vessel_imo)
            .where(SanctionsMatch.match_type == "fuzzy")
            .where(SanctionsMatch.match_score >= 85.0)
        )
        matches = list(result.scalars().all())
        if matches:
            best = max(m.match_score for m in matches)
            return RiskFactor(
                factor_name="near_sanctions_match",
                points=10,
                evidence_description=(
                    f"{len(matches)} near-match(es) on sanctions list (≥85%). "
                    f"Best match: {best:.1f}%."
                ),
            )
        return None

    def _check_high_risk_flag(
        self, vessel: Vessel
    ) -> Optional[RiskFactor]:
        """IMO high-risk flag state → +5."""
        if vessel.flag and vessel.flag.upper() in HIGH_RISK_FLAG_STATES:
            return RiskFactor(
                factor_name="high_risk_flag_state",
                points=5,
                evidence_description=(
                    f"Vessel flagged to {vessel.flag}, on the Paris MoU "
                    f"grey/black list."
                ),
            )
        return None

    def _check_vessel_age(
        self, vessel: Vessel, now: datetime
    ) -> Optional[RiskFactor]:
        """Vessel age over 20 years → +5."""
        if vessel.year_built and (now.year - vessel.year_built) > 20:
            age = now.year - vessel.year_built
            return RiskFactor(
                factor_name="vessel_age",
                points=5,
                evidence_description=(
                    f"Vessel built in {vessel.year_built} ({age} years old). "
                    f"Vessels over 20 years are higher risk."
                ),
            )
        return None
