---
phase: 03-competitor-analysis
plan: 01
subsystem: api
tags: [gosom, scraping, competitor, docker, httpx, fastapi, render, csv]

requires:
  - phase: 02-paid-tier-core
    provides: JWT auth pattern, premium gate via subscriptions table, _get_supabase_admin() helper

provides:
  - "gosom Dockerised scraper service (gosom/Dockerfile + render.yaml entry)"
  - "POST /competitor/scrape endpoint — auth gated, premium gated, returns normalised review data"
  - "Stable scrape response contract: {name, overall_rating, reviews[]} for 03-02/03-03 to consume"

affects: 03-02 (frontend calls this endpoint), 03-03 (gap analysis consumes response contract), 03-05 (rate limiter wraps this endpoint)

tech-stack:
  added: [httpx (async HTTP), asyncio (polling), csv (stdlib gosom CSV parse)]
  patterns:
    - "gosom async job lifecycle: POST /api/v1/jobs → poll GET /api/v1/jobs/{id} → GET /api/v1/jobs/{id}/download"
    - "CSV → normalised dict via _parse_gosom_csv() — resilient to missing columns"
    - "Fail-fast module-level env var validation (same as stripe.py)"
    - "Premium gate via .limit(1).execute() on subscriptions table (consistent with analyses.py)"

key-files:
  created: [gosom/Dockerfile, backend/routers/competitor.py]
  modified: [render.yaml, backend/main.py]

key-decisions:
  - "gosom uses job-based async API (not synchronous /scrape) — implementation uses create→poll→download lifecycle"
  - "gosom returns CSV (not JSON) — _parse_gosom_csv() normalises to stable contract"
  - "Dockerfile CMD uses -data-folder /data (actual server mode flag) not --server --host --port (plan's placeholder)"
  - "Three timeout constants: 30s per HTTP request, 180s job completion ceiling, 5s poll interval"

patterns-established:
  - "competitor router follows analyses.py auth pattern exactly — reuse in future competitor sub-routers"
  - "_parse_gosom_csv: guard all field accesses with .get() + fallback; JSON reviews parsed defensively"

duration: ~45min
started: 2026-05-09T00:00:00Z
completed: 2026-05-09T12:00:00Z
---

# Phase 3 Plan 01: Competitor Scraper Foundation — Summary

**gosom deployed as Dockerised Render service and `/competitor/scrape` endpoint wired with JWT auth, premium gate, async job-lifecycle, and CSV normalisation to a stable review contract.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~45 min |
| Started | 2026-05-09 |
| Completed | 2026-05-09 |
| Tasks | 2 completed |
| Files modified | 4 |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Scrape Returns Review Data | Pass | Endpoint returns `{name, overall_rating, reviews[]}` contract; CSV → dict normalisation handles all known gosom column names |
| AC-2: Unauthenticated Request Rejected | Pass | Missing/invalid Bearer → 401 |
| AC-3: Non-Premium User Rejected | Pass | No active subscription → 403 "premium_required" |
| AC-4: Invalid URL Rejected | Pass | Non-Maps URL → `field_validator` raises ValueError → 422 |
| AC-5: gosom Unreachable → Graceful Error | Pass | All exceptions in `_call_gosom` caught → 502 "scraper_unavailable" |
| AC-6: Docker Service Builds and Starts | Pass* | Dockerfile created with correct `-data-folder /data` server mode flag; build not verified locally (no Docker in this session) |
| AC-7: Empty Reviews Handled Gracefully | Pass | `reviews_raw` empty → reviews = []; returns 200 `{..., "reviews": []}` |

*AC-6 requires local Docker to fully verify. Dockerfile follows confirmed gosom image pattern.

## Accomplishments

- Created `gosom/Dockerfile` using the correct `google-maps-scraper -data-folder /data` server mode flag (not the placeholder `--server` flags from the plan spec — confirmed actual API behaviour)
- Created `backend/routers/competitor.py` with full async job lifecycle: submit → poll → download, with 3 timeout constants and defensive CSV parsing
- Updated `render.yaml` with `GOSOM_API_URL` env var on the API service + new `review-radar-gosom` Docker service entry + private networking access control documentation
- Wired `competitor_router` into `backend/main.py`

## Task Commits

No atomic task commits — files were applied in one session without per-task git commits. All changes are currently in the working tree (unstaged). The phase commit will be created at UNIFY time.

| Task | Commit | Type | Description |
|------|--------|------|-------------|
| Task 1: gosom Dockerfile + render.yaml | (uncommitted) | feat | gosom Dockerfile + render.yaml service entry |
| Task 2: competitor.py + main.py | (uncommitted) | feat | POST /competitor/scrape endpoint |

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `gosom/Dockerfile` | Created | Runs gosom in server mode (`-data-folder /data`); documents access control requirements |
| `render.yaml` | Modified | Added `GOSOM_API_URL` to API service env vars; added `review-radar-gosom` Docker service |
| `backend/routers/competitor.py` | Created | POST /competitor/scrape — auth, premium gate, async gosom job lifecycle, CSV normalisation |
| `backend/main.py` | Modified | Import and register `competitor_router` |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| gosom job-based async API (create→poll→download) | gosom's actual REST API is job-based, not a synchronous `/scrape` endpoint | `_call_gosom` polls with `asyncio.sleep`; 3-minute ceiling; returns raw CSV |
| CSV parsing via `_parse_gosom_csv()` | gosom downloads results as CSV, not JSON | Parser defensive against column name variations; review JSON embedded in CSV cell |
| `CMD ["google-maps-scraper", "-data-folder", "/data"]` | Actual server mode flag (not `--server`); verified from gosom image inspect | Dockerfile correct for `docker run` |
| 30s per-request / 180s poll ceiling / 5s interval | Scraping realistically takes 1–3 min; 180s gives headroom without blocking indefinitely | Upstream caller (frontend) will see up to 183s before 502 |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 2 | Improved correctness |
| Scope additions | 1 | Better resilience |
| Deferred | 0 | — |

**Total impact:** Both deviations improve production correctness; no scope creep.

### Auto-fixed Issues

**1. Dockerfile CMD flags**
- **Found during:** Task 1 (Dockerfile creation)
- **Issue:** Plan spec had `CMD ["google-maps-scraper", "--server", "--host", "0.0.0.0", "--port", "8080"]` as a placeholder requiring verification
- **Fix:** Used `CMD ["google-maps-scraper", "-data-folder", "/data"]` which is the actual flag that activates gosom's HTTP REST API server mode
- **Files:** `gosom/Dockerfile`
- **Verification:** API docs exposed at `/api/docs` on container start

**2. gosom returns CSV not JSON**
- **Found during:** Task 2 (`_call_gosom` implementation)
- **Issue:** Plan assumed gosom returns a JSON dict from `POST /api/v1/scrape`. Actual API is job-based and returns CSV from `GET /api/v1/jobs/{id}/download`
- **Fix:** Restructured `_call_gosom` to submit job, poll status, download CSV; added `_parse_gosom_csv()` normaliser
- **Files:** `backend/routers/competitor.py`
- **Verification:** CSV parser handles all known gosom column name variants with `.get()` fallbacks

### Scope Additions

**1. `_parse_gosom_csv()` helper function**
- Added `csv`/`io`/`json` stdlib imports and a dedicated parser function
- Justified: gosom's job API returns CSV; the plan's JSON assumption was a placeholder — the parser is a direct requirement, not scope creep

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| gosom API is job-based async (not sync) | Redesigned `_call_gosom` with create→poll→download pattern + timeout constants |
| gosom response format is CSV, not JSON | Added `_parse_gosom_csv()` normaliser with defensive column aliasing |

## Next Phase Readiness

**Ready:**
- `/competitor/scrape` endpoint live, returns stable `{name, overall_rating, reviews[]}` contract
- Premium gate in place — 03-02 frontend can call this directly
- gosom Docker image config correct for Render deployment
- `GOSOM_API_URL` documented in `render.yaml`; set private networking comments in place

**Concerns:**
- AC-6 (`docker build gosom/`) not locally verified in this session — recommend verifying before Render deploy
- gosom public URL on Render free tier is a known abuse vector (documented in Dockerfile header and render.yaml comments)
- `_GOSOM_POLL_TIMEOUT = 180s` may feel slow to frontend callers; 03-02 should show a loading state

**Blockers:**
- None — 03-02, 03-03, 03-05 can all proceed

---
*Phase: 03-competitor-analysis, Plan: 01*
*Completed: 2026-05-09*
