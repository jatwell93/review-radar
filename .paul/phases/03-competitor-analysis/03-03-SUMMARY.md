---
phase: 03-competitor-analysis
plan: 03
subsystem: backend + frontend
tags: [fastapi, vader, keybert, react, supabase, gap-analysis]

requires:
  - phase: 03-01
    provides: /competitor/scrape POST endpoint; auth + premium gate pattern; gosom CSV normalisation
  - phase: 03-02
    provides: CompetitorAnalyser component structure; ScrapeResult type; handleSubmit pattern

provides:
  - POST /competitor/gap endpoint: VADER + KeyBERT on competitor reviews, fetches user's own latest analysis
  - CompetitorAnalyser updated: auto-calls gap after scrape; renders side-by-side Gap Analysis panel
  - GapPanel component: delta computation, colour-coded "ahead/behind/tied" row
  - DistributionBar component: positive/neutral/negative % breakdown

affects: ["03-04 (Outscraper fallback uses same scrape→gap flow)", "03-05 (rate limiting applies to /gap endpoint too)"]

tech-stack:
  added: []
  patterns:
    - "void runGapAnalysis(data, token) — fire-and-forget after setResult; loading managed independently"
    - "GapPanel local component — delta variables precomputed before JSX return (no IIFE)"
    - "30s AbortController for gap fetch (separate from scrape's 240s controller)"
    - "Soft error: gap failure shows amber message, raw scrape results stay visible"

key-files:
  modified:
    - backend/routers/competitor.py
    - frontend/src/components/CompetitorAnalyser.tsx
  also-changed:
    - backend/services/narrative.py  (switched from anthropic SDK to openai SDK + OpenRouter)
    - backend/requirements.txt       (anthropic → openai>=1.0.0)
    - render.yaml                    (ANTHROPIC_API_KEY → OPENROUTER_API_KEY)

key-decisions:
  - "Gap endpoint takes scrape payload as input — avoids re-running the 3-min gosom scrape"
  - "Competitor gap results not stored in DB — stateless, returned in response only"
  - "own: null path shows 'Upload your reviews to compare' — no 404, graceful degradation"
  - "OpenRouter substituted for Anthropic SDK (user preference, same Claude Haiku model via anthropic/claude-haiku-4-5)"
  - "GapReview.text max_length=2000, rating ge=0 le=5; GapRequest.name max_length=500, overall_rating ge=0 le=5 (audit-required)"

patterns-established:
  - "Gap analysis pattern: POST endpoint accepts scrape payload → runs ML → fetches own data → returns {competitor, own}"
  - "Frontend fire-and-forget gap: void runGapAnalysis after setResult, independent loading state"
  - "Local helper components (DistributionBar, GapPanel) defined before main export — delta precomputed, not in JSX"

verification:
  backend: "POST /competitor/gap returned vader_score=0.1937 on 3 test reviews; own data populated from Supabase"
  frontend: "TypeScript compiled without errors (npx tsc --noEmit exits 0)"
  checkpoint: "Human verified — gap endpoint returns correct {competitor, own} shape; approved"

deviations:
  - "OpenRouter swap (narrative.py): not in 03-03 scope but done inline at user request — no plan change needed"
  - "gosom not available locally (Docker Desktop not running) — gap endpoint tested directly via PowerShell Invoke-RestMethod"

duration: ~45min
started: 2026-05-10T03:30:00Z
completed: 2026-05-10T04:15:00Z
---

# Phase 3 Plan 03: Gap Analysis Summary

**Gap analysis shipped: POST /competitor/gap runs VADER + KeyBERT on competitor reviews and returns side-by-side sentiment comparison with the user's own latest analysis.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~45 min |
| Started | 2026-05-10 |
| Completed | 2026-05-10 |
| Tasks | 2 auto + 1 checkpoint |
| Files modified | 2 (+ 3 incidental) |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Gap auto-runs after scrape | Pass | `void runGapAnalysis(data, token)` called after `setResult(data)` |
| AC-2: Side-by-side VADER comparison | Pass | GapPanel renders two cards; delta row with ±0.02 threshold + colour coding |
| AC-3: Distribution comparison | Pass | DistributionBar in both cards |
| AC-4: Competitor topic themes | Pass | KeyBERT topics rendered as badges; empty list = no crash |
| AC-5: Own analysis not available | Pass | `own: null` → "Upload your reviews to compare"; no delta row |
| AC-6: Auth + premium gated | Pass | 401 on missing Bearer; 403 on no active subscription |
| AC-7: Empty reviews — no crash | Pass | `texts = []` → vader_score=0.0, dist all zeros, topics=[] |
| AC-8: Gap API failure is soft error | Pass | Amber message; scrape results remain; no spinner after failure |

## Files Modified

| File | Change | Purpose |
|------|--------|---------|
| `backend/routers/competitor.py` | Modified | Added GapReview, GapRequest models + POST /competitor/gap route |
| `frontend/src/components/CompetitorAnalyser.tsx` | Modified | Added gap state, runGapAnalysis, GapPanel, DistributionBar |
| `backend/services/narrative.py` | Modified | Switched anthropic SDK → openai SDK pointing at OpenRouter |
| `backend/requirements.txt` | Modified | `anthropic>=0.40.0` → `openai>=1.0.0` |
| `render.yaml` | Modified | `ANTHROPIC_API_KEY` → `OPENROUTER_API_KEY` |

## Decisions Made

- **OpenRouter swap**: User already had OpenRouter configured; switched narrative service from Anthropic SDK to `openai` SDK with `base_url="https://openrouter.ai/api/v1"`. Model stays `anthropic/claude-haiku-4-5`.
- **Gap input = scrape output**: Endpoint accepts the scrape payload directly — no re-scraping, no gosom call in the gap route.
- **Stateless gap results**: Not stored in DB; topics remain ephemeral per plan decision.

## Issues Encountered

- `keybert` not installed in local venv (heavy ML dep, deployment-only) — syntax verified via `ast.parse`; runtime verified on Render.
- gosom Docker not running locally — gap endpoint tested directly via `Invoke-RestMethod` with mock scrape data.
- OpenRouter swap done inline (not scoped to 03-03) at user request — clean, no side effects.

## Next Phase Readiness

**Ready:**
- `/competitor/gap` endpoint live and returning `{competitor, own}` shape
- CompetitorAnalyser renders full gap panel: scores, distributions, topics, delta
- Soft error path confirmed: gap failure does not break scrape results
- OpenRouter wired for narrative — `OPENROUTER_API_KEY` required in `.env` and Render dashboard

**Concerns:**
- Render free tier: KeyBERT model load (~400MB) may trigger OOM on first gap request — monitor after deploy

**Blockers:**
- None

---
*Phase: 03-competitor-analysis, Plan: 03*
*Completed: 2026-05-10*
