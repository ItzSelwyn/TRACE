"""Initial TRACE M1 schema.

Revision ID: 20260830_000001
Revises: 
Create Date: 2026-08-30 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geography
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260830_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cameras",
        sa.Column("camera_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("location", Geography(geometry_type="POINT", srid=4326), nullable=False),
        sa.Column("zone", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('online','degraded','down')", name="ck_cameras_status"),
        sa.PrimaryKeyConstraint("camera_id"),
    )
    op.create_table(
        "camera_reliability_profile",
        sa.Column("camera_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("day_ocr_reliability", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("night_ocr_reliability", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("rain_ocr_reliability", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("angle_ocr_reliability", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["camera_id"], ["cameras.camera_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("camera_id"),
    )
    op.create_table(
        "road_edges",
        sa.Column("edge_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_camera_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("to_camera_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("distance_km", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column("min_travel_time_s", sa.Integer(), nullable=False),
        sa.Column("max_travel_time_s", sa.Integer(), nullable=False),
        sa.Column("speed_limit_kmph", sa.Integer(), nullable=False),
        sa.Column("path_geometry", Geography(geometry_type="LINESTRING", srid=4326), nullable=True),
        sa.ForeignKeyConstraint(["from_camera_id"], ["cameras.camera_id"]),
        sa.ForeignKeyConstraint(["to_camera_id"], ["cameras.camera_id"]),
        sa.PrimaryKeyConstraint("edge_id"),
    )
    op.create_table(
        "vehicle_observations",
        sa.Column("observation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("camera_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("track_id", sa.Text(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fused_plate_text", sa.Text(), nullable=False),
        sa.Column("fused_confidence", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("vehicle_type", sa.Text(), nullable=False),
        sa.Column("vehicle_colour", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["camera_id"], ["cameras.camera_id"]),
        sa.PrimaryKeyConstraint("observation_id"),
    )
    op.create_table(
        "ocr_reads",
        sa.Column("ocr_read_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("observation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("frame_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_plate_text", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.ForeignKeyConstraint(["observation_id"], ["vehicle_observations.observation_id"]),
        sa.PrimaryKeyConstraint("ocr_read_id"),
    )
    op.create_table(
        "identity_matches",
        sa.Column("match_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("observation_id_a", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("observation_id_b", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plate_similarity", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("ocr_confidence_component", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("type_match", sa.Boolean(), nullable=False),
        sa.Column("colour_match", sa.Boolean(), nullable=False),
        sa.Column("identity_score", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("implied_speed_kmph", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("is_impossible_journey", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.ForeignKeyConstraint(["observation_id_a"], ["vehicle_observations.observation_id"]),
        sa.ForeignKeyConstraint(["observation_id_b"], ["vehicle_observations.observation_id"]),
        sa.PrimaryKeyConstraint("match_id"),
    )
    op.create_table(
        "canonical_vehicles",
        sa.Column("canonical_vehicle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("best_plate_text", sa.Text(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("canonical_vehicle_id"),
    )
    op.create_table(
        "trajectory_points",
        sa.Column("trajectory_point_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("canonical_vehicle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("observation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("camera_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["canonical_vehicle_id"], ["canonical_vehicles.canonical_vehicle_id"]),
        sa.ForeignKeyConstraint(["observation_id"], ["vehicle_observations.observation_id"]),
        sa.ForeignKeyConstraint(["camera_id"], ["cameras.camera_id"]),
        sa.PrimaryKeyConstraint("trajectory_point_id"),
    )
    op.create_table(
        "segment_stats",
        sa.Column("segment_stat_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("edge_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("density", sa.Integer(), nullable=False),
        sa.Column("avg_speed_kmph", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column("congestion_status", sa.Text(), nullable=False),
        sa.CheckConstraint("congestion_status IN ('free','moderate','congested')", name="ck_segment_stats_congestion"),
        sa.ForeignKeyConstraint(["edge_id"], ["road_edges.edge_id"]),
        sa.PrimaryKeyConstraint("segment_stat_id"),
    )
    op.create_table(
        "od_matrix_cache",
        sa.Column("od_entry_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("origin_zone", sa.Text(), nullable=False),
        sa.Column("destination_zone", sa.Text(), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("trip_count", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("od_entry_id"),
    )
    op.create_table(
        "congestion_forecasts",
        sa.Column("forecast_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("edge_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("forecast_for_window", sa.DateTime(timezone=True), nullable=False),
        sa.Column("predicted_density", sa.Integer(), nullable=False),
        sa.Column("congestion_probability", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["edge_id"], ["road_edges.edge_id"]),
        sa.PrimaryKeyConstraint("forecast_id"),
    )
    op.create_table(
        "users",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("role IN ('operator','analyst','admin')", name="ck_users_role"),
        sa.PrimaryKeyConstraint("user_id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "blacklist_entries",
        sa.Column("blacklist_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plate_text", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("added_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.ForeignKeyConstraint(["added_by"], ["users.user_id"]),
        sa.PrimaryKeyConstraint("blacklist_id"),
    )
    op.create_table(
        "anomalies",
        sa.Column("anomaly_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("canonical_vehicle_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("match_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("type IN ('impossible_journey','duplicate_plate','camera_inconsistency')", name="ck_anomalies_type"),
        sa.ForeignKeyConstraint(["canonical_vehicle_id"], ["canonical_vehicles.canonical_vehicle_id"]),
        sa.ForeignKeyConstraint(["match_id"], ["identity_matches.match_id"]),
        sa.PrimaryKeyConstraint("anomaly_id"),
    )
    op.create_table(
        "alerts",
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("plate_text", sa.Text(), nullable=False),
        sa.Column("camera_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("anomaly_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("blacklist_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("type IN ('blacklist_hit','impossible_journey','duplicate_plate','camera_inconsistency')", name="ck_alerts_type"),
        sa.ForeignKeyConstraint(["camera_id"], ["cameras.camera_id"]),
        sa.ForeignKeyConstraint(["anomaly_id"], ["anomalies.anomaly_id"]),
        sa.ForeignKeyConstraint(["blacklist_id"], ["blacklist_entries.blacklist_id"]),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.user_id"]),
        sa.PrimaryKeyConstraint("alert_id"),
    )

    op.create_index("ix_vehicle_obs_camera_time", "vehicle_observations", ["camera_id", "captured_at"], unique=False)
    op.create_index("ix_identity_matches_obs_a", "identity_matches", ["observation_id_a"], unique=False)
    op.create_index("ix_identity_matches_obs_b", "identity_matches", ["observation_id_b"], unique=False)
    op.create_index("ix_identity_matches_score", "identity_matches", ["identity_score"], unique=False)
    op.create_index("ix_trajectory_points_vehicle_seq", "trajectory_points", ["canonical_vehicle_id", "sequence_no"], unique=False)
    op.create_index("ix_road_edges_from_to", "road_edges", ["from_camera_id", "to_camera_id"], unique=False)
    op.create_index("ix_alerts_reviewed_triggered", "alerts", ["reviewed", sa.text("triggered_at DESC")], unique=False)

    op.execute("CREATE INDEX ix_cameras_location_gist ON cameras USING GIST (location)")
    op.execute("CREATE INDEX ix_road_edges_path_geometry_gist ON road_edges USING GIST (path_geometry)")


def downgrade() -> None:
    op.drop_index("ix_road_edges_path_geometry_gist", table_name="road_edges")
    op.drop_index("ix_cameras_location_gist", table_name="cameras")
    op.drop_index("ix_alerts_reviewed_triggered", table_name="alerts")
    op.drop_index("ix_road_edges_from_to", table_name="road_edges")
    op.drop_index("ix_trajectory_points_vehicle_seq", table_name="trajectory_points")
    op.drop_index("ix_identity_matches_score", table_name="identity_matches")
    op.drop_index("ix_identity_matches_obs_b", table_name="identity_matches")
    op.drop_index("ix_identity_matches_obs_a", table_name="identity_matches")
    op.drop_index("ix_vehicle_obs_camera_time", table_name="vehicle_observations")
    op.drop_table("alerts")
    op.drop_table("anomalies")
    op.drop_table("blacklist_entries")
    op.drop_table("users")
    op.drop_table("congestion_forecasts")
    op.drop_table("od_matrix_cache")
    op.drop_table("segment_stats")
    op.drop_table("trajectory_points")
    op.drop_table("canonical_vehicles")
    op.drop_table("identity_matches")
    op.drop_table("ocr_reads")
    op.drop_table("vehicle_observations")
    op.drop_table("road_edges")
    op.drop_table("camera_reliability_profile")
    op.drop_table("cameras")
