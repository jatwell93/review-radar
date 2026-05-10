# Project State

## Project Reference

See: .paul/PROJECT.md (updated 2026-05-08)

**Core value:** Pharmacy owners get actionable, plain-English insights from their Google reviews in under 30 seconds.
**Current focus:** Milestone v0.3 complete — Phase 4 (Automation & Suite) is next

## Current Position

Milestone: v0.3 Competitor Analysis — ✅ COMPLETE
Phase: 4 of 4 (Automation & Suite) — Not started
Plan: Not started
Status: Ready to plan Phase 4
Last activity: 2026-05-10 — Phase 3 complete. All 5 plans shipped. Transitioning to Phase 4.

Progress:
- Milestone v0.1: [██████████] 100% ✅
- Milestone v0.2: [██████████] 100% ✅
- Milestone v0.3: [██████████] 100% ✅
- Phase 4: [░░░░░░░░░░] 0% (not started)

## Loop Position

Current loop state:
```
PLAN ──▶ APPLY ──▶ UNIFY
  ✓        ✓        ✓     [Loop complete — ready for next PLAN]
```

## Accumulated Context

### Decisions
| Decision | Rationale | Impact |
|----------|-----------|--------|
| 2026-05-09: Enterprise audit on 03-03-PLAN.md. Applied 1 must-have (GapReview.text max_length=2000) + 3 strongly-recommended (GapRequest.name max_length=500, overall_rating/rating ge=0 le=5, IIFE in JSX → GapPanel component). Deferred 3. Verdict: conditionally acceptable → approved. | Phase 3 | Gap endpoint hardened against DoS via unbounded text; frontend gap panel idiomatic |
| 2026-05-10: Enterprise audit on 03-04-PLAN.md. Applied 1 must-have (except HTTPException: raise before except Exception in _call_outscraper) + 3 strongly-recommended (_OUTSCRAPER_REQUEST_TIMEOUT/_REVIEW_LIMIT constants, logger.warning on fallback activation, verification checklist expanded). Deferred 3. Verdict: conditionally acceptable → approved. | Phase 3 | Outscraper fallback plan hardened against exception masking and invisible cost accumulation |
| 2026-05-09: Enterprise audit on 03-02-PLAN.md. Applied 1 must-have (res.json() try/catch + explicit return after error branch), 2 strongly-recommended (AbortController 240s timeout, Link vs a for internal nav). Deferred 2 (back-nav link, star bounds guard). Verdict: conditionally acceptable → approved. | Phase 3 | Frontend scrape flow hardened against silent failures and indefinite loading |
| 2026-05-08: Enterprise audit on 03-01-PLAN.md. Applied 3 must-have (URL max_length, normalization try/except, gosom access control docs) + 3 strongly-recommended (GOSOM_API_URL in render.yaml, gosom health verify, AC-7 empty reviews). Deferred 3. Verdict: conditionally acceptable → approved. | Phase 3 | gosom scraper plan hardened; private networking required before commercial launch |
| 2026-05-08: Enterprise audit on 03-05-PLAN.md. Applied 3 must-have (UTC datetime for month key, AC-5 failed-scrape quota protection, created_at audit column) + 4 strongly-recommended (Retry-After header, non-premium 403 verify, December overflow fix, TOCTOU documented). Deferred 2 (atomic increment, Retry-After in body). Verdict: conditionally acceptable → approved. | Phase 3 | Rate limiting plan strengthened for production correctness |
| 2026-05-08: Enterprise audit on 02-05-PLAN.md. Applied 1 must-have (Distribution | None typed model), 2 strongly-recommended (previous_score Field bounds ge=-1/le=1; defence-in-depth .eq user_id on browser Supabase query). Deferred 2 (magic number threshold, rate limiting). Verdict: conditionally acceptable → approved. | Phase 2 | NarrativeRequest validated against VADER range; cross-user data isolation defence-in-depth consistent with codebase pattern |
| 2026-05-08: Pre-save snapshot pattern. Fetch prior analysis before trySaveAnalysis fires to avoid race condition (current upload never fetched as "previous"). | Phase 2 plan 05 | Correct trend direction on first re-upload |
| 2026-05-08: Topics stateless (not stored). KeyBERT per-request only; no topics column in analyses table. | Phase 2 plan 04 | History page shows no topics; comparison skips topics |
| 2026-05-06: Enterprise audit on 02-03-PLAN.md. Applied 2 must-have (auto-save fires before narrative not after; SaveAnalysisRequest size validators) + 3 strongly-recommended (typed Pydantic models from analyze.py; insert ID extraction pattern; history query defense-in-depth .eq). Deferred 2 (per-user count limit, CSV filename storage). Verdict: conditionally acceptable → approved. | Phase 2 | Save timing bug closed; payload abuse prevented; type consistency enforced across pipeline and storage |
| Phase 1 = free tier MVP only | Validate core value before building paid machinery | All v1 work is stateless, no auth/DB |
| Claude Haiku included in free tier | Cost negligible (~$0.01–0.04/run), dramatically improves output quality | Requires ANTHROPIC_API_KEY from day one |
| Stateless architecture (Phase 1) | Removes auth complexity, zero barrier to try | No Supabase until Phase 2 |

### Git State
Last phase commit: fbca29e feat(02-paid-tier-core): Phase 2 complete — Paid Tier Core shipped
Branch: main
Feature branches merged: none

### Deferred Issues
| Issue | Origin | Effort | Revisit |
|-------|--------|--------|---------|
| Suite-wide auth consolidation | Planning | L | Phase 2 start |
| Bundle vs per-tool pricing decision | Planning | S | Before Phase 2 launch |
| PDF report visual design | Planning | M | Before 01-05 |
| gosom scraper ToS risk mitigation | Planning | S | Phase 3 start |
| Upgrade anthropic SDK in venv from 0.26.0 → >=0.40.0 | 01-04 execution | XS | Before 01-05 live test |
| Multi-location support | Phase 2 scope | M | Phase 3 or standalone plan |
| Google OAuth | Phase 2 scope | S | Future phase if demand |
| Per-user analysis count limit | 02-03 audit | S | Before scale |
| Render free tier KeyBERT OOM risk | Phase 2 plan 04 | XS | After deploy |

### Blockers/Concerns
None.

## Session Continuity

Last session: 2026-05-10
Stopped at: Phase 3 complete — all 5 plans unified
Next action: /paul:plan for Phase 4 (Automation & Suite)
Resume file: .paul/ROADMAP.md

---
*STATE.md — Updated after every significant action*
