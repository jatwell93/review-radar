# Enterprise Plan Audit Report

**Plan:** `.paul/phases/03-competitor-analysis/03-02-PLAN.md`
**Audited:** 2026-05-09
**Verdict:** Conditionally acceptable → approved after applying 1 must-have + 2 strongly-recommended upgrades

---

## 1. Executive Verdict

**Conditionally acceptable.** The plan's auth layering, premium gate, and basic error handling are correctly structured. However, three concrete gaps — one release-blocking and two production-reliability issues — were identified and auto-applied. After remediation, the plan is approved for APPLY.

Would I sign off on this? Yes, after the applied fixes.

---

## 2. What Is Solid

- **Server Component auth architecture:** `getSubscriptionStatus()` + redirect pattern matches `history/page.tsx` exactly — auth is resolved server-side before any UI renders; no auth bypass vector in this design.
- **Client-side URL validation before API call:** Prevents trivial bad requests from ever reaching the backend. Correctly mirrors backend's `field_validator` as a UX pre-check, not as a security control (backend validates authoritatively).
- **Session token retrieval in submit handler:** Calling `getSession()` inside `handleSubmit` (not in component state/effect) avoids stale token bugs. Correct pattern.
- **`finally` block for `setLoading(false)`:** Loading state is guaranteed to clear regardless of success, error, or exception path.
- **Error status code mapping:** 422 → validation message, 502 → scraper message. User never sees raw HTTP codes or technical error strings.
- **Empty reviews gracefully handled:** `reviews.length === 0` renders a message, not a crash. Consistent with 03-01 AC-7 contract.
- **`NEXT_PUBLIC_API_URL` env var:** Not hardcoded. Correct.
- **Boundaries section:** Explicitly protects backend, auth helpers, unrelated components. No scope creep risk.

---

## 3. Enterprise Gaps Identified

### Gap 1 (Must-Have): `res.json()` throws unhandled `SyntaxError` on non-JSON response body

**Risk:** The plan's success path is `setResult(await res.json())`. If the backend returns a 200 with a non-JSON body — HTML error page from Render, empty body from a crashed process, partial JSON from a mid-response crash — `res.json()` throws `SyntaxError`. This exception is NOT caught at the call site. The unhandled exception propagates past the `finally` (loading clears), but produces no user-visible error. The user sees: loading stops, no result appears, no error message. Silent failure with no recovery path.

Additionally: the `!res.ok` branch sets an error but the plan does not explicitly state `return` after doing so. Without an explicit `return`, execution falls through to `setResult(await res.json())` on the error response body, which may also throw or produce garbage data.

**Affected:** Task 2 `handleSubmit` step 4-5.

### Gap 2 (Strongly Recommended): No request timeout — indefinite loading if gosom stalls

**Risk:** The backend has `_GOSOM_POLL_TIMEOUT = 180s` and `_GOSOM_REQUEST_TIMEOUT = 30s`, but the browser `fetch()` has no default timeout. If gosom enters a state where it neither completes nor returns an error within 180s (network partition, partial response, Render container OOM), the backend may itself hang and never return. The frontend `fetch()` will hang indefinitely. The user is stuck in loading state with no way to recover without a hard browser refresh. Given the amber warning says "please keep this page open", users will wait far longer than they should before realising something is wrong.

A 240s (4 min) frontend ceiling — slightly above the backend's ~210s maximum — ensures the frontend always recovers gracefully even if the backend hangs, and shows a clear timeout message.

**Affected:** Task 2 `handleSubmit`.

### Gap 3 (Strongly Recommended): `<a>` instead of `<Link>` for internal CTA on dashboard page

**Risk:** The dashboard CTA `<a href="/dashboard/competitor">` causes a full browser navigation (page unload + full Next.js bootstrap) instead of a client-side SPA route transition. In a Next.js App Router application this is the correct tool for external links only. Internal navigation via `<a>` disables route prefetching, slows navigation (~200-400ms additional cold start), and defeats Next.js's automatic page transition optimizations. While not a data integrity risk, this is a visible UX degradation on the most prominent premium user action.

**Affected:** Task 1, `dashboard/page.tsx` CTA.

### Gap 4 (Can Safely Defer): No `← Back to Dashboard` navigation in competitor page

Users on `/dashboard/competitor` have no in-page navigation back to `/dashboard`. Browser back button is the only mechanism. On mobile or embedded webviews, this may leave users stranded. Not a data risk, purely UX polish.

### Gap 5 (Can Safely Defer): `Math.round(r.rating)` without bounds guard in star display

`'★'.repeat(Math.round(r.rating))` — if `r.rating` is 0 (no stars, possible for edge case reviews), renders empty string (acceptable). If `r.rating` comes back as a float like 5.5 (rounds to 6), `'★'.repeat(6)` renders 6 stars (visually wrong). The backend normalizes via `float()` and gosom ratings are 1-5, making this unlikely. A `Math.min(5, Math.max(0, Math.round(r.rating)))` guard would be strictly correct. Safe to defer given the normalized upstream contract.

---

## 4. Upgrades Applied to Plan

### Must-Have (Release-Blocking)

| # | Finding | Plan Section Modified | Change Applied |
|---|---------|----------------------|----------------|
| 1 | `res.json()` throws unhandled `SyntaxError` on non-JSON response; no explicit `return` after `!res.ok` error path (fall-through risk) | Task 2 `<action>`, Task 2 `<verify>`, `<verification>`, AC section | Added explicit `return` after each `setError()` in `!res.ok` branch; wrapped `res.json()` in try/catch with user-friendly error message; added AC-7 (malformed response) and verification checks |

### Strongly Recommended

| # | Finding | Plan Section Modified | Change Applied |
|---|---------|----------------------|----------------|
| 2 | No frontend timeout — indefinite loading if gosom stalls beyond its own 180s ceiling | Task 2 `<action>` steps 3+, `<verify>`, `<verification>`, AC section | Added `AbortController` with 240s `setTimeout`; `signal` passed to `fetch`; `AbortError` caught separately → "Scraper timed out" message; `clearTimeout` in `finally`; added AC-8 (timeout) and verification checks |
| 3 | `<a>` for internal CTA causes full page reload — should be `<Link>` from `next/link` | Task 1 `<action>`, `<verify>`, `<verification>` | Replaced `<a href="...">` with `<Link href="...">` from `next/link`; added `import Link from 'next/link'` instruction; added verify check for `<Link>` usage |

### Deferred (Can Safely Defer)

| # | Finding | Rationale for Deferral |
|---|---------|----------------------|
| 4 | No `← Back to Dashboard` navigation in competitor page | UX polish, not a production risk. Browser back button is sufficient for MVP. Can add in 03-02 polish or a future UI pass. |
| 5 | `Math.round(r.rating)` without `Math.min/Max` bounds guard | Gosom ratings are 1-5; backend normalizes via `float()`. Edge case is astronomically unlikely. Cosmetic at worst. |

---

## 5. Audit & Compliance Readiness

**Evidence production:** The component provides user-visible error messages for all failure modes (401, 403, 422, 502, timeout, malformed response) after audit fixes. No silent failures remain.

**Post-incident reconstruction:** No server-side logging is introduced in this plan (frontend-only). If a scrape fails silently in production, investigation would require backend logs (03-01 scope, already in place via FastAPI). Acceptable for this plan's scope.

**Silent failure prevention:** After applying must-have fix, all code paths produce user-visible feedback. The `finally` block guarantees loading state always clears.

**Ownership:** The premium gate is enforced server-side (Server Component + Supabase) and backend-side (JWT + subscription check in competitor.py). Frontend-only gate bypass cannot grant access to scrape results.

**Audit trail weakness:** No logging of competitor scrape attempts at the frontend layer. Backend logs in 03-01 handle this. Acceptable.

---

## 6. Final Release Bar

**Must be true before this plan ships:**
- `res.json()` is wrapped in try/catch with explicit `return` after error branches (applied)
- `AbortController` with 240s timeout wired to fetch `signal` (applied)
- `<Link>` used for internal CTA (applied)

**Remaining risks after applied fixes:**
- Scrape duration (1-3 min) is inherent to gosom's job-based API — the amber warning card mitigates user confusion
- `NEXT_PUBLIC_API_URL` undefined in build will surface as a runtime `fetch` error (shows generic error message to user) — acceptable, deployment concern not plan gap
- No back-navigation on competitor page (UX gap, deferred)

**Sign-off:** Yes, I would sign off on this plan with the applied fixes. The authentication architecture is solid, the error contract is well-defined, and the scope boundaries are correctly enforced.

---

**Summary:** Applied 1 must-have + 2 strongly-recommended upgrades. Deferred 2 items.
**Plan status:** Updated and ready for APPLY

---
*Audit performed by PAUL Enterprise Audit Workflow*
*Audit template version: 1.0*
