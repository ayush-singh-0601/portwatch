"""
SQLAlchemy model for port call records.

Port calls are detected from AIS data (geofence matching) or
enriched from external sources such as MarineTraffic or Equasis.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class PortCall(Base):
    """Record of a vessel's visit to a port."""

    __tablename__ = "port_calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    vessel_imo: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("vessels.imo", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    port_name: Mapped[str] = mapped_column(String(255), nullable=False)
    port_country: Mapped[str | None] = mapped_column(
        String(3),
        nullable=True,
        comment="ISO 3166-1 alpha-3",
    )
    unlocode: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        comment="UN/LOCODE e.g. SGSIN, NLRTM",
    )

    arrival_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    departure_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Port State Control (PSC) inspection data
    psc_detention: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether the vessel was detained by PSC",
    )
    psc_deficiencies: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of deficiencies found during PSC inspection",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    vessel: Mapped["Vessel"] = relationship(  # noqa: F821
        "Vessel",
        back_populates="port_calls",
    )

    def __repr__(self) -> str:
        return (
            f"<PortCall(id={self.id}, vessel_imo={self.vessel_imo}, "
            f"port={self.port_name!r})>"
        )
