"""Add ports reference table for geospatial proximity queries.

Revision ID: 003_add_ports_table
Revises: 002_supabase_compat
Create Date: 2026-08-19
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_add_ports_table"
down_revision: Union[str, None] = "002_supabase_compat"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("unlocode", sa.String(length=10), nullable=True, comment="UN/LOCODE e.g. SGSIN, NLRTM"),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("country", sa.String(length=3), nullable=True, comment="ISO 3166-1 alpha-3"),
        sa.Column("latitude", sa.Float(), nullable=False, comment="WGS-84 latitude, decimal degrees"),
        sa.Column("longitude", sa.Float(), nullable=False, comment="WGS-84 longitude, decimal degrees"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ports_unlocode", "ports", ["unlocode"], unique=True)
    op.create_index("ix_ports_country", "ports", ["country"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ports_country", table_name="ports")
    op.drop_index("ix_ports_unlocode", table_name="ports")
    op.drop_table("ports")
