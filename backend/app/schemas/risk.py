"""
Pydantic schemas for risk scoring responses.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class RiskFactorResponse(BaseModel):
    """Individual risk factor in a vessel's score breakdown."""

    id: int
    factor_name: str
    points: int = Field(..., ge=0, description="Points contributed to the total score")
    evidence_description: str | None = None
    evidence_link: str | None = None

    model_config = {"from_attributes": True}


class RiskScoreResponse(BaseModel):
    """Current risk score with full factor breakdown."""

    id: int
    vessel_imo: int
    total_score: int = Field(..., ge=0, le=100, description="Composite risk score 0-100")
    calculated_at: datetime
    factors: list[RiskFactorResponse] = Field(default_factory=list)
    risk_level: str = Field(
        ...,
        description="Human-readable risk level: low / medium / high / critical",
    )

    model_config = {"from_attributes": True}

    @staticmethod
    def classify_risk(score: int) -> str:
        """Return a human-readable risk level for a given numeric score.

        Args:
            score: Risk score from 0 to 100.

        Returns:
            One of ``low``, ``medium``, ``high``, ``critical``.
        """
        if score < 25:
            return "low"
        if score < 50:
            return "medium"
        if score < 75:
            return "high"
        return "critical"


class RiskHistoryResponse(BaseModel):
    """Historical risk scores for trend analysis."""

    vessel_imo: int
    scores: list[RiskScoreResponse]
    total: int = Field(..., ge=0)
