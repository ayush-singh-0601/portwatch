"""
SQLAlchemy model for the ``vessels`` table.

Stores static vessel information typically sourced from AIS
messages types 5 / 24 and external registries (e.g. Equasis, IHS).
"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Vessel(Base):
    """A maritime vessel identified by its IMO number."""

    __tablename__ = "vessels"

    # IMO number — 7-digit unique identifier issued by the IMO.
    imo: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)

    # Maritime Mobile Service Identity — 9-digit, unique per radio installation.
    mmsi: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    flag: Mapped[str | None] = mapped_column(String(3), nullable=True, comment="ISO 3166-1 alpha-3")
    vessel_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    gross_tonnage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dwt: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="Deadweight tonnage")
    year_built: Mapped[int | None] = mapped_column(Integer, nullable=True)
    call_sign: Mapped[str | None] = mapped_column(String(20), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ── Relationships ──────────────────────────────────────────────
    risk_scores: Mapped[list["RiskScore"]] = relationship(  # noqa: F821
        "RiskScore",
        back_populates="vessel",
        lazy="selectin",
    )
    dark_events: Mapped[list["DarkEvent"]] = relationship(  # noqa: F821
        "DarkEvent",
        back_populates="vessel",
        lazy="selectin",
    )
    port_calls: Mapped[list["PortCall"]] = relationship(  # noqa: F821
        "PortCall",
        back_populates="vessel",
        lazy="selectin",
    )
    sanctions_matches: Mapped[list["SanctionsMatch"]] = relationship(  # noqa: F821
        "SanctionsMatch",
        back_populates="vessel",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Vessel(imo={self.imo}, name={self.name!r})>"
