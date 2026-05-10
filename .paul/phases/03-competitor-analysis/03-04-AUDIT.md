# Enterprise Plan Audit Report

**Plan:** .paul/phases/03-competitor-analysis/03-04-PLAN.md
**Audited:** 2026-05-10
**Verdict:** Conditionally acceptable → approved (findings applied)

---

## 1. Executive Verdict

**Conditionally acceptable → approved after applying findings.**

The architectural approach is correct: transparent fallback, identical response contract, AC-5 discriminates availability vs auth failures, optional key keeps gosom-only mode viable. Three gaps prevent unconditional sign-off and are addressed before approval.

Would I approve this for production after applying the findings? Yes.

---

## 2. What Is Solid

- **AC-5 non-502 bypass** — Re-raising non-502 HTTPExceptions correctly discriminates "gosom blocked" from "caller sent bad auth/URL". This is the critical correctness constraint and it is right.
- **Optional OUTSCRAPER_API_KEY** — Not added to `_REQUIRED_ENV_VARS` means gosom-only deployments need zero config change. The opt-in design is correct.
- **Same contract enforcement** — `{name, overall_rating, reviews[]}` returned regardless of scraper source. Gap endpoint, frontend, and rate limiter are genuinely unaffected.
- **`scraper_response_invalid` vs `scraper_unavailable` distinction** — Preserved in `_scrape_with_fallback`. gosom parsing failure (server responded but garbage) correctly does NOT trigger Outscraper fallback — Outscraper won't fix a malformed response.
- **Boundary protection** — Auth gate, gap endpoint, and `_call_gosom`/`_parse_gosom_csv` are explicitly out of scope.

---

## 3. Enterprise Gaps Identified

### G-1 — Exception masking in `_call_outscraper` (Must-Have)
The plan initially specified bare `except Exception` wrapping `_call_outscraper`. Since the function body itself raises `HTTPException(502)`, that exception is caught by `except Exception` and re-raised as a new `HTTPException(502)`. Functionally equivalent but: (a) breaks the established pattern from `_call_gosom` which uses `except HTTPException: raise` first, (b) creates a new exception object destroying the original traceback chain, (c) would silently mask any future `HTTPException` raised with a non-502 status from within the helper (e.g., if validation is added later).

### G-2 — Magic numbers 30 and 100 (Strongly Recommended)
The existing code has `_GOSOM_REQUEST_TIMEOUT = 30.0`, `_GOSOM_POLL_TIMEOUT = 180.0`, `_GOSOM_POLL_INTERVAL = 5.0` as module-level tuning constants. Inlining `30` (timeout) and `100` (review limit) directly into `_call_outscraper` breaks this pattern. An operator tuning timeouts for Render's constraints would need to hunt inside the function body rather than adjust a constant.

### G-3 — Silent Outscraper fallback (Strongly Recommended)
When `_scrape_with_fallback` switches from gosom to Outscraper, there is no log entry. In production:
- Outscraper is a paid-per-request commercial API — silent activation means invisible cost accumulation
- Systematic gosom blockage (e.g., IP ban) would be invisible until invoice arrives
- Post-incident reconstruction cannot determine when fallback started activating

A `logger.warning()` at the fallback decision point is the minimal acceptable observability signal.

---

## 4. Upgrades Applied to Plan

### Must-Have (Release-Blocking)

| # | Finding | Plan Section Modified | Change Applied |
|---|---------|----------------------|----------------|
| 1 | `except HTTPException: raise` missing before `except Exception` in `_call_outscraper` — exception masking, breaks `_call_gosom` pattern | Task 1 `<action>` | Added explicit `except HTTPException: raise` before `except Exception` wrapper with audit comment |

### Strongly Recommended

| # | Finding | Plan Section Modified | Change Applied |
|---|---------|----------------------|----------------|
| 1 | Magic numbers `30` (timeout) and `100` (review limit) break the established `_GOSOM_*` constants pattern | Task 1 `<action>` | Added `_OUTSCRAPER_REQUEST_TIMEOUT = 30.0`, `_OUTSCRAPER_REVIEW_LIMIT = 100`, `_OUTSCRAPER_REVIEWS_URL` as module-level constants; task action updated to reference them |
| 2 | No log warning when Outscraper fallback activates — invisible commercial spend and gosom blockage | Task 1 `<action>` | Added `logger.warning("gosom unavailable (502), falling back to Outscraper for %s", url)` in `_scrape_with_fallback` step 2; `import logging` / `logger = logging.getLogger(__name__)` specified |
| 3 | Verification checklist missing checks for new constants and logger | `<verification>` | Added 3 verification items: constants grep, logger.warning grep, except ordering check |

### Deferred (Can Safely Defer)

| # | Finding | Rationale for Deferral |
|---|---------|------------------------|
| 1 | Rating bounds validation on Outscraper response (rating could be outside 0–5) | gosom path has the same unvalidated float; consistent behaviour; GapReview Pydantic model validates at the gap endpoint boundary |
| 2 | `OUTSCRAPER_REVIEWS_URL` as env var instead of hardcoded constant | Outscraper is a stable commercial API; URL changes require SDK update not config change; acceptable for this release |
| 3 | `X-API-KEY` header visible in httpx debug logs | Requires explicit `HTTPX_LOG_LEVEL=debug` — not a default risk; document in security runbook if needed |

---

## 5. Audit & Compliance Readiness

**Defensible audit evidence:** After applying G-3, the `logger.warning` produces a timestamped log record whenever fallback activates. This is the minimum trace for post-incident reconstruction ("when did we switch to Outscraper?").

**Silent failure prevention:** The `scraper_unavailable` / `scraper_response_invalid` detail codes distinguish failure modes at the API surface. Both are returned as 502 to callers — the frontend's generic "Could not reach the scraper" message is appropriate.

**Cost accountability:** After applying G-3, operators can grep logs for `falling back to Outscraper` to measure fallback frequency and correlate with Outscraper billing.

**Ownership gap:** No metric/counter for fallback rate. Acceptable at this stage; 03-05 (rate limiting) provides a natural location to add counters.

---

## 6. Final Release Bar

**Must be true before this plan ships:**
- `except HTTPException: raise` present in `_call_outscraper` (G-1)
- `_OUTSCRAPER_REQUEST_TIMEOUT`, `_OUTSCRAPER_REVIEW_LIMIT` are module-level constants (G-2)
- `logger.warning()` fires when Outscraper fallback activates (G-3)

**Risks remaining after findings applied:**
- Outscraper JSON field names (`reviews_data`, `review_text`, `review_rating`) are based on documented API; actual field names should be verified on first live Outscraper request
- No integration test against real Outscraper API — relies on manual verification post-deploy

**Sign-off:** Yes, with findings applied this plan is production-appropriate for a pharmacy analytics SaaS at Phase 3 maturity.

---

**Summary:** Applied 1 must-have + 3 strongly-recommended upgrades. Deferred 3 items.
**Plan status:** Updated and ready for APPLY

---
*Audit performed by PAUL Enterprise Audit Workflow*
*Audit template version: 1.0*
