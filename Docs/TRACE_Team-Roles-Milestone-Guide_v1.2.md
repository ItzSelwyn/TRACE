# TRACE
Tracking, Recognition, Analytics & City-wide Traffic Enforcement

# Team Roles & Milestone Contribution Guide — Revised v1.2

Current execution team: 3 members. The six milestones and all TRACE requirements remain unchanged.

**Changes from v1.1:** §6 corrected — App/Website Flow is no longer listed as unchanged; it was revised to v1.1 to add the `PATCH /alerts/{id}` endpoint reference (mirroring TRD v1.3). No role, milestone, ownership, or requirement content changed in this revision.

## 1. Role Assignment

| Role | Focus |
|---|---|
| P1 — Frontend Developer / UI Engineer | Designs and codes the complete React/MapLibre UI and integrates REST/WebSocket data. |
| P2 — Backend + ML Engineer | Builds the complete Python/FastAPI pipeline, PostgreSQL/PostGIS layer and all five logical intelligence modules plus alerts. |
| P3 — Data Collector & Project Support | Prepares datasets, annotations, ground truth and demo scenarios; supports QA, documentation and rehearsal. |

## 2. P1 — Frontend Developer / UI Engineer

### M1
- React/Vite shell, navigation and all 8 Screen Inventory entries (6 top-level routes; Traffic Analytics' 3 sub-views are tabs, not separate routes — see Agent Build Brief §1).
- Reusable UI components and visual system.

### M2
- Confidence Badge, Status Dot, Map Panel and state components.

### M3
- Evidence Panel and identity-confidence presentation.

### M4
- Vehicle Trace, GIS trajectory, observation timeline and anomaly treatment.

### M5
- Dashboard, Heatmap, OD Matrix and Segment Detail with real API integration.

### M6
- Alerts (including the Review toggle wired to `PATCH /alerts/{id}`), Blacklist, Camera Network Status and WebSocket live-update UI; final polish.

## 3. P2 — Backend + ML Engineer
All backend intelligence remains logically separated but runs in one FastAPI application.

### M1
- PostgreSQL + PostGIS and existing schema.
- Single FastAPI app with internal perception, identity, reasoning, analytics, prediction and alerts modules.
- Seed cameras/road_edges and configure Docker Compose.

### M2
- YOLO + ByteTrack + PaddleOCR + temporal OCR fusion.
- Persist ocr_reads and vehicle_observations.

### M3
- Identity Score, low-confidence fallback, identity_matches and camera-reliability weighting.

### M4
- Reachability, trajectory reconstruction, impossible-journey detection and existing trajectory endpoint.

### M5
- Density, OD, congestion, forecast and existing analytics endpoints.

### M6
- Blacklist, anomaly alerts, alert logging (including the `PATCH /alerts/{id}` review endpoint), access control and existing WebSocket endpoint.

## 4. P3 — Data Collector & Project Support

### M1
- Collect/organize footage; label ground truth; prepare evaluation and demo data.

### M2
- Maintain annotation quality and support condition-based OCR evaluation.

### M3
- Prepare known observation pairs and validate identity outcomes.

### M4
- Stage known journeys including one impossible pair; verify timestamps and expected outcomes.

### M5
- Validate density, OD and congestion results against known demo data.

### M6
- Run end-to-end QA, test alerts/camera-down/empty/low-confidence states, support docs and rehearsal.

## 5. Working Rule
P2 is the critical path in M2–M4. P1 can use mocked JSON/API responses until endpoints are ready. P3 works ahead on data and validation. All three review milestone integrations.

## 6. Files That Remain Unchanged
The Backend Schema and UI/UX Brief remain unchanged (their compatibility notes were updated to acknowledge the TRD v1.3/Flow v1.1 addition, but no screen, component, table, or field changed). The App/Website Flow was revised to v1.1 solely to reference the new `PATCH /alerts/{id}` endpoint; no flow step, screen, or persona behavior changed. The PRD was separately revised to v1.1 for Section 7.2 team-composition wording only — no functional requirement changed. The TRD (now v1.3), Implementation Plan, and this team guide are the documents revised for the single-FastAPI deployment, three-person ownership, and the alert-review endpoint addition.

— TRACE Team Roles & Milestone Contribution Guide, Revised v1.2 —
