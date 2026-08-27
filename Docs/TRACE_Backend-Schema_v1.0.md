# TRACE
### Tracking, Recognition, Analytics & City-wide Traffic Enforcement
_Backend Schema_

| Field | Detail |
|---|---|
| Problem Statement ID | 26127 |
| Project Title | TRACE (Tracking, Recognition, Analytics & City-wide Traffic Enforcement) |
| Document Type | Backend Schema |
| Derived From | TRACE PRD v1.0, TRACE TRD v1.0, TRACE App/Website Flow v1.0, TRACE UI/UX Brief v1.0 |
| Database Engine | PostgreSQL + PostGIS extension |
| Document Owner | Nigesh (Project Lead) |
| Status | Draft v1.0 |

**Compatibility Note:** Compatible with PRD v1.1, TRD v1.3, and App/Website Flow v1.1. TRD v1.3 added `PATCH /alerts/{id}` to the API contract, but no table or column change was required as a result: the `alerts.reviewed`, `alerts.reviewed_by`, and `alerts.reviewed_at` fields already defined in Section 7.3 below were designed to support exactly this write path. No other revision altered any functional requirement, data field, or API contract this schema depends on.

## 1. Introduction

#### 1.1 Purpose
This document defines the database schema that persists every piece of data required by the functional requirements in the PRD, the modules in the Technical Requirement Document, and the screens and components in the App/Website Flow and UI/UX Brief. No table or field in this document is invented independently — each is traced to a specific upstream requirement or UI element, and each is tagged with the FR-xxx/NFR-xxx ID it supports.

#### 1.2 Conventions
- All table and column names use snake_case.
- Every table has a surrogate primary key named `<table>_id` (UUID) unless noted otherwise.
- All timestamp columns are stored in UTC as `timestamptz` and are named with an `_at` suffix.
- Camera and vehicle positions use `geography(Point, 4326)`; road segments use `geography(LineString, 4326)` where a path geometry is needed for map rendering.
- Foreign keys are named `<referenced_table_singular>_id`.
- Enum-like fields (status, type, role) are implemented as Postgres CHECK-constrained text columns for prototype simplicity, upgradeable to native enum types without a data migration.

#### 1.3 Schema Grouping
Tables are grouped into six areas that mirror the five-layer architecture plus a cross-cutting access-control area: Camera & Road Network, Perception, Identity & Trajectory, Analytics, Alerts & Blacklist, and Access Control.

## 2. Entity Relationship Overview
- cameras 1—N vehicle_observations (a camera records many observations).
- cameras 1—N road_edges (a camera is an endpoint of many road-graph edges).
- cameras 1—1 camera_reliability_profile (each camera has one active reliability profile).
- vehicle_observations 1—N ocr_reads (a fused observation is built from many raw per-frame OCR reads).
- vehicle_observations N—N vehicle_observations via identity_matches (pairwise candidate/confirmed matches between observations).
- canonical_vehicles 1—N trajectory_points, and trajectory_points N—1 vehicle_observations (a canonical vehicle's trajectory is an ordered chain of observations).
- canonical_vehicles 1—N anomalies (a vehicle's trajectory may raise zero or more anomaly events).
- anomalies and blacklist_entries both feed 1—N into alerts (alerts are a unified log over both anomaly and blacklist triggers).
- road_edges 1—N segment_stats and 1—N congestion_forecasts (analytics and forecasts are computed per edge/segment).
- users 1—N alerts (via reviewed_by) and 1—N blacklist_entries (via added_by).

## 3. Camera & Road Network Tables

#### 3.1 cameras
Supports: FR-STR-01, FR-PRD-03, NFR-05.

| Column | Type | Constraints | Description |
|---|---|---|---|
| camera_id | uuid | PK | Unique camera node identifier. |
| name | text | NOT NULL | Human-readable camera/junction name. |
| location | geography(Point,4326) | NOT NULL | Camera coordinates for GIS map plotting. |
| zone | text | NOT NULL | Zone/sector label, used for OD matrix grouping (FR-ANL-02). |
| status | text | CHECK IN ('online','degraded','down') | Live feed status shown on Camera Network Status screen. |
| last_seen_at | timestamptz | NULL allowed | Last successful frame ingestion time. |

#### 3.2 camera_reliability_profile
Supports: FR-PRD-03 (camera-aware identity weighting).

| Column | Type | Constraints | Description |
|---|---|---|---|
| camera_id | uuid | PK, FK -> cameras | One profile row per camera. |
| day_ocr_reliability | numeric(4,3) | 0–1 | Estimated OCR reliability in daylight. |
| night_ocr_reliability | numeric(4,3) | 0–1 | Estimated OCR reliability at night. |
| rain_ocr_reliability | numeric(4,3) | 0–1 | Estimated OCR reliability in rain. |
| angle_ocr_reliability | numeric(4,3) | 0–1 | Estimated OCR reliability at oblique angles. |
| updated_at | timestamptz | NOT NULL | Last time the static profile was updated. |

#### 3.3 road_edges
Supports: FR-STR-01, FR-STR-02, FR-STR-04 (road-graph reasoning).

| Column | Type | Constraints | Description |
|---|---|---|---|
| edge_id | uuid | PK | Unique road-segment identifier. |
| from_camera_id | uuid | FK -> cameras, NOT NULL | Origin camera node. |
| to_camera_id | uuid | FK -> cameras, NOT NULL | Destination camera node. |
| distance_km | numeric(6,2) | NOT NULL | Road distance between the two nodes. |
| min_travel_time_s | integer | NOT NULL | Fastest plausible travel time, used for impossible-journey checks. |
| max_travel_time_s | integer | NOT NULL | Slowest typical travel time, used in forecasting baselines. |
| speed_limit_kmph | integer | NOT NULL | Posted speed limit for the segment. |
| path_geometry | geography(LineString,4326) | NULL allowed | Optional path geometry for accurate map rendering. |

## 4. Perception Tables

#### 4.1 ocr_reads
Supports: FR-PER-03, FR-PER-04 (raw per-frame evidence prior to temporal fusion).

| Column | Type | Constraints | Description |
|---|---|---|---|
| ocr_read_id | uuid | PK | Unique per-frame OCR read. |
| observation_id | uuid | FK -> vehicle_observations, NOT NULL | Fused observation this read contributes to. |
| frame_timestamp | timestamptz | NOT NULL | Timestamp of the source frame. |
| raw_plate_text | text | NOT NULL | Unfused plate text read from this single frame. |
| confidence | numeric(4,3) | 0–1 | Per-frame OCR confidence score. |

#### 4.2 vehicle_observations
Supports: FR-PER-01, FR-PER-02, FR-PER-04, FR-ID-01 (fused, camera-level vehicle sighting record).

| Column | Type | Constraints | Description |
|---|---|---|---|
| observation_id | uuid | PK | Unique fused observation. |
| camera_id | uuid | FK -> cameras, NOT NULL | Camera that recorded the observation. |
| track_id | text | NOT NULL | Within-camera tracking ID from ByteTrack, prevents duplicate counting. |
| captured_at | timestamptz | NOT NULL | Timestamp of the observation (track midpoint or entry). |
| fused_plate_text | text | NOT NULL | Confidence-weighted fused plate result across all track frames. |
| fused_confidence | numeric(4,3) | 0–1 | Final fused OCR confidence (FR-PER-04). |
| vehicle_type | text | NOT NULL | Detected vehicle type (e.g., car, SUV, two-wheeler). |
| vehicle_colour | text | NOT NULL | Detected vehicle colour. |

## 5. Identity & Trajectory Tables

#### 5.1 identity_matches
Supports: FR-ID-02, FR-ID-03, FR-ID-04, FR-STR-02, FR-STR-04 (the pairwise match record that powers the Evidence Panel in the UI/UX Brief).

| Column | Type | Constraints | Description |
|---|---|---|---|
| match_id | uuid | PK | Unique candidate/confirmed match between two observations. |
| observation_id_a | uuid | FK -> vehicle_observations, NOT NULL | Earlier observation in the pair. |
| observation_id_b | uuid | FK -> vehicle_observations, NOT NULL | Later observation in the pair. |
| plate_similarity | numeric(4,3) | 0–1 | Plate-text similarity component. |
| ocr_confidence_component | numeric(4,3) | 0–1 | Weighted OCR confidence component. |
| type_match | boolean | NOT NULL | Whether vehicle type matched. |
| colour_match | boolean | NOT NULL | Whether vehicle colour matched. |
| identity_score | numeric(4,3) | 0–1, NOT NULL | Composite Identity Score shown as the Confidence Badge (TRD Section 4.2). |
| implied_speed_kmph | numeric(6,2) | NULL allowed | Computed implied travel speed between the two observations. |
| is_impossible_journey | boolean | DEFAULT false | Set true when implied_speed_kmph exceeds the edge's plausible ceiling (FR-STR-04). |

#### 5.2 canonical_vehicles
Supports: FR-STR-03 (groups confirmed matches into one trackable identity).

| Column | Type | Constraints | Description |
|---|---|---|---|
| canonical_vehicle_id | uuid | PK | One row per resolved vehicle identity. |
| best_plate_text | text | NOT NULL | Highest-confidence plate text representing this vehicle. |
| first_seen_at | timestamptz | NOT NULL | Earliest observation timestamp in the trajectory. |
| last_seen_at | timestamptz | NOT NULL | Latest observation timestamp in the trajectory. |

#### 5.3 trajectory_points
Supports: FR-STR-03, FR-STR-05 (the ordered sequence rendered on the Vehicle Trace map).

| Column | Type | Constraints | Description |
|---|---|---|---|
| trajectory_point_id | uuid | PK | Unique point in a reconstructed trajectory. |
| canonical_vehicle_id | uuid | FK -> canonical_vehicles, NOT NULL | Vehicle this point belongs to. |
| observation_id | uuid | FK -> vehicle_observations, NOT NULL | Underlying observation for this point. |
| sequence_no | integer | NOT NULL | Chronological order index within the trajectory. |
| camera_id | uuid | FK -> cameras, NOT NULL | Denormalized for fast map rendering without a join. |
| captured_at | timestamptz | NOT NULL | Denormalized timestamp for fast chronological display. |

## 6. Analytics Tables

#### 6.1 segment_stats
Supports: FR-ANL-01, FR-ANL-03, FR-ANL-05 (Segment Detail panel and heatmap source data).

| Column | Type | Constraints | Description |
|---|---|---|---|
| segment_stat_id | uuid | PK | Unique stat row per edge per time window. |
| edge_id | uuid | FK -> road_edges, NOT NULL | Road segment this statistic covers. |
| window_start | timestamptz | NOT NULL | Start of the aggregation window. |
| window_end | timestamptz | NOT NULL | End of the aggregation window. |
| density | integer | NOT NULL | Vehicle count on the segment within the window (FR-ANL-01). |
| avg_speed_kmph | numeric(6,2) | NOT NULL | Average implied speed within the window. |
| congestion_status | text | CHECK IN ('free','moderate','congested') | Derived bottleneck flag (FR-ANL-03). |

#### 6.2 od_matrix_cache
Supports: FR-ANL-02 (precomputed for fast OD Matrix screen rendering).

| Column | Type | Constraints | Description |
|---|---|---|---|
| od_entry_id | uuid | PK | Unique origin-destination cache row. |
| origin_zone | text | NOT NULL | Zone label matching cameras.zone. |
| destination_zone | text | NOT NULL | Zone label matching cameras.zone. |
| window_start | timestamptz | NOT NULL | Aggregation window start. |
| window_end | timestamptz | NOT NULL | Aggregation window end. |
| trip_count | integer | NOT NULL | Number of trajectories observed from origin to destination in the window. |

#### 6.3 congestion_forecasts
Supports: FR-PRD-01 (Forecast sub-panel on Segment Detail).

| Column | Type | Constraints | Description |
|---|---|---|---|
| forecast_id | uuid | PK | Unique forecast record. |
| edge_id | uuid | FK -> road_edges, NOT NULL | Segment being forecast. |
| forecast_for_window | timestamptz | NOT NULL | Target time window the forecast applies to. |
| predicted_density | integer | NOT NULL | Projected vehicle count. |
| congestion_probability | numeric(4,3) | 0–1 | Projected likelihood of congestion, shown in the UI as a labelled heuristic estimate. |
| generated_at | timestamptz | NOT NULL | When this forecast was computed. |

## 7. Alerts & Blacklist Tables

#### 7.1 blacklist_entries
Supports: FR-ALT-01 (Blacklist Management screen).

| Column | Type | Constraints | Description |
|---|---|---|---|
| blacklist_id | uuid | PK | Unique watched-plate entry. |
| plate_text | text | NOT NULL | Plate number being watched. |
| reason | text | NOT NULL | Reason the plate was flagged. |
| added_by | uuid | FK -> users, NOT NULL | Admin who added the entry. |
| added_at | timestamptz | NOT NULL | When the entry was added. |
| active | boolean | DEFAULT true | Whether the entry is currently enforced. |

#### 7.2 anomalies
Supports: FR-PRD-02 (impossible journeys, duplicate plates, camera-timestamp inconsistencies).

| Column | Type | Constraints | Description |
|---|---|---|---|
| anomaly_id | uuid | PK | Unique anomaly event. |
| type | text | CHECK IN ('impossible_journey','duplicate_plate','camera_inconsistency') | Anomaly classification shown by icon on the Alerts screen. |
| canonical_vehicle_id | uuid | FK -> canonical_vehicles, NULL allowed | Related vehicle identity, if applicable. |
| match_id | uuid | FK -> identity_matches, NULL allowed | Related match record, if the anomaly is match-derived. |
| details | jsonb | NOT NULL | Structured explanation (e.g., implied speed vs. threshold) for the Evidence Panel. |
| detected_at | timestamptz | NOT NULL | When the anomaly was raised. |

#### 7.3 alerts
Supports: FR-ALT-02, FR-ALT-03, FR-ALT-04 (unified alert log behind the Alerts screen). The `reviewed`, `reviewed_by`, and `reviewed_at` fields below back the `PATCH /alerts/{id}` endpoint added in TRD v1.3.

| Column | Type | Constraints | Description |
|---|---|---|---|
| alert_id | uuid | PK | Unique alert. |
| type | text | CHECK IN ('blacklist_hit','impossible_journey','duplicate_plate','camera_inconsistency') | Alert type, mirrors anomaly type plus blacklist_hit. |
| plate_text | text | NOT NULL | Plate the alert concerns. |
| camera_id | uuid | FK -> cameras, NOT NULL | Camera where the triggering event occurred. |
| anomaly_id | uuid | FK -> anomalies, NULL allowed | Linked anomaly, when type is anomaly-derived. |
| blacklist_id | uuid | FK -> blacklist_entries, NULL allowed | Linked blacklist entry, when type is blacklist_hit. |
| triggered_at | timestamptz | NOT NULL | When the alert fired. |
| reviewed | boolean | DEFAULT false | Review status toggle shown on the Alert Card; written via `PATCH /alerts/{id}`. |
| reviewed_by | uuid | FK -> users, NULL allowed | User who reviewed the alert. |
| reviewed_at | timestamptz | NULL allowed | When the alert was reviewed. |

## 8. Access Control Tables

#### 8.1 users
Supports: NFR-06 (role-restricted access).

| Column | Type | Constraints | Description |
|---|---|---|---|
| user_id | uuid | PK | Unique platform user. |
| name | text | NOT NULL | Display name. |
| email | text | UNIQUE, NOT NULL | Login identifier. |
| password_hash | text | NOT NULL | Hashed credential, never stored in plaintext. |
| role | text | CHECK IN ('operator','analyst','admin') | Determines visible navigation items per the UI/UX Brief. |
| created_at | timestamptz | NOT NULL | Account creation time. |

## 9. Indexing and Performance Notes
Supports: NFR-02 (interactive-speed trajectory queries).

- vehicle_observations: index on (camera_id, captured_at) to support fast per-camera time-window scans used by segment_stats aggregation.
- identity_matches: index on (observation_id_a), (observation_id_b), and identity_score, to accelerate both trajectory building and confidence filtering.
- trajectory_points: index on (canonical_vehicle_id, sequence_no) to serve the Vehicle Trace screen's ordered list directly without re-sorting.
- road_edges: index on (from_camera_id, to_camera_id) to accelerate reachability checks (FR-STR-02).
- alerts: index on (reviewed, triggered_at DESC) to serve the default "newest unreviewed first" Alerts screen view.
- PostGIS GIST indexes on all geography columns (cameras.location, road_edges.path_geometry) to accelerate map bounding-box queries.

## 10. Data Retention Notes
Supports: NFR-06. The prototype retains all observation and trajectory data for the duration of the demo dataset without automated expiry. The schema is designed so that a retention job can later be added — deleting rows from ocr_reads and vehicle_observations older than a configured window, while preserving aggregated segment_stats and od_matrix_cache rows for historical analytics — without changing the schema itself. This mirrors the PRD's Section 3.3 note that a full retention/encryption pipeline is documented as production roadmap rather than built for the prototype.

## 11. API-to-Table Mapping
Cross-reference against the TRD's API Design Overview (Section 5), confirming every endpoint has a backing table.

| Endpoint | Primary Table(s) |
|---|---|
| GET /vehicles/{plate}/trajectory | canonical_vehicles, trajectory_points, vehicle_observations, identity_matches |
| GET /analytics/heatmap | segment_stats |
| GET /analytics/od-matrix | od_matrix_cache |
| GET /analytics/segments/{id} | segment_stats, road_edges |
| GET /analytics/forecast/{segment_id} | congestion_forecasts |
| GET /alerts | alerts, anomalies, blacklist_entries |
| PATCH /alerts/{id} | alerts |
| POST / GET /blacklist | blacklist_entries |
| /ws/live-updates | vehicle_observations, alerts (change-triggered push) |

## 12. Traceability
Every table in this document maps to one or more FR-xxx/NFR-xxx requirements from the PRD, the module design in the TRD, and the screens/components defined in the App/Website Flow and UI/UX Brief. This schema is the final data-contract layer; the Implementation Plan will sequence which tables and endpoints are built in which milestone, and by which team role.

— End of Backend Schema —
