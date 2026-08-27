# TRACE — Agent Build Brief v1.1

**Problem Statement ID:** 26127
**Purpose:** This document pins down every implementation decision that the PRD, TRD, Backend Schema, App/Website Flow, UI/UX Brief, and Implementation Plan leave open. It is written so that a coding agent (or a new team member) can start building without inventing thresholds, weights, data, or repo layout on its own. It introduces no new requirements — it only makes existing ones concrete.

**Derived from:** PRD v1.1, TRD v1.3, App/Website Flow v1.1, UI/UX Brief v1.0, Backend Schema v1.0, Implementation Plan v1.3, Team Roles Guide v1.2.

**Changes from v1.0:** (1) Added the missing role mapping for `PATCH /alerts/{id}` in §5 — this endpoint existed in TRD v1.3 and Flow v1.1 but had no auth rule, which would have left it either unreachable or unguarded. (2) Updated all cross-references above and in §7 to the current document versions (TRD v1.3, Flow v1.1, Team Roles Guide v1.2). (3) Marked the alert-review consistency note in §7 as resolved rather than open, since `PATCH /alerts/{id}` now exists. (4) Fixed a formatting error in §7 where two bullet notes had run together without a line break.

---

## 1. Repository Structure
Single repo, single FastAPI backend (per TRD v1.3 §1.2), single React frontend.

```
trace/
├── docker-compose.yml
├── .env.example
├── README.md
├── backend/
│   ├── pyproject.toml
│   ├── alembic/                      # DB migrations
│   ├── app/
│   │   ├── main.py                   # FastAPI app entrypoint
│   │   ├── config.py                 # settings (env-driven, see §5)
│   │   ├── db/
│   │   │   ├── models.py             # SQLAlchemy models = Backend Schema tables
│   │   │   └── session.py
│   │   ├── modules/
│   │   │   ├── perception/           # Layer 1 — YOLO + ByteTrack + PaddleOCR
│   │   │   ├── identity/             # Layer 2 — identity fusion scoring
│   │   │   ├── spatial_temporal/     # Layer 3 — road graph, trajectory, impossible journey
│   │   │   ├── network_intel/        # Layer 4 — density, OD matrix, congestion
│   │   │   ├── prediction_anomaly/   # Layer 5 — forecast, anomaly detection
│   │   │   └── alerts/               # Alert System
│   │   ├── api/
│   │   │   ├── vehicles.py           # /vehicles/{plate}/trajectory
│   │   │   ├── analytics.py          # /analytics/*
│   │   │   ├── alerts.py             # /alerts, PATCH /alerts/{id}
│   │   │   ├── blacklist.py          # /blacklist
│   │   │   └── ws.py                 # /ws/live-updates
│   │   └── schemas/                  # Pydantic request/response models
│   └── tests/
├── frontend/
│   ├── package.json
│   ├── src/
│   │   ├── routes/                   # 6 top-level routes (see below); Traffic Analytics'
│   │   │                             # 3 sub-views are tabs within one route, not separate routes
│   │   │   ├── dashboard/
│   │   │   ├── vehicle-trace/
│   │   │   ├── traffic-analytics/    # tabs: Heatmap | OD Matrix | Segment Detail
│   │   │   ├── alerts/
│   │   │   ├── blacklist/
│   │   │   └── cameras/
│   │   ├── components/               # Confidence Badge, Status Dot, Map Panel, Alert Card, Data Table, Empty State Panel
│   │   └── lib/api.ts                # typed API client
│   └── tests/
├── data/
│   ├── seed/                         # cameras.json, road_edges.json (§3)
│   ├── footage/                      # recorded/simulated camera clips per scenario
│   └── ground_truth/                 # known plates, staged journeys (§3)
└── docs/                             # this brief + the 8 other project documents
```

**Route / screen-count clarification:** The App/Website Flow Screen Inventory contains **8 screens** because Traffic Analytics is specified as three sub-views (Heatmap, OD Matrix, Segment Detail). The implementation uses **6 top-level frontend routes**, with those three Traffic Analytics views implemented as tabs within the single `/traffic-analytics` route. The Team Roles Guide (v1.2) still contains the legacy wording "all 8 routes" in its P1 M1 section; that wording refers to the eight Screen Inventory entries and should **not** be interpreted as a requirement for eight URL routes. The Agent Build Brief's 6-route structure is the implementation source of truth.

Each of the five layer folders (`perception`, `identity`, `spatial_temporal`, `network_intel`, `prediction_anomaly`) is a separable Python package with a defined function-level interface, per the Layer Model (TRD §1.2, NFR-08). The `alerts` folder is a cross-cutting module for the Alert System, not one of the five layers — it consumes output from the other layers (anomalies, blacklist hits) to produce the unified alert log, and now also owns the `PATCH /alerts/{id}` review-write path. All modules run inside one FastAPI process; this satisfies NFR-08 without needing microservices.

---

## 2. Locked-Down Thresholds, Weights, and Formulas
None of the source documents specify numeric defaults. These are proposed defaults — safe to tune later, but an agent needs *something* concrete to build against on day one.

### 2.1 Identity Score (FR-ID-02)
```
identity_score = 0.5 * plate_similarity
               + 0.3 * ocr_confidence_component
               + 0.1 * (1 if type_match else 0)
               + 0.1 * (1 if colour_match else 0)
```
- `plate_similarity`: normalized Levenshtein similarity (1 - edit_distance / max_len) between two fused plate texts.
- Low-confidence threshold (FR-ID-04 / UI/UX Brief §9.1): **identity_score < 0.70** → marked "Low Confidence" in UI.
- Candidate (non-confirmed) match threshold: **0.40 ≤ identity_score < 0.70**.
- Confirmed match: **identity_score ≥ 0.70**.

### 2.2 Impossible Journey (FR-STR-04)
```
implied_speed_kmph = distance_km / (time_gap_hours)
is_impossible_journey = implied_speed_kmph > (speed_limit_kmph * 1.5)
```
- The `* 1.5` multiplier is the "configurable plausible threshold" — store it in `config.py` as `IMPOSSIBLE_JOURNEY_SPEED_MULTIPLIER`, not hardcoded, so it's tunable without a migration.
- Reachability check (FR-STR-02): a candidate match is only considered if `time_gap ≥ min_travel_time_s` for the connecting edge (or shortest path across edges).

### 2.3 Camera Reliability Weighting (FR-PRD-03)
- Reliability profile values (`day_ocr_reliability`, etc.) are multiplied into `ocr_confidence_component` before it enters the identity score formula above:
  `effective_ocr_confidence = raw_ocr_confidence * applicable_reliability_factor`
- Condition selection (day/night/rain/angle) defaults to **time-of-day + a static per-camera "rain" flag** in the seed data for the prototype — no live weather feed is required (out of scope).

### 2.4 Congestion Status (FR-ANL-03)
```
free       : density < 20 vehicles/window AND avg_speed_kmph ≥ 0.7 * speed_limit_kmph
moderate   : density 20–40 OR avg_speed_kmph between 0.4–0.7 * speed_limit_kmph
congested  : density > 40 OR avg_speed_kmph < 0.4 * speed_limit_kmph
precedence : evaluate congested first; if conditions overlap, congested wins over moderate
```
Window default: **5-minute rolling aggregation**, configurable via `ANALYTICS_WINDOW_SECONDS`.

### 2.5 Congestion Forecast (FR-PRD-01)
Prototype uses a **linear trend heuristic**, not ML:
```
predicted_density(t+15min) = current_density + (current_density - density_15min_ago)
congestion_probability = clamp(predicted_density / 40, 0, 1)   # 40 = congested threshold from §2.4
```
Labeled in the UI as a heuristic estimate (per UI/UX Brief §4.5) — this is intentional per PRD §3.2 (narrated/lightweight scope), not a shortcut to fix later.

### 2.6 Anomaly Types (FR-PRD-02)
- `impossible_journey`: from §2.2.
- `duplicate_plate`: same `fused_plate_text` observed at two cameras with overlapping/near-simultaneous timestamps that are *not* graph-reachable apart (i.e., can't both be true).
- `camera_inconsistency`: flagged using only fields already in the schema — no new "operating window" column is introduced. The UI/display label may be "Camera Inconsistency" or "Camera-Timestamp Inconsistency", but the persisted/database enum value MUST be exactly `camera_inconsistency`. An observation triggers this anomaly when either:
  - its `captured_at` is earlier than the `captured_at` of the immediately preceding `vehicle_observations` row for the same `camera_id` + `track_id` (a same-track timestamp that moves backward in time), or
  - it deviates from the expected timestamp sequence of the simulated/recorded feed it was generated from (i.e., the demo dataset can inject a deliberately out-of-order frame timestamp for a staged test case, and the check simply detects any `captured_at` that is out of order relative to ingestion order for that camera).
  This keeps the anomaly detectable from existing `vehicle_observations` data alone and avoids adding a per-camera schedule field to the Backend Schema.

---

## 3. Seed / Demo Data Requirements (P3 ownership)
The agent cannot proceed past M1 without this. Minimum viable seed set:

- **Cameras:** 8–12 nodes forming a small connected road graph (enough for OD matrix and at least 2 distinct routes between any given origin/destination).
- **Road edges:** fully connecting the camera nodes above with realistic `distance_km`, `min_travel_time_s`, `max_travel_time_s`, `speed_limit_kmph`.
- **Footage/simulated frames:** at least one clip per camera with 3–5 known ground-truth vehicles passing through, covering: normal daylight, low-light, angled/motion-blur, and one dirty/damaged plate — to exercise FR-PER-05's >90% accuracy claim meaningfully.
- **Staged scenarios required for demo (Implementation Plan M4 QA):**
  1. One normal multi-camera trajectory (3+ camera hits, chronological, plausible speeds).
  2. One **impossible-journey pair** (two camera hits requiring implausible speed).
  3. One **duplicate-plate** case.
  4. One **camera_inconsistency** case (camera-timestamp inconsistency in the UI/demo wording).
  5. One **blacklisted plate** appearing live, to trigger FR-ALT-02.
  6. One **camera failure mid-run** (TRD §7 M2 checklist) — a corrupted/killed feed to prove graceful degradation.

Store as `data/seed/cameras.json`, `data/seed/road_edges.json`, and `data/ground_truth/scenarios.md` describing each staged case and its expected system output (so P3/QA can verify against a written expectation, not just eyeball the demo).

---

## 4. Repo/Env Scaffolding
- **Backend:** Python 3.11, FastAPI, SQLAlchemy + Alembic, `pyproject.toml` managed with `uv` or `poetry` (agent's choice, but pin one).
- **Frontend:** Vite + React + TypeScript, MapLibre GL JS, a lightweight chart library (e.g., Recharts) for OD matrix flow-volume bars and forecast panel.
- **DB:** PostgreSQL 16 + PostGIS extension, run via `docker-compose.yml` alongside the backend.
- **`.env.example` keys:**
  ```
  DATABASE_URL=postgresql://trace:trace@db:5432/trace
  IMPOSSIBLE_JOURNEY_SPEED_MULTIPLIER=1.5
  IDENTITY_CONFIRM_THRESHOLD=0.70
  IDENTITY_CANDIDATE_THRESHOLD=0.40
  ANALYTICS_WINDOW_SECONDS=300
  JWT_SECRET=changeme
  JWT_EXPIRY_MINUTES=480
  ```

---

## 5. Auth (NFR-06 minimum viable version)
- JWT-based session, issued on login against the `users` table (`password_hash` via bcrypt/argon2).
- JWT role claim (`operator` / `analyst` / `admin`) is enforced **server-side** by FastAPI for protected endpoints — implement as a simple FastAPI dependency (e.g. `require_role("admin")`) applied to routes like `POST /blacklist`, rather than trusting the client to withhold requests. The frontend additionally uses the role to control which navigation items and actions are displayed (UI/UX Brief §3), but this is a UX convenience layered on top of the server-side check, not a substitute for it.
- Role-to-endpoint mapping for the prototype:
  - **Shared Dashboard read access (all authenticated roles):** `GET /analytics/heatmap`, `GET /alerts`, `GET /vehicles/{plate}/trajectory` (for the globally accessible quicksearch), and `GET /blacklist`.
  - **Analytics read access:** `GET /analytics/*` → operator + analyst + admin.
  - **Alert review write access:** `PATCH /alerts/{id}` → operator + admin (the two personas the Flow document assigns this action to — Flow 3 Step 5 and Flow doc §1.2; Analyst is excluded, consistent with the Analyst persona's "rather than individual vehicles/alerts" scope).
  - **Blacklist write access:** `POST /blacklist` → admin only.
  - `/ws/live-updates` is available to all authenticated roles for live observation, alert, heatmap and camera-status updates; no separate `/cameras` REST endpoint is introduced here because the locked TRD API contract does not include one.
- **Shared Dashboard compatibility:** The Dashboard is shared by all three personas. Its heatmap, recent-alerts widget, and global vehicle quicksearch therefore use the shared read mappings above and must not produce 403 responses for an authenticated persona.

This is the prototype's minimal role-restriction implementation — enough to satisfy NFR-06's "role-restricted" requirement without building a full enterprise authorization system. Full enterprise privacy/access controls (fine-grained permissions, audit trails, encryption-at-rest policy) remain out of scope per PRD §3.3 and should be documented as such in the README.

---

## 6. QA / Definition-of-Done Checklist (supplements Implementation Plan §6)
Beyond the M2 NFR-05 six-item checklist already specified in the TRD, the agent should produce and check off, per milestone:

- [ ] M1: seed data loads; all 6 top-level routes render with mocked data; schema migrations run cleanly.
- [ ] M2: FR-PER-01–05 demonstrable; M2 NFR-05 six-item checklist passed and recorded.
- [ ] M3: identity_score computed and displayed with Evidence Panel breakdown for at least one low-confidence and one high-confidence match.
- [ ] M4: all 6 staged scenarios from §3 reproduce their expected outcome exactly.
- [ ] M5: heatmap, OD matrix, segment detail, and forecast all read from the same trajectory dataset (PRD §9 acceptance criterion).
- [ ] M6: blacklist alert fires live during a scripted demo run end-to-end without restarting any service; an operator/admin can mark an alert reviewed via `PATCH /alerts/{id}` and the state persists across a page reload.

---

## 7. Source-Document Consistency Notes
The following notes record how prior source-document inconsistencies were resolved, so the coding agent does not re-litigate settled scope while reconciling documents:

- **Alert review persistence — RESOLVED (TRD v1.3):** `PATCH /alerts/{id}` is the explicit write endpoint for the existing alert-review action. The request updates the alert's `reviewed` state; the backend records `reviewed_by` from the authenticated user and sets/clears `reviewed_at` accordingly. No new table or field was required — see Backend Schema §7.3. Role mapping is `operator + admin` (§5 above).
- **Backend Schema ER wording — RESOLVED:** Backend Schema §2 previously said `blacklist_matches` feeds alerts; the schema itself defines `blacklist_entries`, and the current Backend Schema (§2, §11) has been corrected to use `blacklist_entries` throughout. For implementation, follow the actual table definition and API-to-table mapping: `blacklist_entries`.

These notes identify how prior source inconsistencies were closed; they do not change the locked requirements, API contract, database schema, milestones, or team roles.

---

## 8. What This Brief Deliberately Does Not Add
No new functional requirements, screens, or tables are introduced. The alert-review endpoint and its role mapping are the concrete API implementation of behavior already specified in the Flow and UI/UX documents. Every value above is a *default* inside a threshold or config value already implied by an existing FR/NFR — chosen so the agent has one unambiguous number to start from rather than five equally plausible ones. Tune after the first demo run against real seed data.

— End of Agent Build Brief, Revised v1.1 —
