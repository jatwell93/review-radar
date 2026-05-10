---
phase: 03-competitor-analysis
plan: 05
subsystem: api
tags: [rate-limiting, supabase, postgres, rls, fastapi, react, nextjs]

requires:
  - phase: 03-02-competitor-flow
    provides: /competitor/scrape endpoint and CompetitorAnalyser component this plan extends

provides:
  - competitor_scans Supabase table with RLS (per-user monthly scan tracking)
  - Rate limit enforcement on /competitor/scrape (429 + Retry-After when count >= 10)
  - GET /competitor/usage endpoint returning {count, limit, month}
  - Usage badge in CompetitorAnalyser showing scans used / limit
  - Disabled form state when monthly limit reached
affects: Phase 4 (automation), any future competitor feature work

tech-stack:
  added: []
  patterns:
    - UTC month key (YYYY-MM) for calendar-month rate limiting
    - Upsert on_conflict for idempotent count increment
    - Silent usage fetch degradation (backend enforces if frontend fails)

key-files:
  created: []
  modified:
    - backend/routers/competitor.py
    - frontend/src/components/CompetitorAnalyser.tsx

key-decisions:
  - "SCAN_LIMIT=10 hardcoded constant — no per-user config in MVP"
  - "datetime.now(timezone.utc) for month key — explicit UTC prevents Render host variance"
  - "Upsert (not atomic RPC) for count increment — TOCTOU gap documented, acceptable at pharmacy scale"
  - "Silent usage fetch failure — backend enforces limit; frontend degrade-to-enabled is safe"

patterns-established:
  - "Rate limit check pattern: read count → 429 if >= limit → scrape → increment (count only after success)"
  - "Retry-After header: first day of next month in YYYY-MM-DD (December overflow handled)"

duration: ~30min
started: 2026-05-10T00:00:00Z
completed: 2026-05-10T00:30:00Z
---

# Phase 3 Plan 05: Rate Limiting Summary

**Competitor scan quota enforced at 10/month per user — `competitor_scans` table tracks usage with RLS; backend 429s excess requests with Retry-After; frontend badge shows live count and disables form at limit.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~30 min |
| Started | 2026-05-10 |
| Completed | 2026-05-10 |
| Tasks | 3 completed (1 checkpoint, 2 auto) |
| Files modified | 2 |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Scan Proceeds Under Limit | Pass | Rate check reads count; < 10 → scrape proceeds, upsert increments |
| AC-2: Scan Blocked at Limit | Pass | 429 + `scan_limit_reached` detail + Retry-After header; frontend shows reset message and disables button |
| AC-3: Usage Counter Displayed | Pass | `useEffect` fetches `/competitor/usage` on mount; badge shows "N / 10 scans used in [Month YYYY]" |
| AC-4: Monthly Auto-Reset | Pass | YYYY-MM key means new month = no row = count 0 automatically |
| AC-5: Failed Scrape Does Not Consume Quota | Pass | Upsert only reached after `_scrape_with_fallback` returns without raising |

## Accomplishments

- `competitor_scans` table created in Supabase with RLS — SELECT policy allows users to read own rows; writes via service_role only
- Rate limit enforcement in `/competitor/scrape`: reads count before scrape, raises 429 with RFC 9110-compliant `Retry-After` header, increments only on success
- GET `/competitor/usage` endpoint: same auth + premium gate pattern, returns `{count, limit, month}`
- CompetitorAnalyser enhanced: usage badge appears on load, `atLimit` disables submit button, local count increments after successful scan without re-fetch

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `backend/routers/competitor.py` | Modified | Added `_get_current_month()`, `SCAN_LIMIT`, rate check in `/scrape`, upsert after success, new `GET /usage` endpoint |
| `frontend/src/components/CompetitorAnalyser.tsx` | Modified | Added `UsageData` interface, `formatMonth`/`formatNextMonth` helpers, `useEffect` usage fetch, badge UI, `atLimit` button disable, post-scan local increment |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| `datetime.now(timezone.utc)` for month key | Render defaults UTC but explicit prevents cross-host variance | Consistent month boundaries regardless of server locale |
| Upsert not atomic RPC | MVP simplicity; TOCTOU gap (two concurrent requests both read count=9, both proceed → actual 11) documented in code | Acceptable at pharmacy-owner scale; atomic RPC deferred |
| Silent `/usage` fetch failure | Backend enforces limit even if frontend badge fails; no hard error for users | User experience unblocked by network issues; quota still protected |
| Retry-After = first of next month | RFC 9110 §10.6.30 compliance; clear reset signal | December overflow handled: `new Date(year, mon, 1)` JS Date auto-wrap |

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

**Ready:**
- Phase 3 complete — all 5 plans shipped: gosom scraper, competitor flow UI, gap analysis, Outscraper fallback, rate limiting
- Rate limiting in place before any external launch
- Backend and frontend both enforce the 10-scan/month limit

**Concerns:**
- TOCTOU gap in rate limit count (two simultaneous requests can both exceed limit by 1) — documented in code; atomic RPC needed before high-traffic scale
- gosom scraper still requires private networking setup for production (noted in 03-01 deferred issues)

**Blockers:**
- None — Phase 4 (Automation & Suite) can begin

---
*Phase: 03-competitor-analysis, Plan: 05*
*Completed: 2026-05-10*
