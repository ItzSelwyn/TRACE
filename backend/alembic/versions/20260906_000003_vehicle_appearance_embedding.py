"""Add appearance_embedding JSONB column to vehicle_observations.

Revision ID: 20260906_000003
Revises: 20260906_000002
Create Date: 2026-09-06 15:30:00.000000

Changes:
- vehicle_observations: add appearance_embedding JSONB NULLABLE column
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260906_000003"
down_revision = "20260906_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "vehicle_observations",
        sa.Column("appearance_embedding", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("vehicle_observations", "appearance_embedding")
