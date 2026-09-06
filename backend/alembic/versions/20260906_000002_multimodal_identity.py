"""Multi-modal identity fusion: nullable evidence columns + appearance/temporal/camera-transition signals.

Revision ID: 20260906_000002
Revises: 20260830_000001
Create Date: 2026-09-06 14:00:00.000000

Changes:
- identity_matches: make plate_similarity, ocr_confidence_component, type_match, colour_match NULLABLE
- identity_matches: add appearance_similarity, temporal_score, camera_transition_score columns
- canonical_vehicles: make best_plate_text NULLABLE (allow plate-free canonical vehicles)
"""

from alembic import op
import sqlalchemy as sa


revision = "20260906_000002"
down_revision = "20260830_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # identity_matches: make existing evidence columns nullable
    # so visual-only (CityFlowV2) matches can exist without plate evidence
    # -----------------------------------------------------------------------
    op.alter_column("identity_matches", "plate_similarity", nullable=True)
    op.alter_column("identity_matches", "ocr_confidence_component", nullable=True)
    op.alter_column("identity_matches", "type_match", nullable=True)
    op.alter_column("identity_matches", "colour_match", nullable=True)

    # -----------------------------------------------------------------------
    # identity_matches: add new multi-modal evidence columns
    # -----------------------------------------------------------------------
    op.add_column(
        "identity_matches",
        sa.Column("appearance_similarity", sa.Numeric(precision=4, scale=3), nullable=True),
    )
    op.add_column(
        "identity_matches",
        sa.Column("temporal_score", sa.Numeric(precision=4, scale=3), nullable=True),
    )
    op.add_column(
        "identity_matches",
        sa.Column("camera_transition_score", sa.Numeric(precision=4, scale=3), nullable=True),
    )

    # -----------------------------------------------------------------------
    # canonical_vehicles: allow plate-free canonical vehicles (CityFlowV2)
    # -----------------------------------------------------------------------
    op.alter_column("canonical_vehicles", "best_plate_text", nullable=True)


def downgrade() -> None:
    # Restore NOT NULL constraints (will fail if NULLs exist in data)
    op.alter_column("canonical_vehicles", "best_plate_text", nullable=False)

    op.drop_column("identity_matches", "camera_transition_score")
    op.drop_column("identity_matches", "temporal_score")
    op.drop_column("identity_matches", "appearance_similarity")

    op.alter_column("identity_matches", "colour_match", nullable=False)
    op.alter_column("identity_matches", "type_match", nullable=False)
    op.alter_column("identity_matches", "ocr_confidence_component", nullable=False)
    op.alter_column("identity_matches", "plate_similarity", nullable=False)
