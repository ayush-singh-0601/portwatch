"""
Sanctions screening endpoints.

Routes::

    GET   /api/vessels/{imo}/sanctions  — get existing sanctions matches
    POST  /api/vessels/{imo}/screen     — trigger fresh screening
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.sanctions import SanctionsEntry, SanctionsMatch
from app.models.vessel import Vessel

router = APIRouter(prefix="/api/vessels", tags=["Sanctions"])


# ── Response schemas (endpoint-specific) ───────────────────────────
class SanctionsEntryBrief(BaseModel):
    """Abbreviated sanctions entry for match responses."""

    id: int
    source: str
    entity_name: str
    entity_type: str | None = None
    program: str | None = None
    list_id: str | None = None

    model_config = {"from_attributes": True}


class SanctionsMatchResponse(BaseModel):
    """A single sanctions match result."""

    id: int
    vessel_imo: int
    match_score: float
    match_type: str | None = None
    matched_field: str | None = None
    sanctions_entry: SanctionsEntryBrief

    model_config = {"from_attributes": True}


class SanctionsScreeningResponse(BaseModel):
    """Full sanctions screening response for a vessel."""

    vessel_imo: int
    vessel_name: str
    matches: list[SanctionsMatchResponse]
    total_matches: int
    highest_score: float | None = None
    is_sanctioned: bool = Field(
        False, description="True if any match exceeds the confidence threshold"
    )


class ScreeningTriggerResponse(BaseModel):
    """Response after triggering a fresh screening."""

    vessel_imo: int
    status: str = "completed"
    new_matches_found: int = 0
    matches: list[SanctionsMatchResponse] = Field(default_factory=list)


# ── Endpoints ──────────────────────────────────────────────────────


@router.get(
    "/{imo}/sanctions",
    response_model=SanctionsScreeningResponse,
    summary="Get sanctions screening results",
)
async def get_sanctions(
    imo: int,
    db: AsyncSession = Depends(get_db),
) -> SanctionsScreeningResponse:
    """Return all existing sanctions matches for a vessel.

    Raises:
        HTTPException 404: If the vessel does not exist.
    """
    # Verify vessel
    vessel_result = await db.execute(select(Vessel).where(Vessel.imo == imo))
    vessel = vessel_result.scalar_one_or_none()

    if vessel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vessel with IMO {imo} not found",
        )

    # Fetch matches with eager-loaded sanctions entries
    matches_result = await db.execute(
        select(SanctionsMatch)
        .where(SanctionsMatch.vessel_imo == imo)
        .options(selectinload(SanctionsMatch.sanctions_entry))
        .order_by(SanctionsMatch.match_score.desc())
    )
    matches = list(matches_result.scalars().all())

    highest = max((m.match_score for m in matches), default=None)

    return SanctionsScreeningResponse(
        vessel_imo=imo,
        vessel_name=vessel.name,
        matches=[
            SanctionsMatchResponse(
                id=m.id,
                vessel_imo=m.vessel_imo,
                match_score=m.match_score,
                match_type=m.match_type,
                matched_field=m.matched_field,
                sanctions_entry=SanctionsEntryBrief.model_validate(m.sanctions_entry),
            )
            for m in matches
        ],
        total_matches=len(matches),
        highest_score=highest,
        is_sanctioned=highest is not None and highest >= 85.0,
    )


@router.post(
    "/{imo}/screen",
    response_model=ScreeningTriggerResponse,
    summary="Trigger fresh sanctions screening",
)
async def screen_vessel(
    imo: int,
    db: AsyncSession = Depends(get_db),
) -> ScreeningTriggerResponse:
    """Run a fresh sanctions screening against all active sanctions lists.

    This endpoint:
    1. Fetches the vessel and its ownership entities.
    2. Runs multi-stage fuzzy and exact screening (IMO, vessel name, ownership chain).
    3. Persists screening matches with full deduplication.

    Raises:
        HTTPException 404: If the vessel does not exist.
    """
    from app.agents.sanctions import SanctionsScreeningAgent

    # Verify vessel
    vessel_result = await db.execute(select(Vessel).where(Vessel.imo == imo))
    vessel = vessel_result.scalar_one_or_none()

    if vessel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vessel with IMO {imo} not found",
        )

    agent = SanctionsScreeningAgent(db)
    raw_matches = await agent.screen_vessel(imo)
    await agent.save_matches(imo, raw_matches)

    # Load with sanctions_entry relationships
    matches_result = await db.execute(
        select(SanctionsMatch)
        .where(SanctionsMatch.vessel_imo == imo)
        .options(selectinload(SanctionsMatch.sanctions_entry))
        .order_by(SanctionsMatch.match_score.desc())
    )
    loaded_matches = list(matches_result.scalars().all())

    response_matches = [
        SanctionsMatchResponse(
            id=m.id,
            vessel_imo=m.vessel_imo,
            match_score=m.match_score,
            match_type=m.match_type,
            matched_field=m.matched_field,
            sanctions_entry=SanctionsEntryBrief.model_validate(m.sanctions_entry),
        )
        for m in loaded_matches
    ]

    return ScreeningTriggerResponse(
        vessel_imo=imo,
        status="completed",
        new_matches_found=len(response_matches),
        matches=response_matches,
    )
