# Enterprise Plan Audit Report

**Plan:** `.paul/phases/03-competitor-analysis/03-01-PLAN.md`
**Audited:** 2026-05-08
**Verdict:** Conditionally acceptable → approved

---

## 1. Executive Verdict

Conditionally acceptable. The core architecture is sound — auth/premium gate pattern is exactly consistent with the established codebase, scope is tightly bounded, and boundaries are explicit. Three must-have gaps required remediation before this plan could be executed safely: an unbounded URL payload field, unhandled normalization failure on unexpected gosom response format, and no access control documented for the gosom service endpoint. All have been applied.

Would I approve this for production with the applied fixes? Yes, with the gosom private service migration documented as a pre-commercial launch requirement.

---

## 2. What Is Solid

- **Auth pattern consistency**: Bearer token → `get_user()` → premium gate exactly matches `analyses.py`. No deviation, no novel auth logic. Enterprise reviewers will recognise this as intentionally consistent.
- **Module-level fail-fast env var validation**: `_REQUIRED_ENV_VARS` loop at import time matches `stripe.py` pattern. Prevents cryptic runtime failures on misconfigured deploys.
- **502 wrapping for scraper failures**: `_call_gosom` catches all exceptions and re-raises as `HTTPException(502, "scraper_unavailable")`. Clients never see raw tracebacks or httpx internals.
- **Async httpx with 120s timeout**: Prevents thread starvation on slow scrapes without blocking indefinitely. Correct choice for an async FastAPI endpoint.
- **Response contract normalization**: Mapping gosom's unknown field names to a stable `{"name", "overall_rating", "reviews"}` shape protects downstream plans (03-03 gap analysis) from gosom API changes.
- **Boundaries section**: Explicit protection of `analyses.py`, `stripe.py`, all existing Supabase tables, and the frontend. Prevents scope bleed during execution.

---

## 3. Enterprise Gaps Identified

### Gap 1: URL payload has no length bound
`url: str` with only a `startswith` validator accepts strings of arbitrary length. A 10MB URL passes Pydantic validation and propagates through the entire auth + premium check pipeline before reaching gosom. Standard payload abuse pattern.

### Gap 2: gosom response normalization is unguarded
If gosom returns an unexpected structure (list instead of dict, non-numeric `rating`, missing `reviews` key returning a non-list), the normalization block raises an unhandled `TypeError` or `AttributeError` → FastAPI wraps this as a 500. The plan instructs "adjust field names to match gosom docs" without a safety net for when gosom changes its format or returns an error body that passes `raise_for_status()` but has unexpected shape.

### Gap 3: gosom service has no access control
The gosom Render web service, once deployed, exposes an unauthenticated HTTP endpoint. On Render free tier this is a public URL — any party can trigger Google Maps scraping against the bare service without going through the auth-gated FastAPI endpoint. The plan was silent on this risk.

### Gap 4: GOSOM_API_URL missing from render.yaml for review-radar-api
All other required env vars (`ANTHROPIC_API_KEY`, `ALLOWED_ORIGINS`) are documented in render.yaml with `sync: false`. `GOSOM_API_URL` was absent, breaking the operational pattern — someone deploying from render.yaml would not know it exists.

### Gap 5: No direct gosom server health check in verification
The verification steps jump to FastAPI curl tests, relying on "gosom stopped → 502" as implicit proof. If the gosom CMD flags are wrong (server mode doesn't start), the container exits silently and the 502 path is tested, but the actual gosom server mode is never confirmed working. A direct curl to the gosom endpoint is needed.

### Gap 6: Empty reviews contract undocumented
`raw.get("reviews", [])` returning an empty list produces a valid 200 response, but the downstream plans (03-03) have no explicit contract stating this. The behaviour is correct but the contract was not stated as an acceptance criterion.

---

## 4. Upgrades Applied to Plan

### Must-Have (Release-Blocking)

| # | Finding | Plan Section Modified | Change Applied |
|---|---------|----------------------|----------------|
| 1 | URL field lacks `max_length` — unbounded payload | Task 2, CompetitorScrapeRequest | Added `Field(max_length=2000)` and `Field` import; added 422 verify step for oversized URL |
| 2 | gosom response normalization unguarded — unhandled 500 on unexpected format | Task 2, scrape endpoint normalization block | Wrapped normalization in `try/except Exception → HTTPException(502, "scraper_response_invalid")`; added verify step for malformed response |
| 3 | gosom service access control unspecified — open HTTP endpoint on free tier | Task 1, render.yaml action | Added private service access control documentation: paid plan = Render Private Service; free tier = documented risk; added verification step |

### Strongly Recommended

| # | Finding | Plan Section Modified | Change Applied |
|---|---------|----------------------|----------------|
| 4 | `GOSOM_API_URL` missing from render.yaml envVars for review-radar-api | Task 1, render.yaml action | Added `- key: GOSOM_API_URL, sync: false` to review-radar-api service; added verification check |
| 5 | No direct gosom health check — server mode never independently verified | Task 1, verify section | Added `curl` directly to gosom endpoint to confirm server mode active |
| 6 | Empty reviews behaviour undocumented — no AC for 0-review response | Acceptance criteria | Added AC-7: 0 reviews → 200 with `{"reviews": []}`, not 500/502; added verify step |

### Deferred (Can Safely Defer)

| # | Finding | Rationale for Deferral |
|---|---------|----------------------|
| 1 | Typed Pydantic response model (`CompetitorScrapeResponse`) | gosom field names are unknown until verified against docs; premature typing would lock in wrong field names. Add in 03-02 or 03-03 once gosom contract is confirmed. |
| 2 | URL validation order leaks 422 to unauthenticated users | Pydantic runs before auth check → bad URL returns 422 before auth returns 401. Minor information disclosure (URL format validation exists), no sensitive data exposed. Fix requires moving validation into handler body. Not worth the complexity at this scale. |
| 3 | Internal API key for gosom service (auth between FastAPI and gosom) | Requires either a custom HTTP wrapper around the gosom binary or a forked gosom build. Out of scope for MVP. Addressed by private networking requirement instead. |

---

## 5. Audit & Compliance Readiness

**Evidence production**: The plan produces no persistent audit trail for individual competitor scrapes (no logging, no DB record of who scraped what URL). This is acceptable in 03-01 scope — rate limiting (03-05) will add the `competitor_scans` table which provides scan count evidence per user. No additional logging requirement for this plan.

**Silent failure prevention**: `_call_gosom` catches all httpx errors and re-raises as 502. After applying must-have #2, normalization failures also raise 502. No silent success paths that hide failures.

**Post-incident reconstruction**: If gosom is abused (open endpoint on free tier), the FastAPI access logs (Render's built-in logging) capture the request. However, the gosom service itself has no user attribution — scrape requests arrive from FastAPI's IP, not the end user's. This is an inherent limitation of the two-service architecture; documented as acceptable for MVP.

**Ownership**: `GOSOM_API_URL` is a `sync: false` env var, meaning it must be manually set in the Render dashboard. The operational owner must configure this on deploy. This is consistent with the existing pattern for secrets in this project.

---

## 6. Final Release Bar

**Must be true before this plan ships:**
- gosom Docker image builds and server mode confirmed working locally
- `Field(max_length=2000)` present on `url` (applied ✓)
- Normalization wrapped in try/except (applied ✓)
- render.yaml documents gosom private service requirement (applied ✓)
- GOSOM_API_URL in render.yaml envVars for review-radar-api (applied ✓)

**Risks remaining if shipped with applied fixes:**
- gosom service on Render free tier is publicly accessible — documented risk in render.yaml; migration to private networking required before commercial launch
- gosom API endpoint path and field names are speculative — executor must verify against gosom docs before finalizing `_call_gosom` implementation; plan explicitly flags this
- TOCTOU on unauthenticated gosom access: between checking premium status and calling gosom, the subscription could theoretically be cancelled; this is a read-only timing gap with no financial consequence at this scale

**Would I sign my name to this system with the applied fixes?** Yes, for an early-access MVP with pharmacy-owner scale traffic. The gosom private service migration is a hard prerequisite for commercial launch and is documented as such.

---

**Summary:** Applied 3 must-have + 3 strongly-recommended upgrades. Deferred 3 items.
**Plan status:** Updated and ready for APPLY.

---
*Audit performed by PAUL Enterprise Audit Workflow*
*Audit template version: 1.0*
