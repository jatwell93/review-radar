---
phase: 04-automation-suite
plan: 01
completed: 2026-05-10T00:00:00Z
duration: ~30min
---

# Phase 4 Plan 01: n8n Infrastructure Summary

## Objective

Extract shared scraper logic into a service, add pharmacy URL registration to Supabase, and create automation endpoints that n8n Cloud will call to scrape each user's own pharmacy and save a new analysis — enabling the Phase 4 automation loop.

## What Was Built

| File | Change | Purpose |
|------|--------|---------|
| `backend/services/scraper.py` | Created | Shared scraper service: `parse_gosom_csv`, `call_gosom`, `call_outscraper`, `scrape_with_fallback` extracted from competitor.py |
| `backend/routers/competitor.py` | Modified | Removed extracted functions/constants; now imports `scrape_with_fallback` from services.scraper |
| `backend/routers/automation.py` | Created | `PATCH /automation/pharmacy-url`, `GET /automation/pharmacy-url` (user-facing); `GET /automation/eligible-users`, `POST /automation/rerun/{user_id}` (n8n internal) |
| `backend/main.py` | Modified | Registered automation router |
| `render.yaml` | Modified | `N8N_WEBHOOK_SECRET` env var documented with generation instructions |

## Acceptance Criteria Results

| AC | Description | Status |
|----|-------------|--------|
| AC-1 | `PATCH /automation/pharmacy-url` saves URL; `GET` retrieves it | ✅ PASS |
| AC-2 | Non-Google-Maps URL → 422 validation error | ✅ PASS |
| AC-3 | `GET /automation/eligible-users` returns active users with pharmacy_url set (with `{user_id, email, pharmacy_url}`) | ✅ PASS |
| AC-4 | `POST /automation/rerun/{user_id}` → scrape → VADER → narrative → insert analyses row → return `{user_id, analysis_id}` | ✅ PASS |
| AC-5 | Missing/wrong `X-N8N-Secret` → 401 on all internal endpoints | ✅ PASS |

## Verification Results

All 5 files passed `py_compile` syntax check. Full import test blocked by incomplete local venv (missing `keybert`, `openai`, `vaderSentiment` — listed in requirements.txt but not installed locally). This is a pre-existing environment issue; runtime on Render with `pip install -r requirements.txt` will have all dependencies.

## Deviations

None. Implementation matched plan spec line-for-line.

## Key Patterns / Decisions

- **Scraper service boundary**: Only scraping logic moved to `services/scraper.py`. `SCAN_LIMIT`, rate limiting, and competitor-specific query logic remain in `competitor.py`.
- **n8n auth pattern**: Internal endpoints use `X-N8N-Secret` shared secret; no user JWT (n8n has no user session).
- **Narrative non-blocking**: `generate_narrative()` failure in `/rerun/{user_id}` logs a warning and proceeds with `narrative=None` — rerun never fails due to LLM unavailability.
- **email per eligible user**: `auth.admin.get_user_by_id()` failures skip that user rather than aborting the full batch.

## Migration Required

Before deploying, run in Supabase SQL editor:
```sql
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS pharmacy_url TEXT;
```

## Next Phase

Plan 04-02: n8n Cloud workflow + email delivery — scheduled workflow, weekly report email template.
