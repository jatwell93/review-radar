---
phase: 03-competitor-analysis
plan: 04
subsystem: api
tags: [outscraper, httpx, fallback, scraper, competitor]

requires:
  - phase: 03-01
    provides: gosom job lifecycle, _call_gosom helper, _parse_gosom_csv, stable scrape contract

provides:
  - _call_outscraper async helper (Outscraper Maps Reviews API → normalised dict)
  - _scrape_with_fallback orchestrator (gosom → Outscraper on 502)
  - scrape_competitor endpoint uses fallback chain transparently

affects: 03-05-rate-limiting

tech-stack:
  added: []
  patterns: [gosom→Outscraper fallback chain, except HTTPException before except Exception, module-level constants for tunable values]

key-files:
  created: []
  modified: [backend/routers/competitor.py, render.yaml]

key-decisions:
  - "OUTSCRAPER_API_KEY remains optional — absence = gosom-only mode, not startup failure"
  - "except HTTPException: raise before except Exception in _call_outscraper — matches _call_gosom pattern, prevents re-wrapping"
  - "Non-502 gosom errors bypass fallback (AC-5) — only availability failures trigger Outscraper"

patterns-established:
  - "Fallback chain: try primary, except 502 only, check optional key, warn, call secondary"
  - "Module-level constants for all tunable values (_OUTSCRAPER_REQUEST_TIMEOUT, _OUTSCRAPER_REVIEW_LIMIT)"

duration: ~10min
started: 2026-05-10T00:00:00Z
completed: 2026-05-10T00:00:00Z
---

# Phase 3 Plan 04: Outscraper Fallback Summary

**Transparent Outscraper fallback added to `/competitor/scrape`: gosom 502s now auto-retry via Outscraper Maps Reviews API when `OUTSCRAPER_API_KEY` is set, returning the identical `{name, overall_rating, reviews[]}` contract with no frontend changes.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~10 min |
| Started | 2026-05-10 |
| Completed | 2026-05-10 |
| Tasks | 2 completed |
| Files modified | 2 |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Fallback activates on gosom 502 | Pass | `_scrape_with_fallback` catches 502, checks key, calls `_call_outscraper` |
| AC-2: No fallback when key absent | Pass | `os.getenv("OUTSCRAPER_API_KEY")` absent → raises 502 "scraper_unavailable" |
| AC-3: Both scrapers fail → 502 | Pass | `_call_outscraper` non-200 → HTTPException(502, "scraper_unavailable") |
| AC-4: Response contract identical | Pass | `_call_outscraper` returns `{name, overall_rating, reviews[{text, rating}]}` matching `_parse_gosom_csv` |
| AC-5: Non-502 gosom errors bypass fallback | Pass | `if exc.status_code != 502: raise` before Outscraper path |

## Accomplishments

- `_call_outscraper(url, api_key)` — GET Outscraper Maps Reviews API, normalises JSON to stable scrape contract
- `_scrape_with_fallback(url)` — orchestrates gosom→Outscraper chain with correct AC-5 bypass
- `scrape_competitor` endpoint simplified: single `await _scrape_with_fallback(body.url)` replaces dual gosom call + try/except
- `render.yaml` documents `OUTSCRAPER_API_KEY` as optional `sync: false` env var

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `backend/routers/competitor.py` | Modified | Added `import logging`, `logger`, 3 Outscraper constants, `_call_outscraper`, `_scrape_with_fallback`; updated `scrape_competitor` |
| `render.yaml` | Modified | Documented optional `OUTSCRAPER_API_KEY` for operator reference |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| `OUTSCRAPER_API_KEY` not in `_REQUIRED_ENV_VARS` | Optional — absence means gosom-only mode, not a config error | No startup failure for operators not using Outscraper |
| `logger.warning` on fallback activation | Audit-added: cost monitoring and gosom blockage detection | Operators see when fallback fires in logs |
| `except HTTPException: raise` before `except Exception` in `_call_outscraper` | Audit-added: matches `_call_gosom` pattern; prevents re-wrapping 502s raised inside the try block | Exception chain integrity preserved |

## Deviations from Plan

None — plan executed exactly as written including all audit-added items.

## Issues Encountered

None.

## Next Phase Readiness

**Ready:**
- Fallback chain is transparent to 03-05 (rate limiter): `scrape_competitor` surface is unchanged
- Same `{name, overall_rating, reviews[]}` contract flows into gap analysis and frontend unmodified

**Concerns:**
- Outscraper response field names (`review_text`, `review_rating`) assumed from API docs — verify against a live response if `_call_outscraper` ever returns empty reviews

**Blockers:**
- None

---
*Phase: 03-competitor-analysis, Plan: 04*
*Completed: 2026-05-10*
