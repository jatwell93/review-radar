---
phase: 01-free-tier-mvp
plan: 05
subsystem: ui
tags: [csv, export, pdf, print, netlify, render, deployment, toml, yaml]

requires:
  - phase: 01-04
    provides: Results dashboard with narrative card — complete UI to export from

provides:
  - CSV export button in ResultsDashboard — downloads review-radar-report.csv with BOM, metadata, reviews, narrative
  - PDF/print export button — window.print() with print:hidden on action row
  - netlify.toml at repo root — Netlify build config for frontend/ Next.js app
  - render.yaml at repo root — Render web service config for backend/ FastAPI app

affects: [Phase 2, deployment]

tech-stack:
  added: []
  patterns:
    - CSV export as inline helper (no npm packages) — sanitizeCell prevents formula injection
    - UTF-8 BOM prepended to CSV blob for Windows Excel compatibility
    - DOM-append-before-click pattern for cross-browser download (Safari fix)
    - setTimeout revokeObjectURL to defer cleanup until download queues
    - print:hidden Tailwind class hides action row in browser print output
    - render.yaml sync:false keeps secrets out of version control

key-files:
  created:
    - netlify.toml
    - render.yaml
  modified:
    - frontend/src/components/ResultsDashboard.tsx

key-decisions:
  - "CSV export inline (no jsPDF/FileSaver) — zero new runtime dependencies per plan boundaries"
  - "PDF via window.print() — MVP-appropriate; avoids puppeteer/wkhtmltopdf complexity"
  - "print:hidden on action row only — dashboard content renders as-is in print"
  - "netlify.toml publish = .next (not out) — app uses Next.js App Router, no static export"
  - "render.yaml sync:false on secrets — secrets stay in Render dashboard, not committed to repo"
  - "healthCheckPath: /health — app-level monitoring (not just TCP binding)"

patterns-established:
  - "Export helpers as module-level functions (not inside component) — keeps component body clean"
  - "print:hidden applied at container level — single class hides entire action row"

duration: ~15min
started: 2026-05-02T00:00:00Z
completed: 2026-05-02T00:00:00Z
---

# Phase 1 Plan 05: Export + Deployment Config

**CSV and PDF export buttons wired into the results dashboard; Netlify and Render deployment configs committed — Phase 1 free-tier MVP is fully deliverable.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~15 min |
| Started | 2026-05-02 |
| Completed | 2026-05-02 |
| Tasks | 3 completed |
| Files modified | 3 |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: CSV export downloads structured report file | Pass | Downloads `review-radar-report.csv` with UTF-8 BOM; metadata rows (score, counts), positive + critical review rows; formula-injection sanitized |
| AC-2: PDF export opens browser print dialog | Pass | `window.print()` called; action row hidden via `print:hidden`; dashboard content renders in print as-is |
| AC-3: Netlify config builds frontend from subdirectory | Pass | `netlify.toml` at repo root; `base = "frontend"`, `command = "npm run build"`, `publish = ".next"`, `NODE_VERSION = "20"`; TOML valid |
| AC-4: Render config deploys FastAPI backend | Pass | `render.yaml` at repo root; `rootDir: backend`, `buildCommand: pip install -r requirements.txt`, `startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT`; `healthCheckPath: /health`; `ANTHROPIC_API_KEY` + `ALLOWED_ORIGINS` both `sync: false` |

## Accomplishments

- CSV export generates a structured 3-column report (Type / Detail / Sentiment Score) with UTF-8 BOM for Windows Excel compatibility, formula-injection sanitization, and cross-browser download pattern (DOM-append before click, deferred revokeObjectURL)
- PDF/print export via `window.print()` with `print:hidden` on the action row — buttons disappear in print preview, dashboard content renders cleanly
- `netlify.toml` configures Netlify to build Next.js from `frontend/` subdirectory on Node 20; `NEXT_PUBLIC_API_URL` documented for dashboard env var entry
- `render.yaml` configures Render to deploy FastAPI from `backend/` with health monitoring (`/health`), correct `$PORT` binding, and secrets excluded from version control (`sync: false`)
- Frontend build exits 0 with zero TypeScript errors after all changes

## Task Commits

| Task | Status | Qualify | Description |
|------|--------|---------|-------------|
| Task 1: Export buttons in ResultsDashboard | DONE | PASS | Added sanitizeCell + handleDownloadCSV helpers, Download CSV + Print/Save PDF buttons with print:hidden action row |
| Task 2: netlify.toml | DONE | PASS | Created at repo root; TOML validated via tomllib |
| Task 3: render.yaml | DONE | PASS | Created at repo root; YAML validated; all required fields confirmed |

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `frontend/src/components/ResultsDashboard.tsx` | Modified | Added `sanitizeCell`, `handleDownloadCSV` helpers; replaced single reset button with three-button action row (Download CSV, Print/Save PDF, Analyse another file); `print:hidden` on container |
| `netlify.toml` | Created | Netlify build config: base=frontend, npm run build, publish=.next, Node 20; env var instructions |
| `render.yaml` | Created | Render web service: rootDir=backend, uvicorn start on $PORT, healthCheckPath=/health, secrets sync:false |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Inline CSV/print helpers (no npm packages) | Plan boundaries forbid adding packages; both can be trivially inlined | Zero new runtime dependencies; component self-contained |
| `print:hidden` on action row container only | Dashboard content (score, charts, reviews, narrative) should print as-is for MVP | Simple, targeted — one class hides all three buttons |
| `publish = ".next"` not `"out"` | App uses Next.js App Router with dynamic behaviour; static export (`output: 'export'`) would break it | Netlify auto-detects Next.js 14 and handles SSR correctly |
| `sync: false` on all secret env vars | Secrets must not be committed to repo | Render dashboard is the canonical secret store |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 0 | — |
| Scope additions | 0 | — |
| Deferred | 0 | — |

**Total impact:** None — plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

**Ready:**
- Full end-to-end pipeline: CSV upload → VADER analysis → Claude Haiku narrative → dashboard → export
- Both deployment configs committed; connecting Netlify + Render repos is the only remaining step before the app is live
- No new dependencies introduced — Phase 2 starts from a clean dependency baseline

**Concerns:**
- Render free tier cold starts (30–60s) conflict with "under 30 seconds" product promise — documented in render.yaml; upgrade plan eliminates this
- anthropic SDK in local venv may still be 0.26.0 — `pip install -U "anthropic>=0.40.0"` needed before live narrative testing
- Charts (Recharts SVGs) may appear blank in some browser print previews — acceptable for MVP, text data always present

**Blockers:**
- None — Phase 1 free-tier MVP complete

---
*Phase: 01-free-tier-mvp, Plan: 05*
*Completed: 2026-05-02*
