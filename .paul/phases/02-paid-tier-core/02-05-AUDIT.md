# Enterprise Plan Audit Report

**Plan:** .paul/phases/02-paid-tier-core/02-05-PLAN.md
**Audited:** 2026-05-08
**Verdict:** Conditionally acceptable → approved

---

## 1. Executive Verdict

**Conditionally acceptable → approved after applying 3 upgrades.**

The plan is architecturally sound and appropriately scoped for a Phase 2 closure. The core mechanics — backwards-compatible optional fields on `NarrativeRequest`, a server-side comparison card, and a fire-and-forget Supabase snapshot before save — are correctly designed. The race-condition analysis (snapshot before save) is explicit and correct.

However, two input validation gaps and one missing defence-in-depth control required immediate remediation before this plan is production-safe. All three have been applied. Plan is now approved for APPLY.

---

## 2. What Is Solid

| Element | Why It's Solid |
|---------|---------------|
| Backwards-compatible `previous_score` / `previous_distribution` as optional | Free-tier and first-time users are unaffected; no breaking API change |
| Race condition mitigation: snapshot before save | Explicitly prevents the "current becomes previous" bug; analysis is correct |
| Silent degradation in Task 3 (try/catch, null default) | Trend context is an enhancement; narrative never breaks if Supabase is slow or offline |
| `maybeSingle()` instead of `single()` for the previous query | Returns `null` on no rows rather than throwing PGRST116; correct for "no history" case |
| `setNarrativeLoading(true)` moved before the async snapshot | Skeleton appears immediately; UX latency is absorbed while Supabase query runs |
| History page comparison card: `analyses.length >= 2` guard | Never renders with a null `previous` reference |
| Threshold-based direction (`> 0.02` / `< -0.02`) | Prevents "held steady" being mislabelled for noise-level fluctuations |

---

## 3. Enterprise Gaps Identified

### Gap 1 — `previous_distribution: dict | None` bypasses Pydantic validation (Must-Have)

**What:** The plan specified `previous_distribution: dict | None = None` in `NarrativeRequest`. An untyped `dict` accepts any structure — including `{"positive": "DROP TABLE"}`, `{"positive": null}`, or missing keys entirely.

**Risk:** The `generate_narrative` service accesses `previous_distribution.get("positive", 0)`. With an untyped dict:
- Non-integer values produce nonsense in the Claude prompt without error
- Missing keys silently default to 0, producing a misleading delta ("Negative reviews: +5" when the count wasn't actually 5)
- No 422 response to tell the caller their payload is malformed

**`Distribution` is already imported in `narrative.py` from `routers.analyze`.** There is zero cost to using the typed model.

### Gap 2 — `previous_score` has no range constraint (Strongly Recommended)

**What:** `previous_score: float | None = None` with no bounds. VADER scores are bounded `[-1.0, 1.0]`.

**Risk:** A caller can send `previous_score: 999.0` (intentionally or via a client-side bug). The Claude prompt would then say "score improved from 999.00 to 0.55" — factually absurd, potentially confusing to the pharmacy owner, and embarrassing if shared. The `/narrative/` endpoint has no auth for free-tier users, making this fully exploitable without authentication.

**Fix:** `Field(ge=-1.0, le=1.0, default=None)` — FastAPI returns 422 automatically for out-of-range values. Requires adding `Field` to the pydantic import.

### Gap 3 — Task 3 Supabase query missing defence-in-depth `.eq("user_id", session.user.id)` (Strongly Recommended)

**What:** The browser-client Supabase query for previous analysis relies solely on RLS for user-scoping. All other Supabase reads in this codebase that target user-owned data include `.eq("user_id", user.id)` as explicit defence-in-depth (documented as a project decision in 02-03-SUMMARY.md).

**Risk:** If RLS misconfiguration occurs (e.g., during a migration, a policy drop/recreate), the query would return results from other users. The previous score would silently belong to a different user's analysis. This is a cross-user data leakage vector at the application layer.

`session.user.id` is already available in the code block — zero additional queries required.

---

## 4. Upgrades Applied to Plan

### Must-Have (Release-Blocking)

| # | Finding | Plan Section Modified | Change Applied |
|---|---------|----------------------|----------------|
| 1 | `previous_distribution: dict | None` bypasses Pydantic validation — use typed `Distribution | None` | Task 1 action — NarrativeRequest definition | Changed type to `Distribution | None = None`; added note that `Distribution` is already imported; added `Field` import note alongside `previous_score` fix |

### Strongly Recommended

| # | Finding | Plan Section Modified | Change Applied |
|---|---------|----------------------|----------------|
| 2 | `previous_score` has no range bounds — VADER scale is [-1.0, 1.0] | Task 1 action — NarrativeRequest definition | Changed to `Field(default=None, ge=-1.0, le=1.0)`; added `Field` to required pydantic import |
| 3 | Task 3 Supabase query missing `.eq("user_id", session.user.id)` defence-in-depth | Task 3 action — both the step-by-step snippet and the full `handleAnalysisSuccess` block | Added `.eq("user_id", session.user.id)` to both occurrences of the query chain |

### Deferred (Can Safely Defer)

| # | Finding | Rationale for Deferral |
|---|---------|------------------------|
| 4 | Trend threshold `0.02` is a magic number — should be a named constant for tunability | No user impact; threshold is sensible for VADER scale; easy to extract later; not worth a plan change for a single constant |
| 5 | No rate limiting on `/narrative/` endpoint for unauthenticated callers | Pre-existing architecture (narrative endpoint was always unauthenticated for free-tier). This plan adds no new exposure. Rate limiting belongs in infrastructure layer (Render/Cloudflare), not this plan. |

---

## 5. Audit & Compliance Readiness

**Evidence production:** The narrative endpoint returns `{"narrative": "..."}` — no `previous_score` or `previous_distribution` is echoed back, preventing inadvertent data leakage in logs or responses. ✓

**Silent failure prevention:** Task 3's `try/catch` around the Supabase snapshot is correct: failures degrade gracefully (narrative runs without trend context) and do not surface errors to the user. The verification checks now explicitly test that malformed `previous_score` (999.0) and `previous_distribution` (bad type) return 422, not 500. ✓

**Post-incident reconstruction:** Supabase logs the raw request body to `/narrative/`. After applying Finding 1 (typed `Distribution`), malformed distributions are rejected at the edge with a 422 — no ambiguous partial-execution states reach Claude. ✓

**Cross-user data isolation:** After applying Finding 3, the browser client query includes an explicit user ID filter as defence-in-depth against RLS misconfiguration. Consistent with the codebase's established pattern. ✓

**Audit trail weakness remaining:** The `/narrative/` endpoint logs calls with no user identity (it is intentionally unauthenticated for free-tier). This is a pre-existing condition accepted at project inception and is out of scope for this plan.

---

## 6. Final Release Bar

**Must be true before this plan ships:**
- `previous_distribution` uses `Distribution | None` with Pydantic validation ✓ (applied)
- `previous_score` is bounded `[-1.0, 1.0]` ✓ (applied)
- Browser Supabase query includes `.eq("user_id", session.user.id)` ✓ (applied)
- Verification checklist includes 422 tests for out-of-range `previous_score` and malformed `previous_distribution` ✓ (applied)

**Risks that remain if shipped as-is (post-fixes):**
- `/narrative/` endpoint has no auth and no rate limiting. A determined caller can generate unlimited Claude Haiku calls at Anthropic API cost. This is pre-existing and accepted — mitigating it requires per-IP or API key limiting at the infrastructure layer.
- `Distribution.positive/neutral/negative` has no `ge=0` constraint — negative review counts are technically accepted. This is a pre-existing gap in `routers/analyze.py` not introduced by this plan.

**Sign-off:** With the three applied upgrades, I would approve this plan for production execution.

---

**Summary:** Applied 1 must-have + 2 strongly-recommended upgrades. Deferred 2 items.
**Plan status:** Updated and ready for APPLY

---
*Audit performed by PAUL Enterprise Audit Workflow*
*Audit template version: 1.0*
