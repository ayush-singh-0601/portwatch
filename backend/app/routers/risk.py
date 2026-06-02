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

from app.agents.risk_scoring import RiskScoringAgent
from app.database import get_db
from app.models.risk_score import RiskFactor, RiskScore
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
    """Recalculate the risk score for a vessel using the full 11-factor PRD table.

    Factors evaluated (deterministic, auditable):
    - Beneficial owner on sanctions list (+30)
    - Sanctioned port call in last 12 months (+20)
    - STS transfer at sea (+15)
    - Flag of convenience (+15)
    - Dark events in last 90 days (+5 each, max 25)
    - PSC detention in last 2 years (+10)
    - 3+ name/flag changes (+10)
    - Near-match on sanctions list ≥85% (+10)
    - IMO high-risk flag state (+5)
    - Vessel age over 20 years (+5)
    - Loitering near ship-breaking yard (+5)

    Raises:
        HTTPException 404: If the vessel does not exist.
    """
    # Verify vessel exists
    vessel_result = await db.execute(select(Vessel).where(Vessel.imo == imo))
    vessel = vessel_result.scalar_one_or_none()

    if vessel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vessel with IMO {imo} not found",
        )

    agent = RiskScoringAgent(db)
    risk_score = await agent.calculate_risk(imo)

    return RiskScoreResponse(
        id=risk_score.id,
        vessel_imo=risk_score.vessel_imo,
        total_score=risk_score.total_score,
        calculated_at=risk_score.calculated_at,
        factors=[RiskFactorResponse.model_validate(f) for f in risk_score.factors],
        risk_level=RiskScoreResponse.classify_risk(risk_score.total_score),
    )

