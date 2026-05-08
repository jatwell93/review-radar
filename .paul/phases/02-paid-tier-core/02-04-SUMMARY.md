---
phase: 02-paid-tier-core
plan: 04
subsystem: api
tags: [keybert, sentence-transformers, nlp, fastapi, react, premium]

# Dependency graph
requires:
  - phase: 02-paid-tier-core
    provides: Supabase auth + premium gate pattern (analyses.py)
provides:
  - KeyBERT topic extraction service (lazy-loaded, cached)
  - Premium-gated POST /topics/ endpoint (401/403 enforced)
  - Topics state + async fetch in page.tsx
  - "Key Themes" section in ResultsDashboard with green/red topic pills + upsell
affects: [02-05, future phases using topic data]

# Tech tracking
tech-stack:
  added: [keybert>=0.8.0, sentence-transformers>=2.7.0, all-MiniLM-L6-v2 model]
  patterns: [lazy-loaded singleton NLP service, fire-and-forget async fetch, premium gate pattern reuse]

key-files:
  created: [backend/services/keybert_service.py, backend/routers/topics.py]
  modified: [backend/main.py, backend/requirements.txt, frontend/src/types/analysis.ts, frontend/src/app/page.tsx, frontend/src/components/ResultsDashboard.tsx]

key-decisions:
  - "all-MiniLM-L6-v2 chosen: smallest semantic model (~90MB), balances quality vs Render memory"
  - "Topics are stateless per-request — not stored to DB (avoids schema changes in this plan)"
  - "Fire-and-forget fetch: topics run in parallel with narrative, never block analysis render"

patterns-established:
  - "Lazy singleton NLP service: initialise on first call, cache globally in module scope"
  - "Premium gate: analyses.py auth + subscriptions table check pattern reused verbatim"

# Metrics
duration: ~45min
started: 2026-05-08T00:00:00Z
completed: 2026-05-08T12:00:00Z
---

# Phase 2 Plan 04: KeyBERT Topic Extraction Summary

**KeyBERT-powered POST /topics/ endpoint delivers positive/negative keyword themes to premium users via tag pills in ResultsDashboard, loading asynchronously after analysis.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~45min |
| Started | 2026-05-08 |
| Completed | 2026-05-08 |
| Tasks | 3 completed |
| Files modified | 7 |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Premium users see positive/negative theme pills | Pass | Green/red pill rows render from TopicsResponse |
| AC-2: Non-premium/unauthenticated users see upsell | Pass | topicsDenied=true → upsell text rendered |
| AC-3: Topics load async — analysis not blocked | Pass | tryFetchTopics fires without await after handleAnalysisSuccess |
| AC-4: Backend rejects unauth (401) and non-premium (403) | Pass | Auth header check + subscriptions table gate enforced |

## Accomplishments

- Backend KeyBERT service with lazy-loaded singleton `all-MiniLM-L6-v2` model and score-filtered keyword extraction
- Premium-gated `/topics/` endpoint mirroring the analyses.py auth pattern exactly (401/403 consistent)
- Fire-and-forget `tryFetchTopics` in page.tsx: runs in parallel with narrative, never delays main dashboard
- ResultsDashboard "Key Themes" section: loading skeleton → green pills (loved) / red pills (complaints) / upsell / silent on network failure

## Task Commits

No atomic commits recorded (Phase 2 work not yet committed to git — Phase 1 is last tagged commit).

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `backend/services/keybert_service.py` | Created | Lazy KeyBERT singleton + `extract_topics()` with score filter |
| `backend/routers/topics.py` | Created | Premium-gated POST /topics/ endpoint |
| `backend/main.py` | Modified | Registered `topics_router` |
| `backend/requirements.txt` | Modified | Added `keybert>=0.8.0`, `sentence-transformers>=2.7.0` |
| `frontend/src/types/analysis.ts` | Modified | Added `TopicsResponse` interface |
| `frontend/src/app/page.tsx` | Modified | Topics state, `tryFetchTopics`, reset wiring, prop pass |
| `frontend/src/components/ResultsDashboard.tsx` | Modified | "Key Themes" section with pills, upsell, skeleton |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| `all-MiniLM-L6-v2` model | Smallest semantic model (~90MB) — fits Render free tier RAM budget | If Render OOMs, upgrade to Starter ($7/mo); do NOT fall back to TF-IDF |
| Topics stateless, not stored | Avoids DB schema changes in this plan; 02-05 can add comparison later | History page shows no topics for now |
| Reuse analyses.py auth pattern verbatim | Only two usages — premature to abstract | Consistent 401/403 behaviour across premium endpoints |

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
- Topics endpoint live and returning structured `positive_topics` / `negative_topics`
- Premium gate pattern established and reusable for any future premium feature
- ResultsDashboard extended cleanly; narrative, charts, action row untouched

**Concerns:**
- Render free tier (512MB RAM) may OOM when `sentence-transformers` loads PyTorch (~300MB). Monitor after deploy; upgrade to Render Starter if needed.
- Phase 2 work (plans 02-02 through 02-04) not yet committed to git — transition commit will capture all.

**Blockers:**
- None

---
*Phase: 02-paid-tier-core, Plan: 04*
*Completed: 2026-05-08*
