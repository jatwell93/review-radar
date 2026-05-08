---
phase: 02-paid-tier-core
plan: 03
subsystem: api, database, ui
tags: [supabase, fastapi, nextjs, rls, jwt, stripe, history, auto-save]

# Dependency graph
requires:
  - phase: 02-01
    provides: Supabase auth, SSR client pattern, JWT session, middleware
  - phase: 02-02
    provides: subscriptions table, getSubscriptionStatus(), service role client pattern, premium gating

provides:
  - POST /analyses/ — JWT-authed, premium-gated save endpoint with Pydantic size validators
  - analyses table in Supabase with RLS (insert + select own rows)
  - Auto-save hook in page.tsx — fires silently after analysis for logged-in users, before narrative fetch
  - /dashboard/history — server-rendered premium history list + upgrade prompt for non-premium

affects: [02-04, 02-05, history UI, comparison feature, any phase reading saved analyses]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - trySaveAnalysis fire-and-forget pattern (no await, silent catch, fires before narrative)
    - supabase-py v2 get_user() wrapped in try/except (raises on invalid token, not returns None)
    - Defense-in-depth .eq(user_id) on history query even with RLS active
    - getattr(obj, field, None) for StripeObject attribute access (not .get())

key-files:
  created:
    - backend/routers/analyses.py
    - frontend/src/app/dashboard/history/page.tsx
  modified:
    - backend/main.py (analyses router registered)
    - frontend/src/app/page.tsx (auto-save hook + trySaveAnalysis)

key-decisions:
  - "Save fires before narrative fetch — ensures completion even if user closes tab during AI load"
  - "No client-side premium check before save attempt — let backend 403 silently (simpler, correct)"
  - "analyses insert is NOT upsert — each save is a distinct historical record"
  - "history query uses .eq(user_id) defense-in-depth even with RLS — belt and suspenders"
  - "supabase-py get_user() wrapped in try/except — v2 raises on invalid token rather than returning None"

patterns-established:
  - "StripeObject attribute access: use getattr(obj, field, None), never .get() — stripe-python v15+"
  - "Service role key verification: decode JWT payload and check role=service_role before assuming env is correct"
  - "RLS policy audit: always verify pg_policies after manual migration — policies can be absent even with RLS enabled"

# Metrics
duration: ~2h (including 3 out-of-scope bug fixes discovered during verify)
started: 2026-05-08T08:00:00Z
completed: 2026-05-08T10:00:00Z
---

# Phase 2 Plan 03: Analysis History Summary

**POST /analyses/ backend endpoint + silent auto-save in page.tsx + /dashboard/history page — premium users can now accumulate and review their analysis history over time.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~2h (incl. 3 out-of-scope bug fixes) |
| Started | 2026-05-08 |
| Completed | 2026-05-08 |
| Tasks | 4 completed (2 auto + 2 checkpoints) |
| Files modified | 4 (+ stripe.py bug fix) |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Auto-save fires silently for premium users | Pass | trySaveAnalysis fires after setAnalysisResult, before narrative fetch; verified via Supabase row insert |
| AC-2: Free-tier / unauthenticated users unaffected | Pass | No session → skip; non-premium → backend 403 silently ignored |
| AC-3: History page lists saved analyses for premium users | Pass | /dashboard/history renders date, score, review count ordered newest-first |
| AC-4: History page premium-gates non-subscribers | Pass | Upgrade prompt shown for non-premium authenticated users |
| AC-5: Backend rejects unauthenticated / non-premium save attempts | Pass | No auth header → 401; invalid token → 401; non-premium → 403 |

## Accomplishments

- Backend analyses router with JWT auth, premium gate, typed Pydantic models with size limits, and idempotent insert (not upsert — each save is a distinct historical record)
- Fire-and-forget auto-save in page.tsx that fires before narrative fetch, degrades silently on any failure, and makes no UI changes for any user
- Server-rendered /dashboard/history with premium gate, defense-in-depth RLS query, and clean table UI consistent with dashboard styling
- Analyses table created in Supabase with RLS (users can insert and read own rows only)
- 3 pre-existing bugs discovered and fixed in the stripe.py + Supabase environment during verify

## Task Commits

No atomic commits — all changes in working tree, committed at phase transition.

| Task | Files | Status |
|------|-------|--------|
| Task 1: Backend analyses router | analyses.py, main.py | Complete |
| Task 2: Frontend auto-save + history page | page.tsx, history/page.tsx | Complete |
| Task 3: SQL migration (human-action) | Supabase analyses table + RLS | Complete |
| Task 4: End-to-end verification (human-verify) | All 5 ACs tested | Complete |

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `backend/routers/analyses.py` | Created | POST /analyses/ — JWT auth, premium gate, Supabase insert |
| `backend/main.py` | Modified | analyses router registered after stripe router |
| `frontend/src/app/page.tsx` | Modified | trySaveAnalysis fire-and-forget hook added |
| `frontend/src/app/dashboard/history/page.tsx` | Created | Premium history list + upgrade prompt |
| `backend/routers/stripe.py` | Modified (bug fix) | sub.get() → getattr() for StripeObject compatibility |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Auto-save fires before narrative, not after | Narrative fetch can take 5–10s; firing early ensures save completes even if user closes tab | History row always saved; narrative column is null (acceptable) |
| No client-side premium check | Simpler code; backend 403 is silently ignored anyway | Non-premium users make one extra network request that silently fails |
| INSERT not UPSERT for analyses | Each save is a distinct historical record — idempotency not desired | History accumulates correctly; no accidental overwrites |
| Defense-in-depth .eq(user_id) on history query | Belt-and-suspenders alongside RLS; prevents data leak if policy misconfigured | Explicit filter even with RLS active |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed runtime bugs | 3 | All pre-existing — required to complete verification |
| Scope additions | 0 | None |
| Deferred | 0 | None |

**Total impact:** 3 essential pre-existing fixes, no scope creep.

### Auto-fixed Issues

**1. stripe-python StripeObject `.get()` incompatibility**
- **Found during:** Task 4 verify (checkout.session.completed webhook 500)
- **Issue:** `sub.get("current_period_end")` failed — stripe-python v15+ `Subscription.retrieve()` returns `StripeObject`, not dict; `.get()` raises `AttributeError`
- **Fix:** Changed to `getattr(sub, "current_period_end", None)`
- **Files:** `backend/routers/stripe.py:108`
- **Verification:** Webhook returned 200 after fix; subscription row written

**2. Wrong Supabase key in backend .env**
- **Found during:** Task 4 verify (subscriptions table write returning 42501 RLS violation)
- **Issue:** `SUPABASE_SERVICE_ROLE_KEY` was set to the anon key — JWT payload decoded to `role: anon`, not `role: service_role`; PostgREST used anon role, RLS blocked insert
- **Fix:** User replaced key in `backend/.env` with actual service role key from Supabase dashboard
- **Files:** `backend/.env` (not committed)
- **Verification:** JWT payload re-decoded to `role: service_role`; webhook upsert succeeded

**3. Missing RLS SELECT policy on subscriptions table**
- **Found during:** Task 4 verify (dashboard still showing upgrade CTA despite active subscription row)
- **Issue:** `pg_policies` for `subscriptions` table returned 0 rows — RLS enabled but no policies existed; SSR client (user JWT) could not SELECT own subscription row; `getSubscriptionStatus()` catch block silently returned `'inactive'`
- **Fix:** Added `CREATE POLICY "users can read own subscription" ON subscriptions FOR SELECT USING (auth.uid() = user_id)`
- **Files:** Supabase (SQL migration, manual)
- **Verification:** Dashboard showed "✓ Premium Active" badge immediately after policy added

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| Stripe webhook listener not running from previous session | Restarted `stripe listen --forward-to localhost:8000/stripe/webhook` |
| 8 duplicate Stripe test customers created during failed webhook period | Only one subscription row due to upsert on_conflict=user_id; duplicates cosmetic only |
| venv missing from backend directory | Recreated with `python3 -m venv venv && pip install -r requirements.txt` |

## Next Phase Readiness

**Ready:**
- `analyses` table live with RLS (insert + select own rows)
- `/analyses/` endpoint available for any client with a valid premium JWT
- `/dashboard/history` page rendering correctly for premium and non-premium users
- Auto-save pattern established and working silently end-to-end

**Concerns:**
- `SUPABASE_SERVICE_ROLE_KEY` correctness should be verified before any new environment setup — easy to accidentally use anon key
- RLS policies on all Supabase tables should be audited before launch — missing SELECT policy went undetected until verify
- stripe-python v15+: always use `getattr(obj, field, None)` for StripeObject access, never `.get()`

**Blockers:**
- None

---
*Phase: 02-paid-tier-core, Plan: 03*
*Completed: 2026-05-08*
