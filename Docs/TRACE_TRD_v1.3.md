# TRACE
Tracking, Recognition, Analytics & City-wide Traffic Enforcement

# Technical Requirement Document — Revised v1.3

**Changes from v1.1 (carried into v1.2, unchanged):** NFR-05 made operational through a P2 M2 failure-isolation checklist. Single-FastAPI architecture unchanged.

**Changes from v1.2 (this revision):** Adds `PATCH /alerts/{id}` to the API contract to persist the alert-review action already specified in the App/Website Flow (v1.1) and UI/UX Brief, and already supported by the existing `alerts.reviewed`, `reviewed_by`, and `reviewed_at` schema fields. No table, field, or other endpoint changed. Version bumped from v1.2 to v1.3 because this is an addition to the locked API contract, consistent with this project's convention of bumping the minor version whenever a document's functional content changes (see PRD v1.0→v1.1, TRD v1.1→v1.2).

## 1.2 Architectural Principle — UNCHANGED FROM v1.1
TRACE uses five loosely-coupled logical modules corresponding to the Layer Model. Each has a defined input/output contract. For the prototype, these modules run inside one FastAPI application rather than separate deployable microservices.

## 2. System Architecture — UNCHANGED FROM v1.1
Camera Feed → Perception Module → Identity Fusion Module → Road-Graph Store → Spatial-Temporal Reasoning Module → [Trajectory | Analytics | Anomaly & Prediction] → Alert Module → FastAPI API Layer → React/MapLibre Dashboard.

## 3.1 Prototype Stack — UNCHANGED

| Purpose | Technology |
|---|---|
| Video ingestion | Recorded/simulated multi-camera feeds via OpenCV |
| Detection | YOLO (v8/v9 family) |
| Tracking | ByteTrack |
| OCR | PaddleOCR |
| Identity fusion | Python weighted scoring |
| Road graph | PostgreSQL + PostGIS |
| Backend/API | FastAPI (Python), one application containing logical modules |
| Realtime | WebSockets (polling fallback) |
| Frontend | React + MapLibre GL + charting library |
| Deployment | Docker Compose |

## 5. API Design Overview — REVISED IN v1.3 FOR ALERT REVIEW
The API contract from v1.1/v1.2 is retained in full, with one additive endpoint: `PATCH /alerts/{id}`, which persists the alert-review action already defined in the App/Website Flow and UI/UX Brief. No existing endpoint is removed, renamed, or otherwise changed.

| Endpoint | Method | Purpose |
|---|---|---|
| /vehicles/{plate}/trajectory | GET | Reconstructed chronological trajectory. |
| /analytics/heatmap | GET | Current density values per segment. |
| /analytics/od-matrix | GET | Current OD matrix. |
| /analytics/segments/{id} | GET | Average speed, density and congestion status. |
| /analytics/forecast/{segment_id} | GET | Short-horizon forecast. |
| /alerts | GET | Recent blacklist/anomaly alerts. |
| /alerts/{id} | PATCH | Mark an alert reviewed/unreviewed and persist review metadata. |
| /blacklist | POST / GET | Add/read watched plates. |
| /ws/live-updates | WS | Live observation, alert and heatmap updates. |

## 7. NFR-05 Reliability — OPERATIONAL CHECKLIST FOR P2 / M2 — UNCHANGED FROM v1.2
NFR-05 requires graceful degradation when a camera feed is unavailable. The following checklist is the implementation-level sign-off for M2. It applies to the single-FastAPI prototype and does not change the external API.

1. Wrap each camera's perception call in its own try/except. A bad frame, corrupted feed or OCR crash must log and skip that camera's cycle; it must never raise past the ingestion loop.
2. Never let a per-camera failure block the shared event loop. Run perception/ingestion for each camera as an independent async task or background job so one hung feed cannot stall detection on the others.
3. On failure, write the camera's status as degraded or down, using the existing `cameras` table status field, instead of leaving stale data. This status is consumed by the dashboard and Camera Network Status view.
4. Set a per-camera timeout on detection/OCR calls so a slow frame cannot hang that camera's pipeline indefinitely.
5. Keep the FastAPI process itself unaffected by any single module exception. A Layer 3 reasoning bug on one trajectory query must return a clean error response rather than crash requests for other endpoints.
6. M2 manual test: kill or corrupt one simulated camera feed mid-run. Confirm the other cameras continue ingesting normally and the dashboard shows the affected camera as down rather than frozen or blank.

### M2 Sign-off Evidence
P2 records the result of the six checks in the M2 QA notes, including the camera used for the failure test and evidence that unaffected cameras continued processing. P3 validates the UI state and P1 verifies the corresponding dashboard/camera-status presentation.

## 8. NFR-08 Maintainability — UNCHANGED FROM v1.1
The five intelligence layers remain separable code modules with defined interfaces inside one FastAPI application. A layer can be modified or replaced without rewriting the others.

All other TRD sections remain unchanged from v1.2; the API contract now includes the additive alert-review endpoint described in Section 5.

— TRACE TRD, Revised v1.3 —
