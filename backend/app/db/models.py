from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean, Integer, Numeric, DateTime, ForeignKey, Text, CheckConstraint, Index, desc
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from geoalchemy2 import Geography
import uuid
from datetime import datetime
from typing import List, Optional

class Base(DeclarativeBase):
    pass

class Camera(Base):
    __tablename__ = "cameras"
    
    camera_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    location = mapped_column(Geography(geometry_type='POINT', srid=4326), nullable=False, index=True)
    zone: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Text, 
        CheckConstraint("status IN ('online','degraded','down')", name='ck_cameras_status'), 
        nullable=False, 
        default='online'
    )
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    reliability_profile: Mapped["CameraReliabilityProfile"] = relationship(back_populates="camera")
    edges_from: Mapped[List["RoadEdge"]] = relationship(foreign_keys="[RoadEdge.from_camera_id]", back_populates="from_camera")
    edges_to: Mapped[List["RoadEdge"]] = relationship(foreign_keys="[RoadEdge.to_camera_id]", back_populates="to_camera")
    observations: Mapped[List["VehicleObservation"]] = relationship(back_populates="camera")
    trajectory_points: Mapped[List["TrajectoryPoint"]] = relationship(back_populates="camera")
    alerts: Mapped[List["Alert"]] = relationship(back_populates="camera")


class CameraReliabilityProfile(Base):
    __tablename__ = "camera_reliability_profile"
    
    camera_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("cameras.camera_id", ondelete="CASCADE"), primary_key=True)
    day_ocr_reliability: Mapped[float] = mapped_column(Numeric(4,3), nullable=False)
    night_ocr_reliability: Mapped[float] = mapped_column(Numeric(4,3), nullable=False)
    rain_ocr_reliability: Mapped[float] = mapped_column(Numeric(4,3), nullable=False)
    angle_ocr_reliability: Mapped[float] = mapped_column(Numeric(4,3), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    camera: Mapped["Camera"] = relationship(back_populates="reliability_profile")


class RoadEdge(Base):
    __tablename__ = "road_edges"
    
    edge_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    from_camera_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("cameras.camera_id"), nullable=False)
    to_camera_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("cameras.camera_id"), nullable=False)
    distance_km: Mapped[float] = mapped_column(Numeric(6,2), nullable=False)
    min_travel_time_s: Mapped[int] = mapped_column(Integer, nullable=False)
    max_travel_time_s: Mapped[int] = mapped_column(Integer, nullable=False)
    speed_limit_kmph: Mapped[int] = mapped_column(Integer, nullable=False)
    path_geometry = mapped_column(Geography(geometry_type='LINESTRING', srid=4326), nullable=True, index=True)

    __table_args__ = (
        Index('ix_road_edges_from_to', 'from_camera_id', 'to_camera_id'),
    )

    from_camera: Mapped["Camera"] = relationship(foreign_keys=[from_camera_id], back_populates="edges_from")
    to_camera: Mapped["Camera"] = relationship(foreign_keys=[to_camera_id], back_populates="edges_to")
    segment_stats: Mapped[List["SegmentStat"]] = relationship(back_populates="edge")
    forecasts: Mapped[List["CongestionForecast"]] = relationship(back_populates="edge")


class VehicleObservation(Base):
    __tablename__ = "vehicle_observations"
    
    observation_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    camera_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("cameras.camera_id"), nullable=False)
    track_id: Mapped[str] = mapped_column(Text, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fused_plate_text: Mapped[str] = mapped_column(Text, nullable=False)
    fused_confidence: Mapped[float] = mapped_column(Numeric(4,3), nullable=False)
    vehicle_type: Mapped[str] = mapped_column(Text, nullable=False)
    vehicle_colour: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        Index('ix_vehicle_obs_camera_time', 'camera_id', 'captured_at'),
    )

    camera: Mapped["Camera"] = relationship(back_populates="observations")
    ocr_reads: Mapped[List["OcrRead"]] = relationship(back_populates="observation")
    identity_matches_a: Mapped[List["IdentityMatch"]] = relationship(foreign_keys="[IdentityMatch.observation_id_a]", back_populates="observation_a")
    identity_matches_b: Mapped[List["IdentityMatch"]] = relationship(foreign_keys="[IdentityMatch.observation_id_b]", back_populates="observation_b")
    trajectory_points: Mapped[List["TrajectoryPoint"]] = relationship(back_populates="observation")


class OcrRead(Base):
    __tablename__ = "ocr_reads"
    
    ocr_read_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    observation_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("vehicle_observations.observation_id"), nullable=False)
    frame_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw_plate_text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(4,3), nullable=False)

    observation: Mapped["VehicleObservation"] = relationship(back_populates="ocr_reads")


class IdentityMatch(Base):
    __tablename__ = "identity_matches"
    
    match_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    observation_id_a: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("vehicle_observations.observation_id"), nullable=False)
    observation_id_b: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("vehicle_observations.observation_id"), nullable=False)
    plate_similarity: Mapped[float] = mapped_column(Numeric(4,3), nullable=False)
    ocr_confidence_component: Mapped[float] = mapped_column(Numeric(4,3), nullable=False)
    type_match: Mapped[bool] = mapped_column(Boolean, nullable=False)
    colour_match: Mapped[bool] = mapped_column(Boolean, nullable=False)
    identity_score: Mapped[float] = mapped_column(Numeric(4,3), nullable=False)
    implied_speed_kmph: Mapped[Optional[float]] = mapped_column(Numeric(6,2), nullable=True)
    is_impossible_journey: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        Index('ix_identity_matches_obs_a', 'observation_id_a'),
        Index('ix_identity_matches_obs_b', 'observation_id_b'),
        Index('ix_identity_matches_score', 'identity_score'),
    )

    observation_a: Mapped["VehicleObservation"] = relationship(foreign_keys=[observation_id_a], back_populates="identity_matches_a")
    observation_b: Mapped["VehicleObservation"] = relationship(foreign_keys=[observation_id_b], back_populates="identity_matches_b")
    anomalies: Mapped[List["Anomaly"]] = relationship(back_populates="match")


class CanonicalVehicle(Base):
    __tablename__ = "canonical_vehicles"
    
    canonical_vehicle_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    best_plate_text: Mapped[str] = mapped_column(Text, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    trajectory_points: Mapped[List["TrajectoryPoint"]] = relationship(back_populates="canonical_vehicle")
    anomalies: Mapped[List["Anomaly"]] = relationship(back_populates="canonical_vehicle")


class TrajectoryPoint(Base):
    __tablename__ = "trajectory_points"
    
    trajectory_point_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    canonical_vehicle_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("canonical_vehicles.canonical_vehicle_id"), nullable=False)
    observation_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("vehicle_observations.observation_id"), nullable=False)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    camera_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("cameras.camera_id"), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index('ix_trajectory_points_vehicle_seq', 'canonical_vehicle_id', 'sequence_no'),
    )

    canonical_vehicle: Mapped["CanonicalVehicle"] = relationship(back_populates="trajectory_points")
    observation: Mapped["VehicleObservation"] = relationship(back_populates="trajectory_points")
    camera: Mapped["Camera"] = relationship(back_populates="trajectory_points")


class SegmentStat(Base):
    __tablename__ = "segment_stats"
    
    segment_stat_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    edge_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("road_edges.edge_id"), nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    density: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_speed_kmph: Mapped[float] = mapped_column(Numeric(6,2), nullable=False)
    congestion_status: Mapped[str] = mapped_column(
        Text, 
        CheckConstraint("congestion_status IN ('free','moderate','congested')", name='ck_segment_stats_congestion'),
        nullable=False
    )

    edge: Mapped["RoadEdge"] = relationship(back_populates="segment_stats")


class OdMatrixCache(Base):
    __tablename__ = "od_matrix_cache"
    
    od_entry_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    origin_zone: Mapped[str] = mapped_column(Text, nullable=False)
    destination_zone: Mapped[str] = mapped_column(Text, nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    trip_count: Mapped[int] = mapped_column(Integer, nullable=False)


class CongestionForecast(Base):
    __tablename__ = "congestion_forecasts"
    
    forecast_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    edge_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("road_edges.edge_id"), nullable=False)
    forecast_for_window: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    predicted_density: Mapped[int] = mapped_column(Integer, nullable=False)
    congestion_probability: Mapped[float] = mapped_column(Numeric(4,3), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    edge: Mapped["RoadEdge"] = relationship(back_populates="forecasts")


class User(Base):
    __tablename__ = "users"
    
    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(
        Text,
        CheckConstraint("role IN ('operator','analyst','admin')", name='ck_users_role'),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    blacklist_entries: Mapped[List["BlacklistEntry"]] = relationship(back_populates="adder")
    alerts_reviewed: Mapped[List["Alert"]] = relationship(back_populates="reviewer")


class BlacklistEntry(Base):
    __tablename__ = "blacklist_entries"
    
    blacklist_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plate_text: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    added_by: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    adder: Mapped["User"] = relationship(back_populates="blacklist_entries")
    alerts: Mapped[List["Alert"]] = relationship(back_populates="blacklist_entry")


class Anomaly(Base):
    __tablename__ = "anomalies"
    
    anomaly_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type: Mapped[str] = mapped_column(
        Text,
        CheckConstraint("type IN ('impossible_journey','duplicate_plate','camera_inconsistency')", name='ck_anomalies_type'),
        nullable=False
    )
    canonical_vehicle_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("canonical_vehicles.canonical_vehicle_id"), nullable=True)
    match_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("identity_matches.match_id"), nullable=True)
    details: Mapped[dict] = mapped_column(JSONB, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    canonical_vehicle: Mapped[Optional["CanonicalVehicle"]] = relationship(back_populates="anomalies")
    match: Mapped[Optional["IdentityMatch"]] = relationship(back_populates="anomalies")
    alerts: Mapped[List["Alert"]] = relationship(back_populates="anomaly")


class Alert(Base):
    __tablename__ = "alerts"
    
    alert_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type: Mapped[str] = mapped_column(
        Text,
        CheckConstraint("type IN ('blacklist_hit','impossible_journey','duplicate_plate','camera_inconsistency')", name='ck_alerts_type'),
        nullable=False
    )
    plate_text: Mapped[str] = mapped_column(Text, nullable=False)
    camera_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("cameras.camera_id"), nullable=False)
    anomaly_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("anomalies.anomaly_id"), nullable=True)
    blacklist_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("blacklist_entries.blacklist_id"), nullable=True)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index('ix_alerts_reviewed_triggered', 'reviewed', desc('triggered_at')),
    )

    camera: Mapped["Camera"] = relationship(back_populates="alerts")
    anomaly: Mapped[Optional["Anomaly"]] = relationship(back_populates="alerts")
    blacklist_entry: Mapped[Optional["BlacklistEntry"]] = relationship(back_populates="alerts")
    reviewer: Mapped[Optional["User"]] = relationship(back_populates="alerts_reviewed")
