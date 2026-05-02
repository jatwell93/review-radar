# Enterprise Plan Audit Report

**Plan:** .paul/phases/01-free-tier-mvp/01-03-PLAN.md
**Audited:** 2026-05-02
**Verdict:** Conditionally acceptable → approved (after auto-applied upgrades)

---

## 1. Executive Verdict

**Conditionally acceptable — approved after applying 3 must-have + 3 strongly-recommended upgrades.**

The plan is well-scoped and architecturally sound: correct use of Next.js App Router client components, recharts already in deps, TypeScript types centralised, and the API contract from 01-02 is precisely specified. However, three production-blocking gaps existed in the original draft around error recovery, concurrent request handling, and silent environment misconfiguration. These have been applied. The plan is now safe to execute.

---

## 2. What Is Solid

- **API contract precision:** Task 1 specifies the exact multipart field name (`file`), trailing slash requirement, and response shape — no guessing during implementation.
- **Empty timeline handled:** Plan explicitly covers `timeline: []` with a graceful fallback message, not a crash. This was anticipated from 01-02's SUMMARY.
- **"use client" placement:** Both components correctly require the directive; plan identifies SSR risk for recharts and resolves it.
- **No dependency sprawl:** recharts already pinned in package.json, no new deps introduced. Boundaries section enforces this explicitly.
- **Top/bottom overlap documented:** The edge case from 01-02 SUMMARY is carried forward correctly — just display both lists, no artificial deduplication.
- **Placeholder for 01-04:** Explicit instruction to leave a comment slot for Claude narrative injection prevents 01-04 from needing to understand ResultsDashboard's full structure.

---

## 3. Enterprise Gaps Identified

### Gap 1 — JSON parse unguarded: loading state hangs on network failure (CRITICAL)
**Original plan:** "On non-ok response: parse response JSON, display `json.detail` as error string; reset isLoading"

`response.json()` throws when the backend is unreachable or returns HTML (502 gateway, CORS failure, nginx error page). That exception is uncaught. `isLoading` stays `true` indefinitely — the spinner never resets. The user sees a permanent loading state with no recovery path. This is a silent hang in production.

### Gap 2 — No concurrent request guard: stale data race (CRITICAL)
**Original plan:** No mention of disabling the upload zone during loading.

If `isLoading === true` and the user drops a second file, a second POST fires. The two responses race. If the slower response resolves last, it calls `onSuccess` with stale data after the first result was already displayed — or it races with a network error that resets state. The upload zone must be disabled during loading.

### Gap 3 — NEXT_PUBLIC_API_URL undefined produces a silent misconfiguration (CRITICAL)
**Original plan:** `${process.env.NEXT_PUBLIC_API_URL}/analyze/`

`NEXT_PUBLIC_*` vars are inlined at build time. If missing from `.env.local`, the value is `undefined` and the URL becomes the string `"undefined/analyze/"`. Next.js does not warn. The fetch throws a `TypeError: Failed to fetch` with no indication of the root cause — a developer wastes significant time before finding the missing env var.

### Gap 4 — No client-side file size check: slow upload before server rejection (MODERATE)
The backend enforces 10 MB. Without a client-side check, a user uploading a 500 MB file streams the entire payload over potentially a slow connection before receiving a rejection. For the target user (pharmacy owner, possibly on mobile), this is a multi-minute hang.

### Gap 5 — ResultsDashboard type imports not specified: risk of `any` drift (MODERATE)
The plan specifies types in `analysis.ts` but does not instruct the implementer to import them in `ResultsDashboard.tsx`. An implementer may inline types or use `any` for the props, causing the TypeScript compiler to miss contract mismatches.

### Gap 6 — Empty review lists produce blank section headings (LOW)
If `top_reviews` and `bottom_reviews` are both empty (pipeline edge case on corrupt-but-parseable CSV), the section headings render with nothing below them. No guard is specified.

---

## 4. Upgrades Applied to Plan

### Must-Have (Release-Blocking)

| # | Finding | Plan Section Modified | Change Applied |
|---|---------|----------------------|----------------|
| 1 | `response.json()` unguarded — loading state hangs on non-JSON response | Task 1 `<action>`, Task 1 `<verify>`, AC-4 added | Wrap fetch + json() in try/catch with finally block; fallback message "Request failed. Please try again."; new AC-4 covers network failure recovery |
| 2 | No concurrent request guard | Task 1 `<action>`, Task 1 `<verify>` | Disable file input and ignore drag events when `isLoading === true`; verify step 5 added |
| 3 | `NEXT_PUBLIC_API_URL` undefined produces `"undefined/analyze/"` | Task 1 `<action>` | `const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'` with `console.warn` guard; URL constructed from `apiUrl` not raw env var |

### Strongly Recommended

| # | Finding | Plan Section Modified | Change Applied |
|---|---------|----------------------|----------------|
| 4 | No client-side file size check | Task 1 `<action>`, Task 1 `<verify>` | `if (file.size > 10 * 1024 * 1024)` guard before POST; verify step 4 added |
| 5 | ResultsDashboard type imports not specified | Task 2 `<action>` | Explicit import instruction: `AnalysisResponse, ReviewItem, TimelineEntry, Distribution` from `@/types/analysis`; "do not use `any`" instruction added |
| 6 | Empty review lists produce blank headings | Task 2 `<action>` | Guard added: if both lists empty, render "No individual review data available" |

### Deferred (Can Safely Defer)

| # | Finding | Rationale for Deferral |
|---|---------|----------------------|
| 7 | AbortController on unmount | React 18 removed the setState-on-unmounted-component warning; no user-visible bug; wasted network only. MVP acceptable. |
| 8 | ARIA roles on drag-drop zone | Pharmacy owners are mouse users; accessibility pass deferred to Phase 2 alongside broader UX hardening |
| 9 | Plain-language VADER threshold explanation | Scale subtext ("-1 to +1") is included; tooltip/explainer is UX refinement, not correctness |

---

## 5. Audit & Compliance Readiness

**Error recovery:** After upgrades, all failure modes produce visible, actionable error messages. No silent hangs. The `finally` block guarantees `isLoading` always resets.

**State integrity:** Concurrent request guard prevents stale data from overwriting a valid result. One request in flight at a time.

**Configuration safety:** API URL guard surfaces missing env var at runtime with a clear warning rather than silently constructing a broken URL.

**Type safety:** Explicit import instruction eliminates `any` drift between the API contract (analysis.ts) and the consumer (ResultsDashboard).

**No audit trail gaps:** This is a stateless UI plan — no server-side state mutations, no writes to external systems. Audit trail requirements are N/A for this scope.

**Post-incident reconstruction:** Browser console warns on missing env var. Error messages are user-visible and specific. No silent failure paths remain after upgrades.

---

## 6. Final Release Bar

**What must be true before this plan ships:**
- All 3 must-have upgrades applied ✓ (done in this audit pass)
- All 3 strongly-recommended upgrades applied ✓ (done in this audit pass)
- `npm run build` exits 0 with no TypeScript errors
- Manual test: upload invalid file → error shown, zone resets; kill backend → "Request failed" shown, zone resets; upload valid CSV → dashboard renders

**Remaining risks after upgrades:**
- Accessibility gap (deferred) — not a correctness risk
- No rate limiting on frontend (backend also lacks it) — acceptable for stateless free tier
- File size check is client-side only — backend 10 MB guard remains the authoritative check

**Sign-off:** After applying the 6 upgrades, this plan is defensible for production. The core failure modes are covered. The scope is tightly bounded. I would approve this for APPLY.

---

**Summary:** Applied 3 must-have + 3 strongly-recommended upgrades. Deferred 3 items.
**Plan status:** Updated and ready for APPLY

---
*Audit performed by PAUL Enterprise Audit Workflow*
*Audit template version: 1.0*
