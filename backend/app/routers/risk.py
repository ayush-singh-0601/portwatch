"""
Risk scoring endpoints.

Routes::

    GET   /api/vessels/{imo}/risk            — current risk score + breakdown
    POST  /api/vessels/{imo}/risk/calculate   — trigger risk recalculation
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.dark_event import DarkEvent
from app.models.risk_score import RiskFactor, RiskScore
from app.models.sanctions import SanctionsMatch
from app.models.sts_event import STSEvent
from app.models.vessel import Vessel
from app.schemas.risk import RiskFactorResponse, RiskScoreResponse

router = APIRouter(prefix="/api/vessels", tags=["Risk"])


@router.get(
    "/{imo}/risk",
    response_model=RiskScoreResponse,
    summary="Get current risk score and breakdown",
)
async def get_risk_score(
    imo: int,
    db: AsyncSession = Depends(get_db),
) -> RiskScoreResponse:
    """Return the latest risk score and factor breakdown for a vessel.

    Raises:
        HTTPException 404: If the vessel or risk score does not exist.
    """
    # Verify vessel
    vessel_result = await db.execute(select(Vessel).where(Vessel.imo == imo))
    vessel = vessel_result.scalar_one_or_none()

    if vessel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vessel with IMO {imo} not found",
        )

    # Get latest risk score with factors
    score_result = await db.execute(
        select(RiskScore)
        .where(RiskScore.vessel_imo == imo)
        .options(selectinload(RiskScore.factors))
        .order_by(RiskScore.calculated_at.desc())
        .limit(1)
    )
    risk_score = score_result.scalar_one_or_none()

    if risk_score is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No risk score found for vessel IMO {imo}. Trigger a calculation first.",
        )

    return RiskScoreResponse(
        id=risk_score.id,
        vessel_imo=risk_score.vessel_imo,
        total_score=risk_score.total_score,
        calculated_at=risk_score.calculated_at,
        factors=[RiskFactorResponse.model_validate(f) for f in risk_score.factors],
        risk_level=RiskScoreResponse.classify_risk(risk_score.total_score),
    )


@router.post(
    "/{imo}/risk/calculate",
    response_model=RiskScoreResponse,
    summary="Trigger risk score recalculation",
)
async def calculate_risk(
    imo: int,
    db: AsyncSession = Depends(get_db),
) -> RiskScoreResponse:
    """Recalculate the risk score for a vessel based on current data.

    Scoring factors:
    - Sanctions matches (up to 40 points)
    - Dark activity events (up to 25 points)
    - STS transfer events (up to 20 points)
    - Flag risk (up to 15 points)

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

    factors: list[RiskFactor] = []
    total = 0

    # ── Factor 1: Sanctions matches ────────────────────────────────
    sanctions_result = await db.execute(
        select(SanctionsMatch).where(SanctionsMatch.vessel_imo == imo)
    )
    sanctions_matches = list(sanctions_result.scalars().all())

    if sanctions_matches:
        best_score = max(m.match_score for m in sanctions_matches)
        points = min(40, int(best_score * 0.4))
        total += points
        factors.append(
            RiskFactor(
                factor_name="sanctions_match",
                points=points,
                evidence_description=(
                    f"{len(sanctions_matches)} sanctions match(es) found, "
                    f"highest confidence: {best_score:.1f}%"
                ),
            )
        )

    # ── Factor 2: Dark activity ────────────────────────────────────
    dark_result = await db.execute(
        select(DarkEvent).where(DarkEvent.vessel_imo == imo)
    )
    dark_events = list(dark_result.scalars().all())

    if dark_events:
        total_hours = sum(e.duration_hours or 0 for e in dark_events)
        points = min(25, len(dark_events) * 8 + int(total_hours / 24) * 2)
        total += points
        factors.append(
            RiskFactor(
                factor_name="dark_activity",
                points=points,
                evidence_description=(
                    f"{len(dark_events)} AIS dark event(s), "
                    f"total dark time: {total_hours:.1f} hours"
                ),
            )
        )

    # ── Factor 3: STS transfers ────────────────────────────────────
    sts_result = await db.execute(
        select(STSEvent).where(
            (STSEvent.vessel_a_imo == imo) | (STSEvent.vessel_b_imo == imo)
        )
    )
    sts_events = list(sts_result.scalars().all())

    if sts_events:
        open_ocean = sum(1 for e in sts_events if not e.in_port_limits)
        points = min(20, len(sts_events) * 5 + open_ocean * 10)
        total += points
        factors.append(
            RiskFactor(
                factor_name="sts_transfer",
                points=points,
                evidence_description=(
                    f"{len(sts_events)} STS transfer(s) detected, "
                    f"{open_ocean} in open ocean"
                ),
            )
        )

    # ── Factor 4: Flag risk ────────────────────────────────────────
    HIGH_RISK_FLAGS = {"CMR", "TGO", "TZA", "PLW", "COM", "GNQ", "BOL", "MDG", "SLE", "VUT"}
    if vessel.flag and vessel.flag.upper() in HIGH_RISK_FLAGS:
        points = 15
        total += points
        factors.append(
            RiskFactor(
                factor_name="flag_risk",
                points=points,
                evidence_description=(
                    f"Vessel flagged to {vessel.flag}, which is on the "
                    f"Paris MoU grey/black list"
                ),
            )
        )

    # Cap total at 100
    total = min(100, total)

    # Persist
    risk_score = RiskScore(
        vessel_imo=imo,
        total_score=total,
        calculated_at=datetime.now(timezone.utc),
        factors=factors,
    )
    db.add(risk_score)
    await db.commit()
    await db.refresh(risk_score)

    return RiskScoreResponse(
        id=risk_score.id,
        vessel_imo=risk_score.vessel_imo,
        total_score=risk_score.total_score,
        calculated_at=risk_score.calculated_at,
        factors=[RiskFactorResponse.model_validate(f) for f in risk_score.factors],
        risk_level=RiskScoreResponse.classify_risk(risk_score.total_score),
    )
