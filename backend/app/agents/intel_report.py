"""
IntelReportAgent — gathers all vessel intelligence and renders a PDF report.

Workflow:
1. Query vessel identity from database
2. Fetch ownership chain (entities + edges)
3. Gather sanctions screening results
4. Collect dark events and STS events
5. Get latest risk score + factor breakdown
6. Collect port call history
7. (Optional) Generate LLM narrative for executive summary and actions
8. Render Jinja2 HTML template with all gathered data
9. Convert to PDF via WeasyPrint
10. Return download path
"""

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.dark_event import DarkEvent
from app.models.ownership import OwnershipEdge, OwnershipEntity
from app.models.port_call import PortCall
from app.models.risk_score import RiskScore
from app.models.sanctions import SanctionsMatch
from app.models.sts_event import STSEvent
from app.models.vessel import Vessel
from app.services.pdf_report import generate_report_pdf, render_html

logger = logging.getLogger(__name__)

# Output directory for generated reports
REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


class IntelReportAgent:
    """Agent that gathers intelligence and produces a PDF report for a vessel."""

    def __init__(self, db: AsyncSession, llm_client=None):
        """
        Args:
            db: Async database session.
            llm_client: Optional LLM client for narrative generation.
                        Must implement `async generate(prompt: str) -> str`.
        """
        self.db = db
        self.llm_client = llm_client

    async def generate_report(
        self,
        vessel_imo: int,
        sections: Optional[list[str]] = None,
        output_format: str = "pdf",
    ) -> dict:
        """Generate a complete intelligence report for a vessel.

        Args:
            vessel_imo: IMO number of the vessel.
            sections: List of section identifiers to include.
            output_format: 'pdf' or 'html'.

        Returns:
            Dict with report_id, filepath, file_size_bytes, generated_at.
        """
        if sections is None:
            sections = [
                "executive_summary",
                "vessel_profile",
                "ownership_structure",
                "sanctions_screening",
                "risk_assessment",
                "dark_activity",
                "port_history",
            ]

        report_id = str(uuid.uuid4())
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        logger.info(f"Generating intel report for IMO {vessel_imo} (ID: {report_id[:8]})")

        # ── 1. Gather vessel identity ──────────────────────────
        vessel = await self._get_vessel(vessel_imo)
        if vessel is None:
            raise ValueError(f"Vessel IMO {vessel_imo} not found")

        # ── 2. Gather ownership chain ──────────────────────────
        ownership_entities = await self._get_ownership(vessel_imo)

        # ── 3. Gather sanctions matches ────────────────────────
        sanctions_matches = await self._get_sanctions(vessel_imo)

        # ── 4. Gather risk score ───────────────────────────────
        risk_score = await self._get_risk_score(vessel_imo)
        risk_level = self._classify_risk(risk_score.total_score if risk_score else 0)

        # ── 5. Gather dark events ──────────────────────────────
        dark_events = await self._get_dark_events(vessel_imo)

        # ── 6. Gather port calls ───────────────────────────────
        port_calls = await self._get_port_calls(vessel_imo)

        # ── 7. Optional LLM narrative ──────────────────────────
        narrative_summary = None
        narrative_actions = None
        if self.llm_client:
            narrative_summary, narrative_actions = await self._generate_narrative(
                vessel, risk_score, sanctions_matches, dark_events
            )

        # ── 8. Build template context ──────────────────────────
        context = {
            "vessel": vessel,
            "report_id": report_id,
            "generated_at": generated_at,
            "sections": sections,
            "ownership_entities": ownership_entities,
            "sanctions_matches": sanctions_matches,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "dark_events": dark_events,
            "port_calls": port_calls,
            "narrative_summary": narrative_summary,
            "narrative_actions": narrative_actions,
        }

        # ── 9. Render and convert ──────────────────────────────
        filename = f"portwatch_report_{vessel_imo}_{report_id[:8]}.{output_format}"
        output_path = REPORTS_DIR / filename

        filepath = generate_report_pdf("intel_report.html", context, output_path)

        file_size = filepath.stat().st_size
        logger.info(
            f"Report generated: {filepath.name} ({file_size} bytes, "
            f"{'PDF' if filepath.suffix == '.pdf' else 'HTML fallback'})"
        )

        return {
            "report_id": report_id,
            "vessel_imo": vessel_imo,
            "filepath": str(filepath),
            "filename": filepath.name,
            "file_size_bytes": file_size,
            "generated_at": generated_at,
            "format": "pdf" if filepath.suffix == ".pdf" else "html",
            "download_url": f"/api/reports/{report_id}",
        }

    # ── Data gathering helpers ─────────────────────────────────

    async def _get_vessel(self, imo: int) -> Optional[Vessel]:
        result = await self.db.execute(select(Vessel).where(Vessel.imo == imo))
        return result.scalar_one_or_none()

    async def _get_ownership(self, imo: int) -> list:
        try:
            result = await self.db.execute(
                select(OwnershipEntity)
                .join(OwnershipEdge, OwnershipEdge.source_entity_id == OwnershipEntity.id)
                .where(OwnershipEdge.vessel_imo == imo)
            )
            return list(result.scalars().all())
        except Exception:
            return []

    async def _get_sanctions(self, imo: int) -> list:
        try:
            result = await self.db.execute(
                select(SanctionsMatch).where(SanctionsMatch.vessel_imo == imo)
            )
            return list(result.scalars().all())
        except Exception:
            return []

    async def _get_risk_score(self, imo: int) -> Optional[RiskScore]:
        try:
            result = await self.db.execute(
                select(RiskScore)
                .where(RiskScore.vessel_imo == imo)
                .options(selectinload(RiskScore.factors))
                .order_by(RiskScore.calculated_at.desc())
                .limit(1)
            )
            return result.scalar_one_or_none()
        except Exception:
            return None

    async def _get_dark_events(self, imo: int) -> list:
        try:
            result = await self.db.execute(
                select(DarkEvent)
                .where(DarkEvent.vessel_imo == imo)
                .order_by(DarkEvent.start_time.desc())
            )
            return list(result.scalars().all())
        except Exception:
            return []

    async def _get_port_calls(self, imo: int) -> list:
        try:
            result = await self.db.execute(
                select(PortCall)
                .where(PortCall.vessel_imo == imo)
                .order_by(PortCall.arrival_time.desc())
                .limit(20)
            )
            return list(result.scalars().all())
        except Exception:
            return []

    @staticmethod
    def _classify_risk(score: int) -> str:
        if score < 25:
            return "low"
        if score < 50:
            return "medium"
        if score < 75:
            return "high"
        return "critical"

    # ── Optional LLM narrative ─────────────────────────────────

    async def _generate_narrative(
        self, vessel, risk_score, sanctions_matches, dark_events
    ) -> tuple[Optional[str], Optional[str]]:
        """Generate narrative prose using an LLM client (if configured).

        Returns:
            Tuple of (executive_summary, recommended_actions) or (None, None).
        """
        if not self.llm_client:
            return None, None

        try:
            # Build structured prompt for the LLM
            prompt = f"""You are a maritime intelligence analyst. Write a concise executive summary
and recommended actions section for a vessel intelligence report.

Vessel: {vessel.name} (IMO {vessel.imo}, flag: {vessel.flag})
Risk Score: {risk_score.total_score if risk_score else 'Not calculated'}/100
Sanctions Matches: {len(sanctions_matches)} match(es)
Dark Events: {len(dark_events)} event(s)

Risk Factors:
{chr(10).join(f'- {f.factor_name}: +{f.points} pts — {f.evidence_description}' for f in (risk_score.factors if risk_score else []))}

Write TWO sections separated by '---':
1. Executive Summary (2-3 sentences, factual, no speculation)
2. Recommended Actions (3-5 bullet points)
"""
            response = await self.llm_client.generate(prompt)
            parts = response.split("---")
            summary = parts[0].strip() if len(parts) >= 1 else None
            actions = parts[1].strip() if len(parts) >= 2 else None
            return summary, actions

        except Exception as e:
            logger.warning(f"LLM narrative generation failed: {e}")
            return None, None
