# TRACE
### Tracking, Recognition, Analytics & City-wide Traffic Enforcement
_App/Website Flow Document_

| Field | Detail |
|---|---|
| Problem Statement ID | 26127 |
| Project Title | TRACE (Tracking, Recognition, Analytics & City-wide Traffic Enforcement) |
| Document Type | App/Website Flow |
| Derived From | TRACE PRD v1.0, TRACE TRD v1.0 |
| Status | Revised v1.1 |

**Revision v1.1:** Adds `PATCH /alerts/{id}` to Flow 3 Step 5 and to the Screen Inventory's Alerts row, to reflect the TRD v1.3 API addition that persists the alert-review action this document has always described. No user flow, screen, or persona behavior changed — only the endpoint reference backing an action already specified in Draft v1.0.

**Compatibility Note:** Compatible with PRD v1.1. Compatible with TRD v1.3 — the one endpoint referenced in this document that originates from a TRD revision is `PATCH /alerts/{id}` (added in TRD v1.3), reflected in Flow 3 Step 5 and the Screen Inventory below. No other flow, screen, or endpoint referenced here was changed by PRD v1.1, TRD v1.2, or TRD v1.3.

## 1. Introduction

#### 1.1 Purpose
This document defines the end-to-end user journeys through the TRACE web platform for each persona identified in the PRD, and maps each step to the screen involved, the API endpoint invoked (as defined in the TRD, Section 5), and the functional requirement(s) it satisfies. It is the direct source document for the UI/UX Brief, which will define the visual and interaction design of the exact screens listed here.

#### 1.2 Personas In Scope

| Persona | Description and Primary Need |
|---|---|
| Operator | Front-line user who traces a specific vehicle plate, reviews its trajectory, and responds to real-time alerts (blacklist hits, anomalies). |
| Analyst | Reviews city-wide traffic patterns — density, OD matrix, congestion, and forecasts — rather than individual vehicles. |
| Admin | Manages the blacklist and reviews the alert log; a lightweight persona layered on top of the Operator's access. |

#### 1.3 Design Principle
All three personas share a single web platform with one consistent navigation shell (NFR-04). The platform does not fork into separate apps — persona differences are handled through which navigation items and actions are surfaced, not through separate flows entirely, keeping the system simple to demo and to build within the timeline.

## 2. Site Map / Navigation Structure
The platform is organized around one persistent left/top navigation shell with the following primary destinations:

- Dashboard (Home) — city overview: live heatmap snapshot, recent alerts, quick plate search.
- Vehicle Trace — plate search and trajectory reconstruction view.
- Traffic Analytics — heatmap, OD matrix, segment statistics, congestion forecast.
- Alerts — live and historical alert log (blacklist hits and anomalies).
- Blacklist Management — add/view watched plates (Admin-facing action, visible to Operator as read-only where relevant).
- Camera Network — status view of camera nodes (feed up/down), supporting NFR-05 visibility.

Navigation path: Dashboard sits at the root; all other destinations are one click away from the shell at all times — no destination is nested more than one level deep, satisfying NFR-04's "usable without training" requirement.

## 3. User Flow 1 — Operator: Vehicle Trace
Goal: find a specific plate and view its full reconstructed trajectory. Satisfies FR-STR-03, FR-STR-04, FR-STR-05.

1. Operator lands on Dashboard and selects "Vehicle Trace" from the navigation shell, or uses the quick search box directly from the Dashboard.
2. Operator enters a plate number (full or partial) into the search field on the Vehicle Trace screen.
3. System calls `GET /vehicles/{plate}/trajectory`.
4. System displays the result as a chronological list of observations (camera, timestamp, confidence) alongside a GIS map plotting the route in order.
5. If any two consecutive observations were flagged as an impossible journey (FR-STR-04), the corresponding map segment and list entry are visually marked, with the reason (implied speed vs. threshold) shown on click/hover.
6. Operator can click any single observation to see the Identity Score and the evidence behind it (plate similarity, OCR confidence, attribute match), satisfying NFR-07 explainability.
7. Operator may filter the trajectory by time range to focus on a specific window.

Edge case: if no observations are found for the queried plate, the screen shows a clear "No observations found for this plate in the current data window" state rather than an empty map, and suggests checking the plate format.

## 4. User Flow 2 — Analyst: Traffic Analytics
Goal: review city-wide traffic patterns and congestion forecasts. Satisfies FR-ANL-01 to FR-ANL-05, FR-PRD-01.

1. Analyst selects "Traffic Analytics" from the navigation shell.
2. System calls `GET /analytics/heatmap` and renders the live density heatmap over the city map by default.
3. Analyst switches between three tabs on the same screen: Heatmap, OD Matrix, and Segment Detail — no page reload, satisfying NFR-04's single consistent navigation.
4. OD Matrix tab calls `GET /analytics/od-matrix` and renders it as a matrix/table plus a simple flow-volume visual.
5. Segment Detail tab: Analyst clicks a specific road segment on the map; system calls `GET /analytics/segments/{id}` to show average speed, density, and congestion status (FR-ANL-03, FR-ANL-05).
6. From Segment Detail, Analyst can open the "Forecast" panel, which calls `GET /analytics/forecast/{segment_id}` and displays the short-horizon congestion projection (FR-PRD-01), clearly labeled as a heuristic estimate rather than a guaranteed prediction.

Edge case: if live data for a segment is temporarily unavailable (e.g., a camera feed is down), the segment is shown greyed-out on the heatmap with a status note rather than silently showing stale or zero data (NFR-05).

## 5. User Flow 3 — Alert Handling (Operator/Admin)
Goal: respond promptly to a blacklist hit or anomaly flag. Satisfies FR-ALT-01 to FR-ALT-04, FR-PRD-02.

1. A blacklisted plate is recognized, or an anomaly is detected, triggering a push over `/ws/live-updates`.
2. A live alert banner/badge appears on the navigation shell (visible from any screen) so the Operator does not need to be on the Alerts screen to notice it.
3. Operator clicks through to the Alerts screen, which calls `GET /alerts` and lists alerts newest-first, each tagged by type (Blacklist Hit / Impossible Journey / Duplicate Plate / Camera Inconsistency).
4. Operator clicks an alert to jump directly into the Vehicle Trace screen for that plate, pre-loaded with the relevant trajectory (reusing Flow 1, Steps 3–6).
5. Operator can mark an alert as reviewed; the system calls `PATCH /alerts/{id}` with the new review state, and the review status is persisted via the alert log so the same alert is not repeatedly treated as new (FR-ALT-04).

## 6. User Flow 4 — Admin: Blacklist Management
Goal: add or review watched plates. Satisfies FR-ALT-01.

1. Admin selects "Blacklist Management" from the navigation shell.
2. Screen calls `GET /blacklist` and lists current watched plates with reason/date-added.
3. Admin enters a new plate and a reason, and submits; system calls `POST /blacklist`.
4. New plate is immediately active — any subsequent match against it anywhere in the system will trigger Flow 3.

## 7. Screen Inventory
This table is the direct handoff to the UI/UX Brief — every screen listed here will receive a corresponding visual/interaction specification.

| Screen | Key Components | Primary API(s) |
|---|---|---|
| Dashboard (Home) | Heatmap snapshot, recent alerts widget, quick plate search | `/analytics/heatmap`, `/alerts` |
| Vehicle Trace | Search bar, chronological observation list, GIS trajectory map, evidence detail panel | `/vehicles/{plate}/trajectory` |
| Traffic Analytics — Heatmap | Full-screen density heatmap, time-window filter | `/analytics/heatmap` |
| Traffic Analytics — OD Matrix | Matrix/table view, flow-volume visual | `/analytics/od-matrix` |
| Traffic Analytics — Segment Detail | Segment stats panel, forecast sub-panel | `/analytics/segments/{id}`, `/analytics/forecast/{segment_id}` |
| Alerts | Filterable alert log, review-status toggle | `/alerts`, `PATCH /alerts/{id}` |
| Blacklist Management | Watched-plate table, add-plate form | `/blacklist` |
| Camera Network Status | List/map of camera nodes with up/down status (derived from Perception Module health, exposed via FastAPI API layer) | `/ws/live-updates` |

## 8. Navigation Flow Summary
Dashboard is the shared entry point. From Dashboard: → Vehicle Trace (direct search or via an alert), → Traffic Analytics (Heatmap → OD Matrix → Segment Detail → Forecast, all within one screen's tabs), → Alerts (→ jumps into Vehicle Trace per alert), → Blacklist Management, → Camera Network Status. Every destination also returns to Dashboard via the persistent navigation shell, so the Operator or Analyst is never more than one click from either their starting point or the next relevant action.

## 9. Cross-Cutting States

#### 9.1 Low-Confidence Match Handling
Wherever a match is shown (Vehicle Trace observation list, Alerts), an Identity Score below a configured confidence threshold is visually distinguished (e.g., marked "Low Confidence") rather than presented identically to a high-confidence match, directly supporting FR-ID-04 and NFR-07.

#### 9.2 Feed-Down Handling
Camera Network Status reflects feed availability in real time; any screen displaying data dependent on a down camera (heatmap segment, trajectory gap) shows a status indicator rather than silently omitting or fabricating data, supporting NFR-05.

#### 9.3 Empty and No-Result States
Vehicle Trace, Alerts, and Blacklist Management each define an explicit empty state with guidance text, so the platform never presents a blank screen without explanation.

## 10. Traceability
This document consumes the API contract defined in the TRD (Section 5) and the requirement IDs defined in the PRD (Section 5). It is the source document for the UI/UX Brief (screen-by-screen visual and interaction design) and informs the Backend Schema's read patterns (which endpoints are called most, and with what filters) and the Implementation Plan's milestone sequencing for frontend work.

— End of App/Website Flow Document, Revised v1.1 —
