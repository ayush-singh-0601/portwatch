"""
SQLAlchemy model for AIS "dark" (transponder-off) events.

A dark event is recorded when a vessel's AIS signal disappears for
a duration exceeding a configurable threshold (typically > 6 hours).
"""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class DarkEvent(Base):
    """Period when a vessel's AIS transponder was not transmitting."""

    __tablename__ = "dark_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    vessel_imo: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("vessels.imo", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Start of the dark period
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    start_lat: Mapped[float] = mapped_column(Float, nullable=False)
    start_lon: Mapped[float] = mapped_column(Float, nullable=False)

    # End of the dark period (null if still ongoing)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    end_lon: Mapped[float | None] = mapped_column(Float, nullable=True)

    duration_hours: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Duration of the dark period in hours",
    )
    zone_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="coastal or open_ocean",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    vessel: Mapped["Vessel"] = relationship(  # noqa: F821
        "Vessel",
        back_populates="dark_events",
    )

    def __repr__(self) -> str:
        return (
            f"<DarkEvent(id={self.id}, vessel_imo={self.vessel_imo}, "
            f"duration_h={self.duration_hours})>"
        )
