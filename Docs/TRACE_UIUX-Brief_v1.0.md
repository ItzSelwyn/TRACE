# TRACE
### Tracking, Recognition, Analytics & City-wide Traffic Enforcement
_UI/UX Brief_

| Field | Detail |
|---|---|
| Problem Statement ID | 26127 |
| Project Title | TRACE (Tracking, Recognition, Analytics & City-wide Traffic Enforcement) |
| Document Type | UI/UX Brief |
| Derived From | TRACE PRD v1.0, TRACE TRD v1.0, TRACE App/Website Flow v1.0 |
| Document Owner | Nigesh (Project Lead) |
| Status | Draft v1.0 |

**Compatibility Note:** Compatible with PRD v1.1, TRD v1.3, and App/Website Flow v1.1. No screen, component, or data field specified here was affected by those revisions — the Alerts screen's "Review" toggle (§2.3, §4.6) was already specified in this brief exactly as-is; TRD v1.3 and Flow v1.1 only added the `PATCH /alerts/{id}` endpoint that backs the interaction this brief already described.

## 1. Introduction

#### 1.1 Purpose
This brief defines the visual language and screen-by-screen interaction design for the eight screens identified in the Screen Inventory of the App/Website Flow document. It does not introduce new screens, flows, or data — every element specified here exists to serve a functional requirement already defined in the PRD and a flow step already defined in the App/Website Flow document.

#### 1.2 Design Priorities
- Trust over decoration: since every match and alert carries uncertainty, the interface must make confidence visible at a glance, not hide it behind a polished but opaque result (supports NFR-07).
- Map-centric: the GIS map is the primary surface for trajectory and traffic screens, not a secondary widget beside a data table.
- One navigation shell, zero relearning: Operator, Analyst, and Admin see the same shell; only which items are relevant changes (supports NFR-04).
- Calm under alert load: alerts must be noticeable without being alarming enough to distract from an in-progress task.
- Graceful degradation visible in the UI itself: a down camera or low-confidence match is shown as a distinct state, never disguised as normal data (supports NFR-05).

## 2. Design System Foundations

#### 2.1 Typography
Primary typeface: Aptos, applied consistently across the web application and all project documentation, for a single coherent visual identity between the product and its submission materials.

| Role | Weight / Size (approx.) | Usage |
|---|---|---|
| Page Title | Bold, 24–28px | Screen-level heading in the content area (not the nav shell). |
| Section Heading | Bold, 18–20px | Panel/card headings, e.g. "Trajectory", "Segment Detail". |
| Body Text | Regular, 14–16px | Table cells, descriptions, form labels. |
| Micro / Meta Text | Regular, 12px | Timestamps, confidence percentages, camera IDs. |

#### 2.2 Colour Palette
Colour is used functionally, not decoratively — each colour has one consistent meaning across every screen so the Operator never has to re-interpret it in a new context.

| Token | Hex (indicative) | Meaning / Usage |
|---|---|---|
| Primary (Ink) | #0F172A | Primary text, headings, nav shell background. |
| Neutral Surface | #F5F6F8 | Page and card background. |
| Border / Divider | #D9D9D9 | Table borders, card outlines. |
| High Confidence | #1B7A43 | Identity Score above threshold; camera "online" status. |
| Low Confidence / Caution | #B8860B | Identity Score below threshold; degraded camera reliability. |
| Alert / Anomaly | #B3261E | Blacklist hits, impossible-journey flags, camera-down status. |
| Heatmap Scale (Low→High) | #2E7D32 → #F9A825 → #C62828 | Density gradient on Traffic Analytics heatmap, low to high. |

Note: this palette governs the TRACE web application's UI. All project documentation (this brief included) remains black text on white, left-aligned, per the team's document formatting standard — the palette above is content describing the product, not a formatting instruction for this document.

#### 2.3 Core Components
- Confidence Badge — a small pill showing a percentage and colour (High / Low Confidence tokens), used next to every match, plate read, and forecast value.
- Status Dot — green/amber/red dot used for camera online/degraded/down status.
- Alert Card — compact card with type icon, plate, camera, timestamp, and a "Review" action.
- Data Table — consistent striped-row table used for observation lists, blacklist, and OD matrix.
- Map Panel — the shared MapLibre-based component used across Vehicle Trace, Heatmap, and Segment Detail, differing only in overlay layer.
- Empty State Panel — icon, one-line explanation, and a suggested next action; used wherever a screen has no data to show.

## 3. Navigation Shell Layout
A persistent left-hand vertical navigation bar (collapsible to icon-only on smaller viewports) contains: Dashboard, Vehicle Trace, Traffic Analytics, Alerts, Blacklist Management, Camera Network. The current alert count is shown as a badge on the Alerts nav item, and updates live via the `/ws/live-updates` channel (App/Website Flow, Flow 3). The top bar carries the screen title, a global plate quicksearch field (always accessible, mirroring the Dashboard's quick search), and the signed-in persona indicator.

## 4. Screen-by-Screen Specifications

#### 4.1 Dashboard (Home)
- Layout: three-zone grid — heatmap snapshot (left, ~60% width), recent alerts list (top right), quick plate search (prominent, top of content area).
- Interaction: clicking the heatmap snapshot navigates to Traffic Analytics — Heatmap; clicking an alert card navigates into Vehicle Trace for that plate (Flow 3).
- States: recent alerts list shows an Empty State Panel ("No alerts in the current window") when empty, never a blank card.

#### 4.2 Vehicle Trace
- Layout: search bar full-width at top; below it, a two-column layout — chronological observation list (left, ~35%) and Map Panel with plotted trajectory (right, ~65%).
- Observation list rows: camera ID, timestamp, thumbnail-style vehicle type/colour tag, and a Confidence Badge; an impossible-journey pair is connected by a red dashed line on the map and both list rows carry an Alert-coloured left border.
- Clicking a row opens an Evidence Panel (right-side slide-over) showing the Identity Score breakdown: plate similarity, OCR confidence, attribute match — each as its own labelled bar (FR-ID-04, NFR-07).
- Time-range filter sits above the observation list as a compact date/time range control.
- Empty state: centered Empty State Panel with "No observations found for this plate in the current data window" and a prompt to check the plate format.

#### 4.3 Traffic Analytics — Heatmap
- Layout: full-bleed Map Panel with heatmap overlay; a compact legend (Heatmap Scale) fixed to the bottom-left corner; a time-window selector fixed top-right of the map.
- A camera/segment with unavailable data is rendered in a flat grey rather than omitted or shown as zero-density green, to avoid misreading "no data" as "no traffic" (NFR-05).

#### 4.4 Traffic Analytics — OD Matrix
- Layout: tabbed within the same Traffic Analytics screen as Heatmap; matrix rendered as a table with origin zones as rows and destination zones as columns, cell shade intensity reflecting trip volume.
- A simple flow-volume bar list beneath the matrix highlights the top five origin-destination pairs for quick reading without requiring the full matrix to be parsed.

#### 4.5 Traffic Analytics — Segment Detail
- Layout: opened by clicking a segment on the Heatmap or OD Matrix tab; appears as a right-side slide-over panel (not a full navigation away), so the Analyst keeps map context.
- Panel contents: segment name, average speed, density, congestion status (Status Dot), and a collapsible Forecast sub-panel showing the short-horizon projection with a visible "heuristic estimate" label (FR-PRD-01).

#### 4.6 Alerts
- Layout: single-column list of Alert Cards, newest first, with a filter bar (type, reviewed/unreviewed) above the list.
- Each Alert Card shows a type icon (Blacklist / Impossible Journey / Duplicate Plate / Camera Inconsistency), plate, camera, timestamp, and a "Review" toggle; reviewed alerts visually recede (reduced-emphasis styling) but remain in the list.
- Clicking a card's plate/body (not the Review toggle) opens Vehicle Trace for that plate, prefiltered to the relevant time window.

#### 4.7 Blacklist Management
- Layout: watched-plate table (plate, reason, date added, added by) with an "Add Plate" action opening a small modal form (plate number, reason — required fields).
- Newly added plates appear at the top of the table immediately on save, with a brief success confirmation.

#### 4.8 Camera Network Status
- Layout: split view — list of camera nodes with Status Dot and last-seen timestamp (left), map of the same nodes colour-coded by status (right).
- A degraded/down camera row links directly to any trajectories currently showing a gap because of that camera, helping the Operator understand downstream impact rather than viewing the outage in isolation.

## 5. Map Visualization Guidelines
- Trajectory line: solid line between consecutive normal observations; red dashed segment for an impossible-journey pair (Section 4.2).
- Camera markers: circular markers colour-coded by Status Dot convention (green/amber/red), consistent between Vehicle Trace, Segment Detail, and Camera Network Status.
- Heatmap overlay: continuous colour gradient per the Heatmap Scale token (Section 2.2), refreshed on the live update interval, with a visible legend at all times — never an unlabelled colour overlay.
- Zoom/pan state should persist when a user switches between Heatmap and OD Matrix tabs on the same screen, so context is not lost on every tab change.

## 6. Responsive Behaviour
The prototype targets desktop/laptop usage as the primary demo environment (an operations-style dashboard), with the navigation shell collapsing to icon-only below a defined breakpoint and two-column layouts (e.g., Vehicle Trace) stacking to a single column with the map above the list on narrower viewports. Full mobile optimization is not required for the prototype demo but the layout should not visibly break on a standard tablet width.

## 7. Accessibility Considerations
- Confidence and status information is never conveyed by colour alone — every Confidence Badge and Status Dot is paired with a text label or percentage.
- Minimum text contrast follows standard AA guidance against the Neutral Surface background.
- All interactive elements (map markers, table rows, Alert Cards) are reachable and operable via keyboard focus order, not click-only.

## 8. Traceability
Every screen specified in Section 4 corresponds one-to-one with a row in the App/Website Flow document's Screen Inventory, which in turn traces to specific FR-xxx requirements in the PRD and API endpoints in the TRD. This brief introduces no new data fields — the Backend Schema document defines the exact fields (e.g., Identity Score breakdown, alert type, camera status) that populate the components specified here.

— End of UI/UX Brief —
