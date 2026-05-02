# Enterprise Plan Audit Report

**Plan:** .paul/phases/01-free-tier-mvp/01-02-PLAN.md
**Audited:** 2026-05-02
**Verdict:** Conditionally acceptable → approved (all must-haves applied)

---

## 1. Executive Verdict

**Conditionally acceptable — approved after remediation.**

The plan is well-scoped, correctly stateless, and architecturally sound for its purpose. The VADER pipeline design is appropriate for the free tier. Three must-have issues and two strongly-recommended issues were identified and applied to the plan automatically. No issues remain that would block APPLY.

Would I approve this plan for production with the applied fixes? **Yes.**

---

## 2. What Is Solid

- **Stateless architecture** — No writes anywhere. Correct for Phase 1, zero data retention risk.
- **Module-level VADER instantiation** — Correctly specified to avoid per-request lexicon reload. This is the single highest-impact performance decision in the plan.
- **10MB file size limit** — Appropriate hard ceiling. Prevents trivial resource exhaustion.
- **Priority-ordered tolerant column detection** — Correct design for handling real-world Google review CSV exports that vary by locale and export version.
- **Pydantic response model with typed fields** — Strong contract for 01-03 and 01-04 consumers. The typed `Distribution`, `TimelineEntry`, and `ReviewItem` models prevent silent shape drift between plans.
- **ValueError → HTTPException(422) propagation pattern** — Clean, correct, FastAPI-idiomatic.
- **Empty row filtering in parser** — Correctly specified. Blank rows are a real occurrence in Google exports.

---

## 3. Enterprise Gaps Identified

### Gap 1 — UTF-8 BOM causes silent column detection failure (MUST-HAVE)

Windows Excel CSV exports universally prepend a UTF-8 BOM (`\ufeff`). When `csv.DictReader` reads with `utf-8` encoding, the BOM becomes embedded in the first column header: `"\ufefftext"` instead of `"text"`. The priority-ordered column detection finds no match, falls through all candidates, and raises "No identifiable review text column found" — even though the file is a perfectly valid Google review export. This affects the majority of real-world uploads by pharmacy owners (Windows users). The fix is `utf-8-sig` encoding, which strips BOM automatically.

### Gap 2 — python-dateutil transitive dependency is fragile (MUST-HAVE)

The original plan stated: *"python-dateutil is already a transitive dep of anthropic/httpx — do not add to requirements.txt."* This is an anti-pattern with real consequences. Transitive dependencies are not guaranteed to remain importable — upstream packages can drop them, pin them differently, or restructure their dependency graph. If dateutil is removed, the module-level `from dateutil.parser import parse` fails at **startup**, crashing the entire FastAPI application — not just the timeline feature. A missing explicit dependency makes this a silent runtime bomb. Fix: add `python-dateutil>=2.8` to requirements.txt.

### Gap 3 — Empty reviews list reaches aggregation unguarded (MUST-HAVE)

`run_sentiment_pipeline` operates on `reviews: list[dict]`. The CSV parser correctly raises `ValueError` for empty lists before the pipeline is reached. However, the pipeline itself has no guard. Python's `statistics.mean([])` raises `StatisticsError`; manual `sum(scores)/len(scores)` raises `ZeroDivisionError`. While the upstream guard should catch this, defensive programming is required in the aggregation function — the pipeline must be independently correct. An unexpected code path (future unit test, refactor that bypasses the router) should not cause a crash.

### Gap 4 — Unhandled exceptions leak internals (STRONGLY RECOMMENDED)

The router catches `ValueError` specifically, but unexpected exceptions (malformed CSV triggering csv module errors, unexpected VADER edge cases, future refactors) would surface as unhandled 500s with full FastAPI traceback. FastAPI's default exception handler returns the exception detail in the response body in debug mode and varies in production. A broad outer `except Exception` returning a sanitized "Analysis failed. Please check your file and try again." prevents information disclosure and provides a predictable contract.

### Gap 5 — top_reviews / bottom_reviews overlap undocumented (STRONGLY RECOMMENDED)

When `total_reviews < 10`, the same review appears in both `top_reviews` and `bottom_reviews`. When `total_reviews == 1`, the identical review is in both lists. This is the correct analytical behavior (there is literally only one best and worst review), but without documentation, the 01-03 developer will either treat it as a bug or add unnecessary deduplication logic. The overlap should be documented in code as intentional.

### Gap 6 — CSV injection in review text (CAN SAFELY DEFER)

Review text starting with `=`, `+`, `-`, `@` could inject formulas into downstream Excel exports. Not relevant for this plan (no export happens here). Must be addressed in 01-05.

### Gap 7 — No request correlation ID (CAN SAFELY DEFER)

No trace ID on requests. Makes debugging production issues harder. Not required for Phase 1 MVP.

### Gap 8 — File size check occurs post-read (CAN SAFELY DEFER)

The 10MB check occurs after `await file.read()` — the full file is already in memory. Streaming pre-check would be more efficient. Acceptable for MVP given the 10MB ceiling. Revisit if average upload size grows.

---

## 4. Upgrades Applied to Plan

### Must-Have (Release-Blocking)

| # | Finding | Plan Section Modified | Change Applied |
|---|---------|----------------------|----------------|
| 1 | UTF-8 BOM breaks column detection for Windows CSV exports | Task 1 → csv_parser.py action | Changed encoding from `utf-8` → `utf-8-sig` (BOM-stripping), fallback latin-1 |
| 2 | python-dateutil transitive dep crashes app at startup if removed upstream | Task 2 → sentiment.py action; frontmatter; boundaries | Added explicit `python-dateutil>=2.8` to requirements.txt; updated boundaries exception; updated files_modified |
| 3 | Empty reviews list unguarded in pipeline — ZeroDivisionError / StatisticsError | Task 2 → sentiment.py action | Added explicit guard returning safe empty defaults if reviews list is empty |

### Strongly Recommended

| # | Finding | Plan Section Modified | Change Applied |
|---|---------|----------------------|----------------|
| 4 | Broad exception catch missing — internal errors leak on unexpected failures | Task 1 → router action step 7 | Added broad `except Exception` handler returning sanitized 500 message |
| 5 | top/bottom overlap undocumented — 01-03 developer will treat as a bug | Task 2 → sentiment.py action | Added explicit note: overlap when total_reviews < 10 is intentional; document in code comment |

### Deferred (Can Safely Defer)

| # | Finding | Rationale for Deferral |
|---|---------|----------------------|
| 6 | CSV injection in review text | Only relevant when text is written to Excel/CSV. Flag for 01-05 export plan. |
| 7 | No request correlation ID | Debugging aid, not required for Phase 1 MVP. |
| 8 | File size check occurs post-read | 10MB ceiling makes this acceptable for MVP. Premature optimization. |

---

## 5. Audit & Compliance Readiness

**Evidence production:** The endpoint returns a deterministic structured response. Any analysis can be reproduced by re-uploading the same CSV. No state is written, so there is nothing to reconstruct from logs.

**Silent failure prevention:** Must-have fixes #1 (BOM) and #4 (broad exception handler) prevent the two most likely silent failure modes — files that look valid but aren't parsed correctly, and unexpected exceptions returning uncontrolled error payloads.

**Post-incident reconstruction:** Stateless architecture means there is no stored state to reconstruct. The CSV upload is not logged (correct — review data should not be persisted per project constraints). If a bug is reported, reproduction requires re-uploading the file.

**Ownership and accountability:** Single endpoint, single concern, no external side effects. Clear ownership.

**Would fail a real audit without fixes:**
- Gap 2 (transitive dep): A dependency audit would flag the undocumented runtime dependency.
- Gap 1 (BOM): A QA audit with real-world Windows exports would immediately find this.

---

## 6. Final Release Bar

**What must be true before this plan ships (all now addressed in plan):**
- UTF-8 BOM handling via `utf-8-sig` encoding
- `python-dateutil` explicit in requirements.txt and installed in venv
- Aggregation pipeline has empty list guard
- Router has broad exception handler

**Remaining risks after applied fixes:**
- Minor: file size check post-read (acceptable for 10MB MVP ceiling)
- Minor: no request correlation ID (acceptable for Phase 1)
- Deferred: CSV injection (must address in 01-05)

**Sign-off:** With the applied fixes, this plan is executable and production-safe for Phase 1 scope. The stateless architecture, typed response model, and explicit error contracts make this a solid foundation for the plans that depend on it (01-03, 01-04).

---

**Summary:** Applied 3 must-have + 2 strongly-recommended upgrades. Deferred 3 items.
**Plan status:** Updated and ready for APPLY.

---
*Audit performed by PAUL Enterprise Audit Workflow*
*Audit template version: 1.0*
