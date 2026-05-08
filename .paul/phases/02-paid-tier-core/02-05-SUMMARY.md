---
phase: 02-paid-tier-core
plan: 05
subsystem: api
tags: [narrative, claude-haiku, sentiment-trend, comparison, supabase, react, nextjs]

# Dependency graph
requires:
  - phase: 02-paid-tier-core
    provides: Supabase analyses table with overall_score + distribution columns (02-03)
  - phase: 02-paid-tier-core
    provides: Narrative endpoint POST /narrative/ with NarrativeRequest model (Phase 1 + 02-04 context)
provides:
  - Trend-aware narrative: Claude Haiku prompt includes prior score direction and distribution delta
  - NarrativeRequest v2: optional previous_score (bounded ±1) + previous_distribution (typed Distribution)
  - ComparisonCard: Latest vs Previous score delta + distribution delta (history page, 2+ analyses only)
  - handleAnalysisSuccess v2: snapshots prior analysis before save, passes context to narrative endpoint
affects: [Phase 3 — competitor analysis can extend comparison pattern; future plans using NarrativeRequest]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Backwards-compatible optional fields: Field(default=None) with validators — extend without breaking existing callers"
    - "Pre-save snapshot: fetch prior state before writing current to avoid reading own write as 'previous'"
    - "Silent degradation: catch block swallows Supabase fetch errors, narrative still fires without trend context"

key-files:
  created: []
  modified:
    - backend/routers/narrative.py
    - backend/services/narrative.py
    - frontend/src/app/dashboard/history/page.tsx
    - frontend/src/app/page.tsx

key-decisions:
  - "Distribution | None typed model (not dict | None): validates structure at Pydantic layer, serialises cleanly via model_dump()"
  - "pre_save snapshot: race condition avoided — previous fetched before trySaveAnalysis fires"
  - ".eq(user_id) defence-in-depth on browser Supabase query: consistent with established codebase pattern"

patterns-established:
  - "Trend threshold ±0.02: signals meaningful change vs noise; deferred to future config if tuning needed"
  - "ComparisonCard renders only when analyses.length >= 2: no empty state needed for single-analysis users"

# Metrics
duration: ~30min
started: 2026-05-08T00:00:00Z
completed: 2026-05-08T00:00:00Z
---

# Phase 2 Plan 05: Trend Narrative + History Comparison Card Summary

**Trend-aware Claude Haiku narrative and Latest vs Previous comparison card close the Phase 2 insight loop for premium users.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~30min |
| Started | 2026-05-08 |
| Completed | 2026-05-08 |
| Tasks | 3 completed |
| Files modified | 4 |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Narrative includes trend commentary when prior analysis exists | Pass | direction (improved/declined/held steady) + score delta injected into Claude prompt |
| AC-2: History page shows comparison card for users with 2+ analyses | Pass | ComparisonCard renders above table with score delta + distribution delta |
| AC-3: Narrative endpoint backwards-compatible | Pass | No previous_score → no trend reference, no error; ValidationError on out-of-range values |

## Accomplishments

- `NarrativeRequest` gains `previous_score: float | None = Field(ge=-1.0, le=1.0)` and `previous_distribution: Distribution | None` — validated at Pydantic layer, `model_dump()` passes through cleanly
- Claude Haiku prompt extended with trend block (direction + delta + distribution deltas) as optional instruction 5 — existing 4-instruction structure preserved when no prior score
- `ComparisonCard` component: 3-column grid (Previous / arrow+delta / Latest) + distribution row with colour-coded deltas; renders only for 2+ analyses
- `handleAnalysisSuccess` v2: snapshots prior analysis from Supabase *before* `trySaveAnalysis` fires (race condition prevented), passes `previous_score` + `previous_distribution` to narrative endpoint; unauthenticated and free-tier users unaffected

## Task Commits

No atomic per-task commits recorded (Phase 2 work captured in phase transition commit).

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `backend/routers/narrative.py` | Modified | Added `Field` import; `previous_score` (bounded) + `previous_distribution` (typed) optional fields |
| `backend/services/narrative.py` | Modified | Trend context block: direction classification, score delta, distribution delta; inserted into prompt |
| `frontend/src/app/dashboard/history/page.tsx` | Modified | `Analysis` interface + `distribution` in select; `ComparisonCard` component; conditional render |
| `frontend/src/app/page.tsx` | Modified | Pre-save prior analysis snapshot; `previous_score` + `previous_distribution` passed to narrative |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| `Distribution \| None` (not `dict \| None`) | Validates structure at Pydantic layer; `model_dump()` serialises to plain dict for service layer — no service changes needed | Consistent with established typed model pattern from 02-03 audit |
| Snapshot before save (pre-save pattern) | Prevents race condition where current upload is fetched as "previous" in same tick | Correct trend direction on first re-upload |
| `.eq(user_id)` on browser Supabase query | Defence-in-depth against cross-user data leak; consistent with established codebase pattern | No data isolation gap |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 0 | — |
| Scope additions | 0 | — |
| Deferred | 0 | — |

**Total impact:** None — plan executed exactly as specified.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| `→` arrow in trend_block causes Windows console cp1252 UnicodeEncodeError in test print | Not a runtime issue — Anthropic API communicates over HTTP (UTF-8); noted in summary |

## Next Phase Readiness

**Ready:**
- Trend narrative infrastructure in place — any future phase can pass prior context to Claude
- `ComparisonCard` pattern established for visual deltas — reusable for competitor comparison (Phase 3)
- Phase 2 feature set complete: auth, payments, history, KeyBERT topics, trend comparison

**Concerns:**
- Phase 2 (plans 02-02 through 02-05) not yet committed to git — transition commit captures all
- `→` Unicode in prompt works via API but will fail any Windows console logging that doesn't handle UTF-8

**Blockers:**
- None

---
*Phase: 02-paid-tier-core, Plan: 05*
*Completed: 2026-05-08*
