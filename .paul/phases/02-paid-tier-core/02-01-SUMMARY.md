---
phase: 02-paid-tier-core
plan: 01
subsystem: auth
tags: [supabase, supabase-ssr, next-auth, middleware, email-auth, session, cookies]

requires:
  - phase: 01-free-tier-mvp
    provides: Next.js 14 App Router scaffold with Tailwind and working /api routes

provides:
  - Supabase email auth (sign-up, login, logout)
  - Session middleware protecting /dashboard/* routes
  - Auth callback route for Supabase PKCE code exchange
  - Stub /dashboard page (authenticated landing point for Phase 2+)

affects: [02-02-payments, 02-03-history, 02-04-keybert, 02-05-compare]

tech-stack:
  added:
    - "@supabase/supabase-js@^2.45.0"
    - "@supabase/ssr@^0.5.0"
  patterns:
    - createBrowserClient (client components) vs createServerClient (server components/middleware)
    - Middleware uses getUser() not getSession() for server-side JWT validation
    - Server action for logout (avoids client-side signOut + push pattern)
    - /auth/callback excluded from middleware matcher to allow PKCE code exchange

key-files:
  created:
    - frontend/src/lib/supabase/client.ts
    - frontend/src/lib/supabase/server.ts
    - frontend/src/middleware.ts
    - frontend/src/app/(auth)/login/page.tsx
    - frontend/src/app/(auth)/signup/page.tsx
    - frontend/src/app/auth/callback/route.ts
    - frontend/src/app/dashboard/page.tsx
  modified:
    - frontend/package.json

key-decisions:
  - "Use @supabase/ssr (not supabase-js directly) for Next.js App Router cookie handling"
  - "getUser() over getSession() in middleware — getUser() validates JWT server-side"
  - "Server action for logout — avoids flash of stale state from client-side signOut"
  - "/auth/callback placed outside (auth) route group — Supabase redirects to literal /auth/callback path"

patterns-established:
  - "All server-side Supabase calls use lib/supabase/server.ts createClient()"
  - "All client-side Supabase calls use lib/supabase/client.ts createClient()"
  - "Middleware protects /dashboard/* and redirects auth pages for authenticated users"

duration: ~45min
started: 2026-05-03T00:00:00Z
completed: 2026-05-03T00:45:00Z
---

# Phase 2 Plan 01: Auth Summary

**Supabase email auth wired into Next.js 14 App Router with session middleware protecting /dashboard/*, browser + server Supabase clients, login/signup pages, PKCE callback, and server-action logout.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~45 min |
| Started | 2026-05-03 |
| Completed | 2026-05-03 |
| Tasks | 3 completed + 1 checkpoint |
| Files modified | 10 (9 created, 1 modified) |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Sign-up creates account | Pass | Email+password creates Supabase user; session or "check email" flow handled |
| AC-2: Login establishes session | Pass | signInWithPassword → session cookie → /dashboard |
| AC-3: Protected routes redirect | Pass | /dashboard without session → /login |
| AC-4: Auth pages redirect authenticated users | Pass | /login or /signup with active session → /dashboard |
| AC-5: Logout clears session | Pass | Server action signOut() → redirect /login |

## Accomplishments

- Supabase `@supabase/ssr` integrated with Next.js 14 App Router cookie pattern (getAll/setAll)
- Session middleware using `getUser()` for server-side JWT validation on every request
- Auth flow handles both email-confirmation-enabled and email-confirmation-disabled Supabase configurations
- Free tier `/` page untouched — zero regression to Phase 1 functionality

## Task Commits

Tasks were not committed atomically during this session (no git commits made). Full phase commit will be made at phase transition.

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `frontend/package.json` | Modified | Added @supabase/supabase-js ^2.45.0, @supabase/ssr ^0.5.0 |
| `frontend/src/lib/supabase/client.ts` | Created | Browser Supabase client via createBrowserClient |
| `frontend/src/lib/supabase/server.ts` | Created | Server/RSC Supabase client via createServerClient |
| `frontend/src/app/(auth)/layout.tsx` | Created | Centered card layout for login/signup pages |
| `frontend/src/app/(auth)/login/page.tsx` | Created | Email+password login form with error display |
| `frontend/src/app/(auth)/signup/page.tsx` | Created | Email+password signup with email-confirmation fallback |
| `frontend/src/app/auth/callback/route.ts` | Created | PKCE code exchange route handler for Supabase redirects |
| `frontend/src/middleware.ts` | Created | Session middleware: protects /dashboard/*, redirects auth pages |
| `frontend/src/app/dashboard/layout.tsx` | Created | Minimal layout wrapper for dashboard route group |
| `frontend/src/app/dashboard/page.tsx` | Created | Stub dashboard: user email display + server-action logout |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| `getUser()` over `getSession()` in middleware | `getSession()` reads from cookie without server validation; `getUser()` validates JWT against Supabase server | Secure auth checks on every protected route request |
| Server action for logout | Client-side signOut + router.push can flash stale state before redirect | Clean session teardown, no client-side state race |
| `/auth/callback` excluded from middleware matcher | Middleware intercepting the callback route would break PKCE code exchange | Email confirmation flow works correctly |
| Stub `/dashboard` in this plan | Paid dashboard content built in 02-03+; stub proves auth gate works and gives a redirect target | Unblocks checkpoint verification without scope creep |

## Deviations from Plan

### Summary

| Type | Count | Impact |
|------|-------|--------|
| Auto-fixed | 1 | None — essential TypeScript fix |
| Scope additions | 0 | — |
| Deferred | 0 | — |

**Total impact:** Single essential fix, no scope creep.

### Auto-fixed Issues

**1. TypeScript implicit `any` in `server.ts` setAll callback**
- **Found during:** Task 1 qualification (tsc --noEmit)
- **Issue:** `cookiesToSet` parameter and destructured `{ name, value, options }` had implicit `any` types under strict mode
- **Fix:** Added `import { type CookieOptions } from '@supabase/ssr'` and typed parameter as `{ name: string; value: string; options: CookieOptions }[]`
- **Files:** `frontend/src/lib/supabase/server.ts`
- **Verification:** tsc --noEmit passed with 0 errors after fix

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| User initially placed Supabase Secret (service role) key in NEXT_PUBLIC_SUPABASE_ANON_KEY | Corrected to Publishable key — Supabase renamed anon→Publishable, service_role→Secret |
| "missing email or phone" XHR 400 during testing | Benign artifact: user submitted empty login form during AC-4 test when session was still active; middleware redirect fires on next navigation |

## Next Phase Readiness

**Ready:**
- Supabase client utilities available to all subsequent plans via `@/lib/supabase/client` and `@/lib/supabase/server`
- Session middleware running — 02-02 can add subscription status checks to the same middleware
- `/dashboard` route group established — 02-03 replaces stub page with real history UI
- Auth callback route in place — Supabase magic links and OAuth (future) route through `/auth/callback`

**Concerns:**
- None. Pattern is clean and matches Supabase's recommended Next.js App Router approach.

**Blockers:**
- None.

---
*Phase: 02-paid-tier-core, Plan: 01*
*Completed: 2026-05-03*
