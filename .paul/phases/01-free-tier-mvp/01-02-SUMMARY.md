---
phase: 01-free-tier-mvp
plan: 02
subsystem: api
tags: [fastapi, vader, sentiment, csv, pydantic]

requires:
  - phase: 01-01
    provides: FastAPI scaffold with CORS, venv, and uvicorn configured

provides:
  - POST /analyze endpoint accepting multipart CSV upload
  - VADER sentiment pipeline with aggregation (overall score, distribution, timeline, top/bottom reviews)
  - Tolerant CSV parser with BOM handling and column auto-detection

affects: [01-03, 01-04]

tech-stack:
  added: [python-dateutil>=2.8]
  patterns:
    - Module-level VADER analyzer instantiation (avoid per-request init)
    - utf-8-sig BOM decoding first, latin-1 fallback
    - Broad outer exception handler wrapping endpoint to prevent traceback leakage

key-files:
  created:
    - backend/routers/analyze.py
    - backend/services/csv_parser.py
    - backend/services/sentiment.py
    - backend/routers/__init__.py
    - backend/services/__init__.py
  modified:
    - backend/main.py
    - backend/requirements.txt

key-decisions:
  - "python-dateutil pinned explicitly — not relied on as transitive dep to avoid startup crash if httpx/anthropic drop it"
  - "Empty list guard in pipeline even though CSV parser already raises — defensive belt-and-suspenders"
  - "top/bottom reviews can overlap when total_reviews < 10 — intentional, documented in code for 01-03 frontend"

patterns-established:
  - "Router pattern: routers/ package with APIRouter, prefix set in router file, registered via include_router in main.py"
  - "Service pattern: services/ package with pure functions, no FastAPI dependencies"
  - "Pydantic models co-located in router file (not a separate models.py) for single-plan endpoints"

duration: ~30min
started: 2026-05-02T00:00:00Z
completed: 2026-05-02T00:00:00Z
---

# Phase 1 Plan 02: CSV Ingestion + VADER Pipeline Summary

**POST /analyze endpoint live — accepts CSV upload, runs VADER scoring on each review, returns aggregated JSON with overall score, distribution, timeline, and top/bottom 5 reviews.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~30 min |
| Started | 2026-05-02 |
| Completed | 2026-05-02 |
| Tasks | 2 of 2 completed |
| Files created | 5 |
| Files modified | 2 |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Valid CSV returns structured analysis | Pass | 200 with all 6 fields; distribution sum == total_reviews confirmed |
| AC-2: Invalid upload returns 422 | Pass | .txt → 422, empty file → 422, no text column → 422 |
| AC-3: Tolerant column detection | Pass | Priority list + contains fallback; BOM-prefixed CSV → 200 |

## Accomplishments

- VADER pipeline instantiated at module level (lexicon loaded once, not per request)
- CSV parser handles Windows BOM exports via utf-8-sig decode with latin-1 fallback
- Timeline groups by YYYY-MM using dateutil with graceful skip of unparseable dates
- Broad `except Exception` wrapper prevents internal tracebacks leaking to clients

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `backend/routers/__init__.py` | Created (empty) | Router package marker |
| `backend/routers/analyze.py` | Created (68 lines) | POST /analyze endpoint, Pydantic models |
| `backend/services/__init__.py` | Created (empty) | Services package marker |
| `backend/services/csv_parser.py` | Created (65 lines) | BOM-tolerant CSV ingestion + column detection |
| `backend/services/sentiment.py` | Created (92 lines) | VADER scoring, classification, aggregation pipeline |
| `backend/main.py` | Modified (24→27 lines) | Added router import + include_router |
| `backend/requirements.txt` | Modified (+1 line) | Added python-dateutil>=2.8 |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| dateutil imported inside try/except in sentiment.py | Graceful degradation if dep missing; returns `timeline: []` instead of crashing | 01-03 must handle empty timeline array |
| top/bottom overlap allowed for small datasets | Correct behaviour when fewer than 10 reviews — no artificial deduplication | 01-03 frontend must handle duplicate review items |
| Pydantic models in analyze.py (not models.py) | Single endpoint, no sharing needed; avoids premature abstraction | If 01-04 reuses ReviewItem, extract to shared models.py then |

## Deviations from Plan

None — plan executed exactly as specified.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| Initial server query returned only /health | Old uvicorn process from prior session; fresh process confirmed /analyze registered correctly |

## Next Phase Readiness

**Ready:**
- `AnalysisResponse` shape is the contract for 01-03 (dashboard UI) and 01-04 (Claude narrative)
- All 6 response fields typed and validated by Pydantic
- `timeline` may be `[]` if CSV has no date column — 01-03 must render gracefully
- `top_reviews` / `bottom_reviews` may contain duplicates when `total_reviews < 10` — 01-03 should handle

**Concerns:**
- No rate limiting on /analyze — acceptable for free tier MVP (stateless, no auth)
- 10 MB file size cap is enforced in code but not tested with large files

**Blockers:**
- None

---
*Phase: 01-free-tier-mvp, Plan: 02*
*Completed: 2026-05-02*
