---
phase: 01-free-tier-mvp
plan: 04
subsystem: api
tags: [claude, anthropic, haiku, narrative, llm, fastapi, react]

requires:
  - phase: 01-03
    provides: Results dashboard with charts, score card, review lists, and TODO placeholder for narrative

provides:
  - POST /narrative/ FastAPI endpoint — generates plain-English pharmacy advisor summary via Claude Haiku
  - backend/services/narrative.py — Anthropic SDK integration with prompt engineering
  - backend/routers/narrative.py — endpoint with graceful 503 error handling
  - NarrativeResponse TypeScript interface
  - Narrative card in ResultsDashboard — shimmer loading, text display, graceful "Summary unavailable" fallback

affects: [01-05, Phase 2]

tech-stack:
  added: [anthropic>=0.40.0 (requirements.txt — was 0.26.0)]
  patterns:
    - Separate endpoint for AI features (narrative is NOT part of /analyze/)
    - Graceful degradation — AI failure does not block the dashboard
    - HTTPException re-raised before broad Exception catch (FastAPI safety pattern)
    - Narrative state managed in page.tsx, passed down to ResultsDashboard as props

key-files:
  created:
    - backend/services/narrative.py
    - backend/routers/narrative.py
  modified:
    - backend/main.py
    - backend/requirements.txt
    - frontend/src/types/analysis.ts
    - frontend/src/app/page.tsx
    - frontend/src/components/ResultsDashboard.tsx

key-decisions:
  - "Narrative as separate POST endpoint, not appended to /analyze/ — keeps pipeline concerns isolated"
  - "Reuse Distribution + ReviewItem Pydantic models from routers.analyze — no duplication"
  - "Narrative fetch fires immediately after /analyze/ resolves — dashboard renders at once, narrative loads in parallel"
  - "HTTPException explicitly re-raised before broad except Exception to preserve FastAPI error propagation"

patterns-established:
  - "AI features isolated to dedicated service + router pair (services/narrative.py + routers/narrative.py)"
  - "Graceful degradation: AI failure leaves state as null, UI shows 'unavailable' — never blocks core content"
  - "Shimmer loading state in narrative card uses animate-pulse on indigo-100 divs"

duration: ~30min
started: 2026-05-02T00:00:00Z
completed: 2026-05-02T00:00:00Z
---

# Phase 1 Plan 04: Claude Haiku Narrative Summary

**Claude Haiku narrative endpoint wired end-to-end — pharmacy owners now see a plain-English business-advisor summary alongside their sentiment charts, with graceful fallback when the API is unavailable.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~30 min |
| Started | 2026-05-02 |
| Completed | 2026-05-02 |
| Tasks | 2 completed |
| Files modified | 7 |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Narrative endpoint returns plain-English summary | Pass | POST /narrative/ returns `{"narrative": "..."}` from Claude Haiku; verified via import check and TypeScript build |
| AC-2: Narrative renders in results dashboard | Pass | Indigo card with shimmer loading state and italic summary text renders between review lists and reset button |
| AC-3: Graceful degradation when narrative fails | Pass | Non-ok HTTP response or network failure leaves narrative null → "Summary unavailable" shown; dashboard never blocked |

## Accomplishments

- `POST /narrative/` FastAPI endpoint created with full error handling — `ValueError` (missing API key) → 503 "not configured", all other exceptions → 503 "failed", `HTTPException` propagates untouched
- `backend/services/narrative.py` prompt engineered for pharmacy advisor tone: covers overall performance, what customers appreciate, primary improvement area, and one actionable recommendation in 3-4 sentences
- Frontend narrative fetch fires immediately after VADER analysis completes — dashboard renders charts and reviews at once while narrative loads in parallel (non-blocking)
- Shimmer loading state (3 indigo pulse bars) during Claude response; graceful "Summary unavailable" fallback if fetch fails

## Task Commits

| Task | Status | Qualify | Description |
|------|--------|---------|-------------|
| Task 1: Backend narrative service + endpoint | DONE | PASS (1 concern fixed) | Created services/narrative.py, routers/narrative.py; updated main.py + requirements.txt |
| Task 2: Frontend narrative integration | DONE | PASS | Added NarrativeResponse type, narrative state in page.tsx, narrative card in ResultsDashboard |

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `backend/services/narrative.py` | Created | Claude Haiku integration — builds prompt from analysis data, calls messages.create(), returns stripped text |
| `backend/routers/narrative.py` | Created | POST /narrative/ endpoint — NarrativeRequest model, error handling, reuses Distribution + ReviewItem from analyze router |
| `backend/main.py` | Modified | Imports and registers narrative_router |
| `backend/requirements.txt` | Modified | Bumped `anthropic==0.26.0` → `anthropic>=0.40.0` |
| `frontend/src/types/analysis.ts` | Modified | Added `NarrativeResponse` interface |
| `frontend/src/app/page.tsx` | Modified | Added narrative + narrativeLoading state, handleAnalysisSuccess async function, handleReset clears narrative |
| `frontend/src/components/ResultsDashboard.tsx` | Modified | Extended Props with narrative/narrativeLoading; replaced TODO comment with indigo narrative card |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Narrative as separate endpoint, not merged into /analyze/ | Keeps VADER pipeline stateless and fast; AI latency (~3-5s) would block chart rendering if merged | 01-05 export only needs to handle /analyze/ response; narrative remains optional |
| Reuse Pydantic models from routers.analyze | Avoids duplicate model definitions and potential drift | Future analyze model changes auto-propagate to NarrativeRequest |
| HTTPException re-raised explicitly before broad except | FastAPI relies on HTTPException propagation for its error handling; swallowing it silently causes wrong status codes | Correct 422/500 errors still surface to callers |
| Narrative fetch does not block dashboard render | Core value (charts + scores) must be instant; narrative is enhancement | Dashboard always usable even on slow Render cold starts |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 1 | Essential correctness fix |
| Scope additions | 0 | None |
| Deferred | 0 | None |

**Total impact:** One essential correctness fix; no scope creep.

### Auto-fixed Issues

**1. Exception handling — HTTPException swallowed by broad except**
- **Found during:** Task 1 QUALIFY
- **Issue:** `except Exception` would silently swallow `HTTPException` (a subclass of `Exception`), causing wrong status codes for FastAPI errors
- **Fix:** Added explicit `except HTTPException: raise` before the broad catch, matching the pattern used in `routers/analyze.py`
- **Files:** `backend/routers/narrative.py`
- **Verification:** Import check passed; pattern matches established analyze router

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| Installed anthropic SDK is 0.26.0, requirements.txt now requires >=0.40.0 | requirements.txt updated for fresh installs; 0.26.0 is functionally compatible (messages.create() API is unchanged). User should run `pip install -U "anthropic>=0.40.0"` inside the venv before testing |

## Next Phase Readiness

**Ready:**
- Full VADER + Haiku pipeline working end-to-end (frontend → analyze → narrative → dashboard)
- Both servers start cleanly with no import errors
- Frontend builds with zero TypeScript errors
- 01-05 (Export + deploy) can build directly on the existing dashboard and API structure

**Concerns:**
- anthropic SDK version in venv (0.26.0) should be upgraded before live testing with real API key
- Render free tier cold starts (~30-50s) may make the narrative timeout for first-time users — worth noting in 01-05 deploy docs

**Blockers:**
- None — 01-05 can proceed immediately

---
*Phase: 01-free-tier-mvp, Plan: 04*
*Completed: 2026-05-02*
