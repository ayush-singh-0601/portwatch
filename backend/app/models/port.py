"""
SQLAlchemy model for the ``ports`` reference table.

Stores a lightweight registry of world ports used exclusively for
geospatial proximity queries (coastal detection, port-limit checks,
and risk-zone proximity).  No vessel FK — purely a read-only
reference dataset.
"""

from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Port(Base):
    """A maritime port identified by its UN/LOCODE."""

    __tablename__ = "ports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # UN/LOCODE -- e.g. "SGSIN", "NLRTM".  Should be unique where known.
    unlocode: Mapped[str | None] = mapped_column(
        String(10),
        unique=True,
        nullable=True,
        index=True,
        comment="UN/LOCODE e.g. SGSIN, NLRTM",
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # ISO 3166-1 alpha-3 country code
    country: Mapped[str | None] = mapped_column(
        String(3),
        nullable=True,
        index=True,
        comment="ISO 3166-1 alpha-3",
    )

    # WGS-84 decimal degrees
    latitude: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="WGS-84 latitude, decimal degrees",
    )
    longitude: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="WGS-84 longitude, decimal degrees",
    )

    def __repr__(self) -> str:
        return f"<Port(unlocode={self.unlocode!r}, name={self.name!r})>"
