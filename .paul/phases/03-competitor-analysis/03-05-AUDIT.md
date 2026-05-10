# Enterprise Plan Audit Report

**Plan:** `.paul/phases/03-competitor-analysis/03-05-PLAN.md`
**Audited:** 2026-05-08
**Verdict:** Conditionally acceptable → approved (after findings applied)

---

## 1. Executive Verdict

**Conditionally acceptable — approved after auto-applied fixes.**

The plan is architecturally sound. The auth pattern is established and consistent, the YYYY-MM key design for monthly reset is elegant and correct, and the service-role-writes / user-RLS-reads security layering is the right model. However, in its original form the plan had three release-blocking gaps (undefined timezone, no failed-scrape protection, missing audit column) and four strongly-recommended improvements. All seven have been auto-applied. The plan is now ready for APPLY.

---

## 2. What Is Solid

- **JWT auth + premium gate pattern**: Consistent with `analyses.py` and `stripe.py` — established, tested pattern. No reinvention.
- **YYYY-MM text key for monthly reset**: Avoids date math complexity. Natural reset by new key — no cron job, no reset logic, no edge cases at month boundaries. Correct design.
- **Service role for writes, SELECT-only RLS for reads**: Users cannot inflate or reset their own counts via the client. Backend-authoritative count is the only source of truth.
- **`UNIQUE(user_id, scan_month)` DB constraint**: Enforces at database level — even if application logic has a bug, duplicate rows are impossible.
- **Degraded UI on `/usage` failure**: Silent degradation is correct — backend enforces the limit regardless. Not showing a badge on failure is better than a broken error state.
- **TOCTOU acknowledged in plan text**: The non-atomic upsert race condition is explicitly called out as a known MVP trade-off rather than silently shipped.

---

## 3. Enterprise Gaps Identified

### Gap 1 — `datetime.now()` uses server local time [MUST-HAVE]
`datetime.now()` without timezone info uses the process's local timezone. On Render, this is currently UTC, but it's implicit and fragile. If the deployment region changes, month boundaries shift silently. Month boundaries are the entire correctness guarantee of the YYYY-MM key design — this must be explicit.

### Gap 2 — No AC or task instruction for failed-scrape quota behaviour [MUST-HAVE]
The plan said "increment after scrape completes successfully" without defining "successfully." If the scrape raises an exception (network failure, gosom blocked, Outscraper error), Python propagates the exception before the upsert, so the count is not incremented. This is the correct accidental behaviour, but it's unspecified — meaning a future implementer could move the increment before the scrape call and break this guarantee. Needs an explicit AC and task instruction.

### Gap 3 — `competitor_scans` table missing `created_at` [MUST-HAVE]
Without a timestamp column, there is no audit trail for "I already used 10 scans" disputes. No way to reconstruct when scans occurred, debug unexpected limit hits, or investigate support tickets. At minimum, `created_at TIMESTAMPTZ DEFAULT now()` is required.

### Gap 4 — No `Retry-After` header on 429 responses [STRONGLY RECOMMENDED]
RFC 9110 §10.6.30 specifies that 429 responses SHOULD include a `Retry-After` header. Without it, clients (including the frontend) have to infer the reset time from the `month` field. Adding `Retry-After: YYYY-MM-01` (first of next month) is a one-liner and makes the API behaviorally correct for any future client.

### Gap 5 — Verification missing non-premium 403 for `/competitor/usage` [STRONGLY RECOMMENDED]
The verify section checked 401 (no auth) but not 403 (non-premium). The premium check on `/usage` is intentional and correct — but if it's not in the verification checklist, it won't be tested.

### Gap 6 — Frontend "next month" calculation December overflow [STRONGLY RECOMMENDED]
The plan instructed "add 1 month to the parsed YYYY-MM." A naive implementation of `parseInt(month) + 1` produces `month=13` in December — a silent bug that produces an incorrect UI label for 1 month per year. JavaScript's `Date` constructor accepts month index 13 and rolls over to January of the next year, but this is non-obvious and would pass review. Explicit safe pattern needed.

### Gap 7 — TOCTOU race not documented in verification checklist [STRONGLY RECOMMENDED]
The plan text acknowledged the TOCTOU gap, but the verification checklist didn't. Verification checklists are read without the surrounding prose. The known trade-off needs to appear there as a documented conscious decision, not be silently absent.

---

## 4. Upgrades Applied to Plan

### Must-Have (Release-Blocking)

| # | Finding | Plan Section Modified | Change Applied |
|---|---------|----------------------|----------------|
| 1 | `datetime.now()` uses server local time | Task 2 action | Changed to `datetime.now(timezone.utc)`, added `timezone` to import |
| 2 | No AC/instruction for failed-scrape quota protection | Acceptance Criteria + Task 2 action | Added AC-5 (failed scrape doesn't consume quota) + clarified increment placement relative to scrape exception handling |
| 3 | `competitor_scans` table missing `created_at` | Task 1 (SQL migration) | Added `created_at TIMESTAMPTZ DEFAULT now() NOT NULL` to CREATE TABLE |

### Strongly Recommended

| # | Finding | Plan Section Modified | Change Applied |
|---|---------|----------------------|----------------|
| 4 | No Retry-After header on 429 response | Task 2 action | Added Retry-After header computation (first-of-next-month date) to 429 raise |
| 5 | Verification gap: non-premium 403 on `/usage` not tested | Task 2 verify + overall verification | Added non-premium 403 check to both verify blocks |
| 6 | Frontend December/month overflow in "next month" label | Task 3 action | Replaced prose instruction with explicit JS `Date` constructor pattern with December example |
| 7 | TOCTOU race undocumented in verification | Overall verification | Added explicit checklist item documenting the known MVP trade-off |

### Deferred (Can Safely Defer)

| # | Finding | Rationale for Deferral |
|---|---------|----------------------|
| 1 | Atomic increment via PostgreSQL RPC (`UPDATE ... RETURNING`) | Plan already acknowledges this. At pharmacy-owner scale (single user, single session), simultaneous concurrent scans are implausible. Safe until multi-user or high-frequency scenario. |
| 2 | `Retry-After` timestamp in `/usage` response body | Client can compute from `month` field. Added as a response header (Retry-After) which is the standard mechanism. Body duplication adds noise. |

---

## 5. Audit & Compliance Readiness

**Audit trail:** With `created_at` added, the `competitor_scans` table now supports post-incident reconstruction ("when did user X run scan N?"). Without this column the table was forensically opaque.

**Silent failure prevention:** The `/usage` endpoint degrading silently in the frontend is correct — the backend is the enforcement point. Silent client degradation does not introduce silent server failures.

**Ownership:** The plan has clear task ownership (human-action for migration, auto tasks for code). The premium gate is applied to both the scan and usage endpoints, ensuring non-premium users cannot reach the rate limit logic at all.

**SOC 2 / audit-defensible:** The permission model (service role writes, user-scoped reads via RLS) is standard and defensible. The rate limit is enforced server-side — client-side disabled state is UX-only.

---

## 6. Final Release Bar

**Before shipping:**
- `datetime.now(timezone.utc)` must be used — not optional
- `created_at` column must be in the migration SQL
- AC-5 (failed-scrape quota protection) must be verified by simulating a scrape exception
- Retry-After header must be present in 429 responses
- December → January month label must be tested or verified in code review

**Remaining risks after fixes applied:**
- TOCTOU race (up to 1 over-count under simultaneous requests) — acceptable at stated scale, documented
- `competitor_scans` count is not carried forward across months (by design) — no rollover; users starting fresh each month is the intended behaviour

**Sign-off:** Conditionally signed. The plan is production-appropriate for the stated MVP scale after the seven applied fixes. A pharmacy owner SaaS at early stage does not require atomic DB primitives for a 10-scan/month limit. The risks that remain are deliberate trade-offs, documented, and reversible.

---

**Summary:** Applied 3 must-have + 4 strongly-recommended upgrades. Deferred 2 items.
**Plan status:** Updated and ready for APPLY

---
*Audit performed by PAUL Enterprise Audit Workflow*
*Audit template version: 1.0*
