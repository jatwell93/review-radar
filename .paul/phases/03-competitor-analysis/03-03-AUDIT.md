# Enterprise Plan Audit Report

**Plan:** .paul/phases/03-competitor-analysis/03-03-PLAN.md
**Audited:** 2026-05-09
**Verdict:** Conditionally acceptable → approved after applying 4 fixes

---

## 1. Executive Verdict

**Conditionally acceptable.** The plan's architecture is fundamentally sound — auth/premium gate reuse, VADER+KeyBERT reuse from existing services, fire-and-forget gap call pattern, and soft error path are all appropriate production patterns. Three issues required remediation before sign-off:

1. `GapReview.text` unbounded — a premium user could POST crafted reviews with arbitrarily long texts to consume CPU/memory on the Render worker via VADER and especially KeyBERT (same DoS vector caught in 02-03 audit).
2. `GapRequest.overall_rating` and `GapReview.rating` had no bounds — malformed payloads render as "999.0 ★ Google" in production UI.
3. IIFE pattern `(() => { ... })()` in JSX — creates a new function on every render cycle and obscures delta logic from React DevTools.

All four remediation items have been applied to the plan. **Approved for APPLY.**

---

## 2. What Is Solid

- **Auth/premium gate reuse** — exact copy of the validated pattern from `scrape_competitor`. No new auth surface; consistent behaviour.
- **`max_length=500` on `GapRequest.reviews`** — total payload bounded before the audit caught the per-item text issue.
- **VADER import pattern** — `score_review` and `classify` imported directly from existing singleton; no per-request lexicon load.
- **Fire-and-forget gap call** — `void runGapAnalysis(data, token)` is the correct pattern. Scrape loading clears promptly; gap loading is independent. Intentional and documented in the plan.
- **Soft error design** — gap failure shows amber message without breaking scrape results. Correct — the scrape is slow and irreplaceable in this request context.
- **Own: null path** — handled gracefully at both API level (returns null) and frontend ("Upload your reviews to compare").
- **`.eq("user_id", str(user.id))` defence-in-depth** on Supabase query — consistent with Phase 2 pattern.
- **`extract_topics` internal exception handling** — the keybert_service catches all model failures; safe to call on empty input or with 500 reviews.
- **No new schema changes** — topics remain stateless per Phase 2 decision; gap results not persisted.

---

## 3. Enterprise Gaps Identified

**Gap A — Unbounded `GapReview.text` (HIGH)**
`GapReview.text: str = ""` had no `max_length`. The gap endpoint accepts `reviews: list[GapReview]` up to 500 items with no per-item text bound. A malicious premium user (or leaked JWT) could POST 500 reviews each with 100,000-character texts: `extract_topics` concatenates all texts into a single doc (`" ".join(...)`) before passing to KeyBERT's sentence-transformers encoder. Render worker CPU/memory would spike. This is the same pattern that was must-have in the 02-03 audit (`SaveAnalysisRequest.narrative max_length=2000`).

**Gap B — Unbounded `GapRequest.name` (MEDIUM)**
`GapRequest.name: str = ""` had no `max_length`. The name is returned in the response and rendered. While Tailwind `truncate` mitigates display, unbounded string inputs to API endpoints are a consistent risk surface.

**Gap C — No bounds on `overall_rating` / `GapReview.rating` (MEDIUM)**
`overall_rating: float = 0.0` and `rating: float = 0.0` had no `ge`/`le` constraints. A crafted payload could send `overall_rating=999.0`, rendering as `999.0 ★ Google` in the competitor card. For a commercial product with paying users, nonsense data renders damage trust even if they don't crash.

**Gap D — IIFE in JSX (LOW-MEDIUM)**
`{gapResult && !gapLoading && (() => { delta computation; return <JSX /> })()}` is non-idiomatic React:
- A new anonymous function is created on every render cycle.
- React DevTools shows an anonymous component, making debugging harder.
- Eslint react rules typically flag this pattern.
- `ComparisonCard` in `history/page.tsx` correctly precomputes `scoreDelta`, `deltaSign`, `deltaColor`, `arrow` before the return — same pattern required here.

---

## 4. Upgrades Applied to Plan

### Must-Have (Release-Blocking)

| # | Finding | Plan Section Modified | Change Applied |
|---|---------|----------------------|----------------|
| 1 | `GapReview.text` unbounded — VADER/KeyBERT DoS risk (same as 02-03 audit) | Task 1 `<action>` models | `text: str = Field(default="", max_length=2000)` |

### Strongly Recommended

| # | Finding | Plan Section Modified | Change Applied |
|---|---------|----------------------|----------------|
| 2 | `GapRequest.name` unbounded | Task 1 `<action>` models | `name: str = Field(default="", max_length=500)` |
| 3 | `overall_rating` and `rating` no bounds — nonsense star renders | Task 1 `<action>` models | `overall_rating: float = Field(ge=0, le=5)`, `rating: float = Field(ge=0, le=5)` |
| 4 | IIFE in JSX — non-idiomatic, new function per render, opaque to DevTools | Task 2 `<action>` gap panel | Replaced IIFE with `GapPanel` local component (delta variables precomputed before return); `{gapResult && !gapLoading && <GapPanel gapResult={gapResult} />}` |

### Deferred (Can Safely Defer)

| # | Finding | Rationale for Deferral |
|---|---------|------------------------|
| 5 | `own_data` Supabase fields not validated before return | `analyses` table was created with NOT NULL constraints (Phase 2). Field names selected explicitly in `.select()`. Low risk of null values in production. |
| 6 | React unmount cleanup for fire-and-forget gap call | React 18 does not error on setState after unmount. No crash risk; no memory leak in practice for a single-component page. |
| 7 | Delta label scale: VADER delta can reach ±2.0, reads oddly ("You are 2.00 ahead") | MVP-acceptable. VADER range is explained in context. Cosmetic concern, not correctness. Revisit in UX polish pass. |

---

## 5. Audit & Compliance Readiness

**Audit trail:** No gap analysis calls are logged or stored — this is by design (scope limit). The auth+premium gate is the access control. The 03-05 rate limiting plan will provide quota-based usage evidence. Acceptable for Phase 3 MVP.

**Silent failure prevention:** `extract_topics` catches all exceptions internally. VADER scoring is deterministic. `runGapAnalysis` catches all network and parse errors and surfaces them via `gapError` state. No silent failure paths identified.

**Post-incident reconstruction:** The gap endpoint has no server-side audit trail. If a user reports wrong numbers, the only evidence is the scrape result (which is also not stored). This is a known limitation of the stateless competitor analysis design. Not remediated here — 03-05 rate limiting may surface some usage data.

**Ownership/accountability:** Auth+premium gate provides user-level accountability. Consistent with existing Phase 2 and 03-01 patterns.

---

## 6. Final Release Bar

**Must be true before ship (all applied):**
- `GapReview.text` has `max_length=2000` — prevents VADER/KeyBERT DoS
- `GapRequest.overall_rating` has `ge=0, le=5` — prevents nonsense star renders
- `GapPanel` component uses precomputed variables (no IIFE) — correct React idiom

**Remaining risks after fixes applied:**
- No server-side audit trail for gap analysis calls (acceptable for Phase 3 MVP; 03-05 provides quota control)
- Delta label can reach "You are 2.00 ahead" if scores are extreme — cosmetic, not blocking

**Sign-off:** With the 4 applied fixes, I would approve this plan for production execution.

---

**Summary:** Applied 1 must-have + 3 strongly-recommended upgrades. Deferred 3 items.
**Plan status:** Updated and ready for APPLY

---
*Audit performed by PAUL Enterprise Audit Workflow*
*Audit template version: 1.0*
