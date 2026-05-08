# Enterprise Plan Audit Report

**Plan:** .paul/phases/02-paid-tier-core/02-03-PLAN.md
**Audited:** 2026-05-06
**Verdict:** Conditionally acceptable → approved (2 must-have + 3 strongly-recommended applied)

---

## 1. Executive Verdict

**Conditionally acceptable — approved after fixes applied.**

The plan has correct security fundamentals: JWT validation via Supabase auth.get_user(), premium gating against the subscriptions table, service-role writes with user_id sourced from the validated token (not the request body), and RLS correctly scoped to auth.uid() = user_id. The established patterns from 02-01 and 02-02 are applied consistently.

Two production-blocking gaps were found:
1. A timing bug that silently drops saves for users who close the tab before narrative loads (~5s window)
2. No payload size validation on the save endpoint — a premium token holder can POST arbitrarily large arrays

Three additional gaps were strongly recommended:
1. SaveAnalysisRequest uses untyped dicts instead of the typed models already defined in analyze.py
2. The insert return value extraction pattern was unspecified — would cause a runtime NameError
3. History page query lacks explicit user_id filter as defense-in-depth against RLS misconfiguration

All five findings have been applied to the PLAN.md. Plan is now approved for APPLY.

---

## 2. What Is Solid

**JWT extraction + validation pattern (consistent with stripe.py):** Bearer token extraction, `auth.get_user(token)` for server-side JWT validation, and the 401/403 error structure are all correct and match the established pattern from 02-02. No deviation.

**Subscriptions table check via .limit(1).execute() (not maybe_single()):** The plan explicitly inherits the supabase-py v2 safe pattern from 02-02. This is the correct pattern and correctly cited.

**Service role for backend writes with user_id from JWT:** The backend sets `user_id = str(user.id)` from the validated JWT — never from the request body. This prevents user impersonation even though the service role bypasses RLS. Correctly designed.

**RLS policies on analyses table:** Both the insert `with check` and select `using` policies correctly bind to `auth.uid() = user_id`. Combined with the service-role write pattern, this provides defense in depth for frontend queries.

**Startup env validation at module level:** Validate SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY at import time (RuntimeError) — consistent with stripe.py pattern. Fail-fast before any requests are served.

**Silent degradation for auto-save:** The fire-and-forget design with silent catch is correct. The free-tier experience must never degrade due to a save failure. The 403 (not premium) case is explicitly noted as silently ignored.

**History page as server component with user-scoped Supabase client:** Using `createClient()` from server.ts (which creates a user-scoped client with the session cookie) means RLS is applied server-side. No client-side token handling needed.

---

## 3. Enterprise Gaps Identified

**Gap 1: Auto-save timing — fires after narrative (3-5 second risk window)**
The plan placed `trySaveAnalysis()` after the narrative fetch completes (~3-5 seconds). A user who uploads CSV, sees results render, and closes the tab before the narrative loads never gets their analysis saved. This is the most common usage pattern (results appear first, narrative is secondary). The save is meant to be automatic — missing it silently destroys user trust.

**Gap 2: SaveAnalysisRequest has no field-level size limits**
`timeline: list[dict]`, `top_reviews: list[dict]`, `bottom_reviews: list[dict]` accept unbounded lists. A premium user (or someone with a valid token) can POST 100,000-item arrays, causing memory pressure and storage bloat. The free-tier pipeline produces bounded outputs (max 5 top/bottom, monthly timeline), but the endpoint has no enforcement. Premium subscription gates the token, but doesn't excuse the missing validation.

**Gap 3: Untyped dicts in SaveAnalysisRequest lose consistency with analyze.py models**
`Distribution`, `TimelineEntry`, and `ReviewItem` are already defined as Pydantic models in `routers/analyze.py`. Redefining them as `dict` in `SaveAnalysisRequest` breaks type safety: if a field name changes in the pipeline, the DB silently stores wrong data with no validation error. Using the existing models ensures the saved data always matches what the pipeline produces.

**Gap 4: Insert return value unspecified — would cause NameError at runtime**
The plan said "Return 201 {"id": inserted_row_id}" but did not specify where `inserted_row_id` comes from. supabase-py returns inserted rows in `result.data`. Without `result = ...execute()` and `result.data[0]['id']`, the variable is undefined. This would be a NameError on every successful insert.

**Gap 5: History page query has no explicit user_id filter**
The page uses the user-scoped Supabase server client (RLS applies). However, if a developer accidentally disables RLS on the analyses table in Supabase (common mistake during debugging), the query returns all users' analyses with no server-side filter as a final safety net. Adding `.eq('user_id', user.id)` costs nothing and prevents catastrophic cross-user data exposure.

---

## 4. Upgrades Applied to Plan

### Must-Have (Release-Blocking)

| # | Finding | Plan Section Modified | Change Applied |
|---|---------|----------------------|----------------|
| 1 | Auto-save fires after narrative (3-5s risk window) — user closing tab during narrative loading loses their save | Task 2 action — trySaveAnalysis call site | Changed call to `trySaveAnalysis(data, null)` immediately after `setAnalysisResult(data)`, before narrative fetch. Added explanation: narrative column null is acceptable (history shows score + date only) |
| 2 | No payload size limits on SaveAnalysisRequest list fields — opens storage abuse via large arrays | Task 1 action — SaveAnalysisRequest model | Added Pydantic v2 `Annotated[list[...], Field(max_length=N)]` validators: timeline max 120, top/bottom reviews max 10, narrative max 2000 chars |

### Strongly Recommended

| # | Finding | Plan Section Modified | Change Applied |
|---|---------|----------------------|----------------|
| 1 | SaveAnalysisRequest uses untyped dicts — loses type consistency with analyze.py Pydantic models | Task 1 action — SaveAnalysisRequest model | Changed to import and reuse `Distribution`, `TimelineEntry`, `ReviewItem` from `routers.analyze`. Insert uses `.model_dump()` for serialization |
| 2 | Insert return value unspecified — `inserted_row_id` would be NameError at runtime | Task 1 action — insert block | Added `result = ...execute()`, `inserted_id = result.data[0]['id'] if result.data else None`, and `JSONResponse(status_code=201, ...)` with explicit `from fastapi.responses import JSONResponse` note |
| 3 | History page Supabase query missing explicit user_id filter (defense-in-depth) | Task 2 action — history page query | Added `.eq('user_id', user.id)` to the query chain with comment explaining it as defense-in-depth against RLS misconfiguration |

### Deferred (Can Safely Defer)

| # | Finding | Rationale for Deferral |
|---|---------|----------------------|
| 1 | Per-user analysis count limit (storage abuse protection) | Premium subscribers are real paying users ($20/yr Stripe gate). Blast radius limited. Suitable for post-launch monitoring. |
| 2 | CSV filename / location label not stored with analysis (audit trail gap) | History only shows date + score for this phase. Filename context useful for 02-05 compare UI — deferring to that plan where it has clear UX value. |

---

## 5. Audit & Compliance Readiness

**Silent failures:** The auto-save design correctly swallows all errors — a failed save never surfaces to the user. However, there is no server-side logging specified for save failures. If the DB is unreachable, errors are silent at both layers. For MVP this is acceptable; for production, a structured log (at WARN level) on the 500 catch block would enable monitoring without user-facing impact.

**Post-incident reconstruction:** The analyses table has `created_at` (insert timestamp) and `user_id`. Combined with Supabase's built-in audit log (if enabled), the insert chain can be reconstructed. No analysis ID is returned to the frontend, so client-side correlation is not possible — but this is a fire-and-forget save, not a transactional write.

**Ownership:** Backend writes use service role (accountable to the server process). Frontend queries use user-scoped sessions (accountable to the authenticated user). The boundary is clean.

**Audit evidence:** The human-verify checkpoint explicitly requires inspecting the Supabase Table Editor for the inserted row. This produces observable evidence that the save mechanism works before declaring the plan complete.

---

## 6. Final Release Bar

**What must be true before this plan ships:**
- `trySaveAnalysis` fires before narrative fetch (applied)
- SaveAnalysisRequest validates list lengths (applied)
- Insert uses typed models with `.model_dump()` (applied)
- Insert ID extracted from `result.data[0]['id']` (applied)
- History query includes `.eq('user_id', user.id)` (applied)
- SQL migration runs successfully in Supabase (human-action checkpoint)
- Auto-save confirmed via Supabase Table Editor row check (human-verify checkpoint)
- Free-tier upload flow produces no regression (human-verify checkpoint)

**Remaining risks after fixes:**
- Save failures are silent at both layers — no server-side log. Acceptable for MVP; should be added in a hardening pass.
- No deduplication key — re-uploading the same CSV creates duplicate history rows. This is intentional (each upload is a new event) but could confuse users. Acceptable for 02-03; address if user feedback indicates confusion.

**Sign-off:** Plan is approvable for APPLY with all applied fixes. The core security properties are sound (JWT validation, premium gating, RLS, service-role write with JWT-sourced user_id). The applied fixes close the production-blocking gaps without scope creep.

---

**Summary:** Applied 2 must-have + 3 strongly-recommended upgrades. Deferred 2 items.
**Plan status:** Updated and ready for APPLY.

---
*Audit performed by PAUL Enterprise Audit Workflow*
*Audit template version: 1.0*
