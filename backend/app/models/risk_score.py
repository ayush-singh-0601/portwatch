"""
SQLAlchemy models for composite risk scoring.

- ``RiskScore`` — aggregate risk score (0-100) for a vessel.
- ``RiskFactor`` — individual factor contributing to the total score.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class RiskScore(Base):
    """Composite risk score for a vessel at a point in time."""

    __tablename__ = "risk_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    vessel_imo: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("vessels.imo", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    total_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Aggregate risk score from 0 (low) to 100 (critical)",
    )
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    factors: Mapped[list["RiskFactor"]] = relationship(
        "RiskFactor",
        back_populates="risk_score",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    vessel: Mapped["Vessel"] = relationship(  # noqa: F821
        "Vessel",
        back_populates="risk_scores",
    )

    def __repr__(self) -> str:
        return f"<RiskScore(id={self.id}, vessel_imo={self.vessel_imo}, score={self.total_score})>"


class RiskFactor(Base):
    """Individual factor contributing to a vessel's risk score."""

    __tablename__ = "risk_factors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    risk_score_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("risk_scores.id", ondelete="CASCADE"),
        nullable=False,
    )
    factor_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="e.g. sanctions_match, dark_activity, sts_transfer, flag_risk",
    )
    points: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Points contributed to the total score",
    )
    evidence_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Human-readable description of the evidence",
    )
    evidence_link: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="URL or reference to the supporting evidence",
    )

    # Relationships
    risk_score: Mapped["RiskScore"] = relationship(
        "RiskScore",
        back_populates="factors",
    )

    def __repr__(self) -> str:
        return f"<RiskFactor(id={self.id}, name={self.factor_name!r}, pts={self.points})>"
