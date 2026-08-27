# TRACE
Tracking, Recognition, Analytics & City-wide Traffic Enforcement

## Project Requirement Document — Revised v1.1

Revision: Section 7.2 team-composition wording only. All functional requirements, NFRs, scope, milestones and acceptance criteria remain unchanged.

Problem Statement ID: 26127 | Organization: Bharat Electronics Limited | Category: Software | Theme: Transportation & Logistics

### 1. Introduction

#### 1.1 Purpose
This PRD defines what TRACE must achieve to satisfy Problem Statement 26127 and the team's quality bar of a complete, working, flaw-free system. It is the source document for the Technical Requirement Document, App/Website Flow, UI/UX Brief, Backend Schema and Implementation Plan.

#### 1.2 Project Background
Modern cities operate large networks of CCTV and ANPR cameras, but these networks typically function as isolated silos. TRACE addresses this by linking observations across space and time and extracting city-level traffic patterns.

#### 1.3 Guiding Principle
TRACE is a spatio-temporal vehicle intelligence system structured around five layers: Layer 1 Perception; Layer 2 Identity; Layer 3 Spatial-Temporal Reasoning; Layer 4 Network Intelligence; Layer 5 Prediction & Anomaly Reasoning.

### 2. Project Objectives
- OBJ-1: Deliver an ANPR/OCR engine with greater than 90% recognition accuracy across varied real-world conditions.
- OBJ-2: Reconstruct the complete city-wide trajectory of any queried vehicle plate with timestamps, direction and route on a GIS map.
- OBJ-3: Compute and visualize macro traffic analytics including density, origin-destination patterns, congestion bottlenecks and heatmaps.
- OBJ-4: Flag blacklisted vehicles and anomalous routes in real time through an alert system.
- OBJ-5: Differentiate TRACE through multi-modal identity fusion, road-graph-constrained reasoning and self-validating anomaly detection.
- OBJ-6: Deliver a working, end-to-end, demo-ready prototype covering every functionality above across six milestones.

### 3. Scope

#### 3.1 In-Scope — Core Build
- Vehicle detection, tracking and plate localization from live or simulated/recorded camera feeds.
- OCR with confidence scoring and temporal evidence aggregation.
- Multi-modal identity fusion using plate text, OCR confidence, vehicle type and colour.
- Road-graph model of camera nodes and connecting road segments.
- Query-based trajectory reconstruction on a GIS map.
- Impossible-journey anomaly detection using road-graph travel-time constraints.
- City Traffic Analytics Dashboard with heatmaps, density and route statistics.
- Blacklist-based real-time alerting.

#### 3.2 In-Scope — Narrated / Lightweight Implementation
- Congestion prediction using a heuristic or lightweight time-series projection.

### 6. Non-Functional Requirements

| Category | ID | Requirement |
|---|---|---|
| Accuracy | NFR-01 | OCR/ANPR recognition accuracy shall exceed 90% on the evaluation dataset. |
| Performance | NFR-02 | Trajectory queries shall return within an acceptable interactive response time on the demo dataset. |
| Scalability | NFR-03 | Additional camera nodes can be added without redesigning the schema. |
| Usability | NFR-04 | Dashboard shall present trajectory, heatmap and alert views through a single consistent navigation structure. |
| Reliability | NFR-05 | System shall degrade gracefully when a camera feed is unavailable, rather than failing the entire pipeline. |
| Security & Privacy | NFR-06 | Access to trajectory and identity data shall be role-restricted; production encryption/retention path documented. |
| Explainability | NFR-07 | Every identity match and anomaly flag shall have a confidence score or reason code. |
| Maintainability | NFR-08 | Each of the five layers shall be implemented as a separable module with a defined interface. |

### 7. Assumptions and Constraints

#### 7.1 Assumptions
- Live camera feeds from an actual city ANPR network will not be available; recorded or simulated multi-camera footage with known ground-truth plates will be used.
- Road-graph distances and expected travel times can be approximated using map data for the demo area.
- The demo dataset will contain a manageable number of camera nodes.

#### 7.2 Constraints — REVISED
- The project must be completed within the timeline defined in the Implementation Plan, by the team constituted for execution — originally scoped as six roles, executed as three (P1 Frontend, P2 Backend + ML, P3 Data Collection & Support) per the Team Roles & Milestone Contribution Guide v1.2 and Implementation Plan v1.3.
- The technology stack is deliberately limited to tools the team can realistically operate under deadline pressure.
- Kafka, Kubernetes, Neo4j, and edge-hardware deployment are constrained to design documentation only.

### 8. Dependencies and Traceability
The PRD remains the source document for the Technical Requirement Document, App/Website Flow, UI/UX Brief, Backend Schema and Implementation Plan. The v1.3 Implementation Plan and v1.2 Team Roles Guide define current execution ownership.

### 9. Success and Acceptance Criteria
- All FR-xxx requirements are implemented and demonstrable in a single end-to-end run.
- OCR/ANPR accuracy exceeds 90% on the evaluation dataset.
- A queried plate returns a correct chronological GIS trajectory including an impossible-journey flag.
- Analytics displays heatmap, density and OD-pattern views from the same trajectory dataset.
- A blacklisted plate triggers a visible real-time alert during the live demo.
- The accompanying documents remain mutually consistent.

### 10. Glossary

| Term | Definition |
|---|---|
| Layer Model | Five-layer intelligence framework: Perception, Identity, Spatial-Temporal Reasoning, Network Intelligence, Prediction & Anomaly. |

— TRACE PRD, Revised v1.1 —

**Editorial note (added for consistency, no functional change):** §7.2 and §8 above now reference the Team Roles Guide as v1.2, reflecting that document's §6 correction (App/Website Flow's status updated to v1.1). No FR/NFR/scope/milestone/acceptance-criteria content in this PRD changed.
