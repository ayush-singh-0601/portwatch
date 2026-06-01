"""
SQLAlchemy models for corporate ownership structures.

Two tables:
- ``ownership_entities`` — companies, persons, trusts, etc.
- ``ownership_edges`` — directed relationships between entities
  (and optionally tied to a vessel via ``vessel_imo``).
"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class OwnershipEntity(Base):
    """A legal entity that can own, operate, or manage vessels."""

    __tablename__ = "ownership_entities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    entity_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="e.g. company, person, trust, state",
    )
    country: Mapped[str | None] = mapped_column(String(3), nullable=True, comment="ISO 3166-1 alpha-3")
    registration: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Company registration / incorporation number",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships: edges originating from this entity
    outgoing_edges: Mapped[list["OwnershipEdge"]] = relationship(
        "OwnershipEdge",
        foreign_keys="OwnershipEdge.source_entity_id",
        back_populates="source_entity",
        lazy="selectin",
    )
    incoming_edges: Mapped[list["OwnershipEdge"]] = relationship(
        "OwnershipEdge",
        foreign_keys="OwnershipEdge.target_entity_id",
        back_populates="target_entity",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<OwnershipEntity(id={self.id}, name={self.name!r})>"


class OwnershipEdge(Base):
    """Directed relationship between two ownership entities.

    Optionally linked to a specific vessel via ``vessel_imo``.
    """

    __tablename__ = "ownership_edges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    source_entity_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ownership_entities.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_entity_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ownership_entities.id", ondelete="CASCADE"),
        nullable=False,
    )

    relationship_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="e.g. owner, operator, manager, beneficial_owner",
    )

    vessel_imo: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("vessels.imo", ondelete="SET NULL"),
        nullable=True,
    )

    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Relationships
    source_entity: Mapped["OwnershipEntity"] = relationship(
        "OwnershipEntity",
        foreign_keys=[source_entity_id],
        back_populates="outgoing_edges",
    )
    target_entity: Mapped["OwnershipEntity"] = relationship(
        "OwnershipEntity",
        foreign_keys=[target_entity_id],
        back_populates="incoming_edges",
    )

    def __repr__(self) -> str:
        return (
            f"<OwnershipEdge(id={self.id}, "
            f"{self.source_entity_id}->{self.target_entity_id}, "
            f"type={self.relationship_type!r})>"
        )
