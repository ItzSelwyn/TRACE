# TRACE — Frontend Roadmap (Figma → Code → Repo)
### For Nigesh & Pallavi (P1 Frontend Ownership)

Derived from: UI/UX Brief v1.0, App/Website Flow v1.1, TRD v1.3, Team Roles Guide v1.2, Implementation Plan v1.3.

---

## Phase 0 — What you're actually building (recap, don't skip)

**6 top-level routes** (not 8 — Traffic Analytics' three views are tabs on one screen, and Segment Detail is a slide-over, not a route):

| # | Route | Primary API(s) | Spec source |
|---|---|---|---|
| 1 | Dashboard (Home) | `/analytics/heatmap`, `/alerts` | Flow §7, Brief §4.1 |
| 2 | Vehicle Trace | `/vehicles/{plate}/trajectory` | Flow §7, Brief §4.2 |
| 3 | Traffic Analytics (Heatmap / OD Matrix / Segment Detail tabs) | `/analytics/heatmap`, `/analytics/od-matrix`, `/analytics/segments/{id}`, `/analytics/forecast/{segment_id}` | Flow §7, Brief §4.3–4.5 |
| 4 | Alerts | `/alerts`, `PATCH /alerts/{id}` | Flow §7, Brief §4.6 |
| 5 | Blacklist Management | `/blacklist` | Flow §7, Brief §4.7 |
| 6 | Camera Network Status | `/ws/live-updates` | Flow §7, Brief §4.8 |

**6 shared components** that every screen is built from (Brief §2.3):
Confidence Badge, Status Dot, Alert Card, Data Table, Map Panel, Empty State Panel.

**Non-negotiable rules baked into the spec** — keep these in mind while designing, not just while coding:
- Color carries exactly one meaning platform-wide (Brief §2.2) — don't let Figma layers drift from the token table.
- Confidence/status is never color-only — always paired with a text label or % (Brief §7, accessibility).
- Every screen with no data gets an explicit Empty State, never a blank panel (Brief §9.3 in Flow doc, §4.1/4.2 in Brief).
- A down/degraded camera is shown as a distinct state, never disguised as normal data (NFR-05, Brief §1.2).

---

## Phase 1 — Figma (you are here)

### 1.1 File structure inside Figma
Set up **4 pages**, in this order, so downstream pages can reference earlier ones as Figma components/styles:

1. **`00 – Foundations`** — color styles (from Brief §2.2 hex table), text styles (Aptos: Page Title, Section Heading, Body, Micro/Meta per Brief §2.1), spacing/grid.
2. **`01 – Components`** — the 6 core components as Figma components with variants:
   - Confidence Badge → variants: `high` / `low`
   - Status Dot → variants: `online` / `degraded` / `down`
   - Alert Card → variants: `blacklist` / `impossible-journey` / `duplicate-plate` / `camera-inconsistency`, each × `reviewed` / `unreviewed`
   - Data Table, Map Panel, Empty State Panel
3. **`02 – Navigation Shell`** — the persistent left nav + top bar (Brief §3), built once, since it wraps every screen.
4. **`03 – Screens`** — one frame per route (6 frames + Segment Detail as a 7th "overlay" frame), each built by dragging in the components from page 01.

### 1.2 Splitting the work between you and Pallavi
Suggested split so you're not both editing the same frames:

- **Nigesh:** Foundations + Components (page 00–01) first, since everything else depends on it → then Dashboard, Vehicle Trace, Alerts (the data-heavy, map-heavy screens).
- **Pallavi:** Navigation Shell (page 02) once Foundations lands → then Traffic Analytics (3 tabs), Blacklist Management, Camera Network Status.

Do Foundations + Components together (even a 30-minute pairing session) before splitting — if you diverge on token names or component structure here, it costs both of you time later in code.

### 1.3 Order to design screens in
Match M1's priority, not visual difficulty: Dashboard and Vehicle Trace first (they're the demo's spine), Alerts second (cross-cutting, appears on every screen as a nav badge), then Traffic Analytics, Blacklist, Camera Network.

### 1.4 What "done" looks like before you hand off to code
- Every screen has an **Empty State** variant and, where relevant, a **loading** state — don't only design the happy path.
- Confidence Badge and Status Dot are true Figma components (not just styled rectangles), so engineering can map one component → one React component 1:1.
- A short annotation layer (or a separate `Notes` page) capturing anything not obvious from the frame — e.g. "this badge turns amber below X% — exact threshold TBD by P2."

---

## Phase 2 — Figma → Code (once designs are ready)

When you're ready, share the Figma file (or export specs/screenshots) and we'll go screen by screen. Two ways I can help, depending on what you have connected:

- If you connect the **Figma MCP connector**, I can pull real design tokens, component structure, and layout data directly from your file and generate matching React/TypeScript components.
- Otherwise, share exported frames/screenshots and the underlying values (hex codes, spacing, font sizes if they drifted from the Brief), and I'll build from those.

Either way, code gets built in the same order as Figma: Foundations (design tokens) → shared components → navigation shell → screens.

### Proposed stack
Per TRD §3.1: **React + MapLibre GL + a charting library**, WebSockets with polling fallback. Not specified by any doc, so pick before Phase 2 starts:
- **Bundler:** Vite (fast, matches Team Roles Guide §2 M1 wording: "React/Vite shell")
- **Language:** TypeScript
- **Styling:** Tailwind CSS recommended — maps cleanly onto Figma's token-based design system and lets two people style independently without collisions. (Your call — CSS Modules or styled-components work too if you prefer.)
- **Charting:** Recharts (lightweight, good with React + TS)
- **State/data fetching:** React Query (or SWR) for the REST calls, plain WebSocket hook for `/ws/live-updates`

### Proposed file structure

```
trace-frontend/
├── public/
├── src/
│   ├── assets/                     # icons, images
│   ├── styles/
│   │   ├── tokens.css               # color/type tokens from Brief §2.1–2.2
│   │   └── globals.css
│   ├── components/
│   │   ├── common/
│   │   │   ├── ConfidenceBadge/
│   │   │   ├── StatusDot/
│   │   │   ├── AlertCard/
│   │   │   ├── DataTable/
│   │   │   ├── MapPanel/
│   │   │   └── EmptyStatePanel/
│   │   └── layout/
│   │       ├── NavShell/
│   │       └── TopBar/
│   ├── screens/
│   │   ├── Dashboard/
│   │   ├── VehicleTrace/
│   │   │   └── EvidencePanel/       # slide-over, Brief §4.2
│   │   ├── TrafficAnalytics/
│   │   │   ├── HeatmapTab.tsx
│   │   │   ├── ODMatrixTab.tsx
│   │   │   └── SegmentDetailPanel.tsx  # slide-over, Brief §4.5
│   │   ├── Alerts/
│   │   ├── BlacklistManagement/
│   │   └── CameraNetworkStatus/
│   ├── api/                        # one file per TRD §5 endpoint group
│   │   ├── vehicles.ts
│   │   ├── analytics.ts
│   │   ├── alerts.ts
│   │   ├── blacklist.ts
│   │   └── liveUpdates.ts           # WebSocket hook
│   ├── hooks/
│   ├── types/                      # shared TS types (mirror Backend Schema fields)
│   ├── router.tsx                  # 6 top-level routes, no nesting >1 level (Flow §2)
│   ├── App.tsx
│   └── main.tsx
├── .env.example
├── package.json
├── tsconfig.json
└── vite.config.ts
```

This mirrors the App/Website Flow's navigation rule directly: **no destination nested more than one level deep** (Flow §2, NFR-04) — so `router.tsx` should stay flat, with Segment Detail and the Evidence Panel implemented as overlays/slide-overs inside their parent screen, not as separate routes.

---

## Phase 3 — Git workflow & pushing to remote

Per Implementation Plan §5 (unchanged since v1.1):

- `main` = stable/demo-ready only
- `dev` = shared integration branch
- Short-lived feature branches off `dev`
- PRs merge into `dev` after review; `dev` → `main` only after milestone acceptance

### Suggested setup once repo exists
```bash
git clone <repo-url>
cd trace-frontend
git checkout -b dev origin/dev        # or create it if it doesn't exist yet
git checkout -b feature/nav-shell dev # branch per component/screen
```

### Suggested branch naming (two frontend devs)
- `feature/foundations-tokens`
- `feature/nav-shell`
- `feature/dashboard`
- `feature/vehicle-trace`
- `feature/traffic-analytics`
- `feature/alerts`
- `feature/blacklist`
- `feature/camera-network`

One branch per screen/component keeps your PRs small and reviewable between just the two of you, and matches M1's "reusable components" then "screens" build order.

### Milestone gate
Per Implementation Plan §3–4, M1 exit criteria is the full shell + all routes + shared components in place — that's the target for the first `dev → main` merge, once P2's endpoints are ready enough to wire in (until then, per Team Roles Guide §5, you can build against mocked JSON matching the TRD §5 contract).

---

## Next step
Design in Figma using the structure above. When a screen (or the whole file) is ready, bring it back here — either connect Figma so I can pull it directly, or share exports — and we'll start converting to code in the same order: tokens → shared components → nav shell → screens.
