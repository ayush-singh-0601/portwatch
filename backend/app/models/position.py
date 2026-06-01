"""
SQLAlchemy model for the ``vessel_positions`` TimescaleDB hypertable.

Stores time-series AIS position reports (message types 1/2/3/18/19).
The ``time`` + ``mmsi`` columns form the composite primary key.

.. note::

    The PostGIS ``GEOGRAPHY(POINT, 4326)`` column (``geog``) is added via
    a raw-SQL Alembic migration rather than the ORM, because async
    SQLAlchemy does not natively support GeoAlchemy2 column DDL.
"""

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, SmallInteger, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class VesselPosition(Base):
    """A single AIS position report for a vessel."""

    __tablename__ = "vessel_positions"

    # Composite primary key: time + mmsi
    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        primary_key=True,
        server_default=func.now(),
    )
    mmsi: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)

    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    speed: Mapped[float | None] = mapped_column(Float, nullable=True, comment="Speed over ground (knots)")
    course: Mapped[float | None] = mapped_column(Float, nullable=True, comment="Course over ground (degrees)")
    heading: Mapped[float | None] = mapped_column(Float, nullable=True, comment="True heading (degrees)")

    nav_status: Mapped[int | None] = mapped_column(
        SmallInteger,
        nullable=True,
        comment="AIS navigational status code (0-15)",
    )
    msg_type: Mapped[int | None] = mapped_column(
        SmallInteger,
        nullable=True,
        comment="AIS message type that produced this report",
    )

    def __repr__(self) -> str:
        return (
            f"<VesselPosition(time={self.time!r}, mmsi={self.mmsi}, "
            f"lat={self.latitude}, lon={self.longitude})>"
        )
