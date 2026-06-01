"""
SQLAlchemy models for sanctions screening.

- ``SanctionsEntry`` — consolidated sanctions list entries
  (OFAC SDN, EU, UN, OFSI).
- ``SanctionsMatch`` — records linking a vessel to a matched
  sanctions entity with confidence scores.
"""

from datetime import datetime

from sqlalchemy import ARRAY, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class SanctionsEntry(Base):
    """A single entry from a sanctions list (OFAC / EU / UN / OFSI)."""

    __tablename__ = "sanctions_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    source: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment="Sanctions list source: OFAC, EU, UN, OFSI",
    )
    entity_name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    entity_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="e.g. vessel, individual, organization",
    )
    program: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Sanctions program / regime",
    )
    list_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Source-specific entry identifier",
    )
    aliases: Mapped[list[str] | None] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="Known aliases / alternative names",
    )
    imo_number: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        index=True,
        comment="IMO number if the entity is a vessel",
    )
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    matches: Mapped[list["SanctionsMatch"]] = relationship(
        "SanctionsMatch",
        back_populates="sanctions_entry",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<SanctionsEntry(id={self.id}, source={self.source!r}, name={self.entity_name!r})>"


class SanctionsMatch(Base):
    """Association between a vessel and a sanctions entry with match metadata."""

    __tablename__ = "sanctions_matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    vessel_imo: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("vessels.imo", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    matched_entity_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("ownership_entities.id", ondelete="SET NULL"),
        nullable=True,
        comment="Ownership entity that triggered the match (if applicable)",
    )
    sanctions_entry_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sanctions_entries.id", ondelete="CASCADE"),
        nullable=False,
    )
    match_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Fuzzy match confidence score (0-100)",
    )
    match_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="exact, fuzzy, alias, imo",
    )
    matched_field: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Field that triggered the match: name, alias, imo_number",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    vessel: Mapped["Vessel"] = relationship(  # noqa: F821
        "Vessel",
        back_populates="sanctions_matches",
    )
    sanctions_entry: Mapped["SanctionsEntry"] = relationship(
        "SanctionsEntry",
        back_populates="matches",
    )

    def __repr__(self) -> str:
        return (
            f"<SanctionsMatch(id={self.id}, vessel_imo={self.vessel_imo}, "
            f"score={self.match_score})>"
        )
