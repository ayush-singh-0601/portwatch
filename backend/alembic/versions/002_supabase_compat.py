"""Supabase-compatible schema — replaces TimescaleDB hypertable with standard table.

This migration supersedes 001_initial when running on Supabase (which does not
support TimescaleDB). It creates all tables using standard PostgreSQL + PostGIS.

Revision ID: 002_supabase_compat
Revises: None
Create Date: 2026-06-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY

# revision identifiers
revision: str = "002_supabase_compat"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Extensions (PostGIS only — no TimescaleDB on Supabase) ─────
    # op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")

    # ── vessels ────────────────────────────────────────────────────
    op.create_table(
        "vessels",
        sa.Column("imo", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("mmsi", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("flag", sa.String(3), nullable=True, comment="ISO 3166-1 alpha-3"),
        sa.Column("vessel_type", sa.String(100), nullable=True),
        sa.Column("gross_tonnage", sa.Integer(), nullable=True),
        sa.Column("dwt", sa.Integer(), nullable=True, comment="Deadweight tonnage"),
        sa.Column("year_built", sa.Integer(), nullable=True),
        sa.Column("call_sign", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("imo"),
        sa.UniqueConstraint("mmsi"),
    )

    # ── vessel_positions (standard table — no hypertable) ──────────
    op.create_table(
        "vessel_positions",
        sa.Column("time", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("mmsi", sa.Integer(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("speed", sa.Float(), nullable=True, comment="Speed over ground (knots)"),
        sa.Column("course", sa.Float(), nullable=True, comment="Course over ground (degrees)"),
        sa.Column("heading", sa.Float(), nullable=True, comment="True heading (degrees)"),
        sa.Column("nav_status", sa.SmallInteger(), nullable=True, comment="AIS navigational status code (0-15)"),
        sa.Column("msg_type", sa.SmallInteger(), nullable=True, comment="AIS message type"),
        sa.PrimaryKeyConstraint("time", "mmsi"),
    )

    # Indexes for positions (standard B-tree, no GIST geography index)
    op.create_index("idx_pos_mmsi_time", "vessel_positions", ["mmsi", sa.text("time DESC")])

    # ── ownership_entities ─────────────────────────────────────────
    op.create_table(
        "ownership_entities",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=True, comment="e.g. company, person, trust, state"),
        sa.Column("country", sa.String(3), nullable=True, comment="ISO 3166-1 alpha-3"),
        sa.Column("registration", sa.Text(), nullable=True, comment="Company registration / incorporation number"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ownership_entities_name", "ownership_entities", ["name"])

    # ── ownership_edges ────────────────────────────────────────────
    op.create_table(
        "ownership_edges",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_entity_id", sa.Integer(), sa.ForeignKey("ownership_entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_entity_id", sa.Integer(), sa.ForeignKey("ownership_entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relationship_type", sa.String(100), nullable=True, comment="e.g. owner, operator, manager, beneficial_owner"),
        sa.Column("vessel_imo", sa.Integer(), sa.ForeignKey("vessels.imo", ondelete="SET NULL"), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── sanctions_entries ──────────────────────────────────────────
    op.create_table(
        "sanctions_entries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source", sa.String(20), nullable=False, comment="OFAC, EU, UN, OFSI"),
        sa.Column("entity_name", sa.String(500), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=True),
        sa.Column("program", sa.String(255), nullable=True),
        sa.Column("list_id", sa.String(100), nullable=True),
        sa.Column("aliases", ARRAY(sa.String()), nullable=True),
        sa.Column("imo_number", sa.String(20), nullable=True),
        sa.Column("last_updated", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sanctions_entries_source", "sanctions_entries", ["source"])
    op.create_index("ix_sanctions_entries_entity_name", "sanctions_entries", ["entity_name"])
    op.create_index("ix_sanctions_entries_imo", "sanctions_entries", ["imo_number"])

    # ── sanctions_matches ──────────────────────────────────────────
    op.create_table(
        "sanctions_matches",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("vessel_imo", sa.Integer(), sa.ForeignKey("vessels.imo", ondelete="CASCADE"), nullable=False),
        sa.Column("matched_entity_id", sa.Integer(), sa.ForeignKey("ownership_entities.id", ondelete="SET NULL"), nullable=True),
        sa.Column("sanctions_entry_id", sa.Integer(), sa.ForeignKey("sanctions_entries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("match_score", sa.Float(), nullable=False, comment="Fuzzy match confidence (0-100)"),
        sa.Column("match_type", sa.String(50), nullable=True, comment="exact, fuzzy, alias, imo"),
        sa.Column("matched_field", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sanctions_matches_vessel", "sanctions_matches", ["vessel_imo"])

    # ── dark_events ────────────────────────────────────────────────
    op.create_table(
        "dark_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("vessel_imo", sa.Integer(), sa.ForeignKey("vessels.imo", ondelete="CASCADE"), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("start_lat", sa.Float(), nullable=False),
        sa.Column("start_lon", sa.Float(), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_lat", sa.Float(), nullable=True),
        sa.Column("end_lon", sa.Float(), nullable=True),
        sa.Column("duration_hours", sa.Float(), nullable=True),
        sa.Column("zone_type", sa.String(50), nullable=True, comment="coastal or open_ocean"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dark_events_vessel", "dark_events", ["vessel_imo"])

    # ── sts_events ─────────────────────────────────────────────────
    op.create_table(
        "sts_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("vessel_a_imo", sa.Integer(), sa.ForeignKey("vessels.imo", ondelete="CASCADE"), nullable=False),
        sa.Column("vessel_b_imo", sa.Integer(), sa.ForeignKey("vessels.imo", ondelete="CASCADE"), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("min_distance_m", sa.Float(), nullable=True),
        sa.Column("duration_minutes", sa.Float(), nullable=True),
        sa.Column("in_port_limits", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── risk_scores ────────────────────────────────────────────────
    op.create_table(
        "risk_scores",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("vessel_imo", sa.Integer(), sa.ForeignKey("vessels.imo", ondelete="CASCADE"), nullable=False),
        sa.Column("total_score", sa.Integer(), nullable=False, comment="0-100"),
        sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_risk_scores_vessel", "risk_scores", ["vessel_imo"])

    # ── risk_factors ───────────────────────────────────────────────
    op.create_table(
        "risk_factors",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("risk_score_id", sa.Integer(), sa.ForeignKey("risk_scores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("factor_name", sa.String(200), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("evidence_description", sa.Text(), nullable=True),
        sa.Column("evidence_link", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── port_calls ─────────────────────────────────────────────────
    op.create_table(
        "port_calls",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("vessel_imo", sa.Integer(), sa.ForeignKey("vessels.imo", ondelete="CASCADE"), nullable=False),
        sa.Column("port_name", sa.String(255), nullable=False),
        sa.Column("port_country", sa.String(3), nullable=False),
        sa.Column("unlocode", sa.String(10), nullable=True),
        sa.Column("arrival_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("departure_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("psc_detention", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("psc_deficiencies", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_port_calls_vessel", "port_calls", ["vessel_imo"])


def downgrade() -> None:
    op.drop_table("port_calls")
    op.drop_table("risk_factors")
    op.drop_table("risk_scores")
    op.drop_table("sts_events")
    op.drop_table("dark_events")
    op.drop_table("sanctions_matches")
    op.drop_table("sanctions_entries")
    op.drop_table("ownership_edges")
    op.drop_table("ownership_entities")
    op.drop_table("vessel_positions")
    op.drop_table("vessels")
