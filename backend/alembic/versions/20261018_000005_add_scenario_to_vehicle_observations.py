"""Add scenario to vehicle_observations.

Revision ID: 20261018_000005
Revises: 20260913_000004
Create Date: 2026-10-18 21:16:00.000000

Changes:
- vehicle_observations: add scenario (Text, default 'S05')
- Add index on scenario
"""

from alembic import op
import sqlalchemy as sa


revision = "20261018_000005"
down_revision = "20260913_000004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add scenario column with safe default
    op.add_column(
        "vehicle_observations",
        sa.Column("scenario", sa.Text(), nullable=False, server_default="S05"),
    )

    # 2. Add index for fast scenario-based queries
    op.create_index(
        "ix_vehicle_obs_scenario",
        "vehicle_observations",
        ["scenario"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_vehicle_obs_scenario", table_name="vehicle_observations")
    op.drop_column("vehicle_observations", "scenario")
