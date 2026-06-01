"""
SQLAlchemy model for Ship-to-Ship (STS) transfer events.

An STS event is detected when two vessels remain within close
proximity (configurable, e.g. < 500 m) for a sustained period.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class STSEvent(Base):
    """Detected Ship-to-Ship transfer event between two vessels."""

    __tablename__ = "sts_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    vessel_a_imo: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("vessels.imo", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vessel_b_imo: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("vessels.imo", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    min_distance_m: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Minimum distance between vessels in metres",
    )
    duration_minutes: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Duration of the STS event in minutes",
    )
    in_port_limits: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether the STS occurred within port limits",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<STSEvent(id={self.id}, "
            f"vessel_a={self.vessel_a_imo}, vessel_b={self.vessel_b_imo})>"
        )
