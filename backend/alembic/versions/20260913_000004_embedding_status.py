"""Add embedding_status, embedding_failure_reason, and embedding_attempts to vehicle_observations.

Revision ID: 20260913_000004
Revises: 20260906_000003
Create Date: 2026-09-13 18:25:00.000000

Changes:
- vehicle_observations: add embedding_status (pending/complete/failed), embedding_failure_reason, embedding_attempts
- Backfill existing records based on whether appearance_embedding is populated
- Add index on embedding_status
"""

from alembic import op
import sqlalchemy as sa


revision = "20260913_000004"
down_revision = "20260906_000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add columns with safe defaults
    op.add_column(
        "vehicle_observations",
        sa.Column("embedding_status", sa.String(length=20), nullable=False, server_default="pending"),
    )
    op.add_column(
        "vehicle_observations",
        sa.Column("embedding_failure_reason", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "vehicle_observations",
        sa.Column("embedding_attempts", sa.Integer(), nullable=False, server_default="0"),
    )

    # 2. Add index for fast querying by embedding status
    op.create_index(
        "ix_vehicle_obs_embedding_status",
        "vehicle_observations",
        ["embedding_status"],
        unique=False,
    )

    # 3. Backfill existing historical records
    op.execute("""
        UPDATE vehicle_observations
        SET embedding_status = 'complete', embedding_attempts = 1
        WHERE appearance_embedding IS NOT NULL AND jsonb_typeof(appearance_embedding) = 'array';
    """)
    op.execute("""
        UPDATE vehicle_observations
        SET embedding_status = 'failed', embedding_failure_reason = 'historical_crop_unavailable', embedding_attempts = 1
        WHERE appearance_embedding IS NULL OR jsonb_typeof(appearance_embedding) != 'array';
    """)


def downgrade() -> None:
    op.drop_index("ix_vehicle_obs_embedding_status", table_name="vehicle_observations")
    op.drop_column("vehicle_observations", "embedding_attempts")
    op.drop_column("vehicle_observations", "embedding_failure_reason")
    op.drop_column("vehicle_observations", "embedding_status")
