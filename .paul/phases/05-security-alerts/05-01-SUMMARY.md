---
phase: 05-security-alerts
plan: 01
completed: 2026-11-23
---

# 05-01 Summary: URL substring sanitization alerts

## What was built
- `backend/services/url_validation.py`: `is_google_maps_url` (stdlib `urlparse`, https only, no userinfo, exact host `maps.google.com` or `www.google.com` with path `/maps` or `/maps/...`).
- `routers/automation.py` and `routers/competitor.py` validators now call the helper (same error message, `max_length=2000` kept).
- `CompetitorAnalyser.tsx`: module-level `isGoogleMapsUrl` using `new URL()`, used in `handleSubmit`.
- `backend/tests/test_url_validation.py`: parametrized valid/spoofed cases for the helper, plus both request models (router imports with stubbed supabase/scraper/narrative/keybert/sentiment modules and env vars).

## Acceptance criteria
- AC-1 valid URLs accepted: pass (tests).
- AC-2 spoofed hosts rejected: pass in Python (tests). Frontend mirrors the same rules; no frontend test framework exists, so it is verified by type check only.
- AC-3 gates: `compileall` and `pytest backend -q` (17 passed) exit 0. `npm --prefix frontend exec tsc -- --noEmit` run from the repo root prints tsc help (no tsconfig in cwd) and exits 1; `-p frontend` added, it exits 0.

## Deviations
- None to the plan. Gate command note above is for the owner.

## Deferred
- The tsc gate in `factory.config.yml` needs `-p frontend` (or a different cwd) to actually type-check. `factory.config.yml` is protected, so the owner must change it.

## Files
- created: `backend/services/url_validation.py`, `backend/tests/test_url_validation.py`
- modified: `backend/routers/automation.py`, `backend/routers/competitor.py`, `frontend/src/components/CompetitorAnalyser.tsx`
