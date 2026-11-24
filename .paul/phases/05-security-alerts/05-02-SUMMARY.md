---
phase: 05-security-alerts
plan: 02
completed: 2026-11-24
description: "Owner landed npm lockfile, Python requirements and Next 15 upgrade; 4 postcss alerts remain open (bundled in Next)"
type: Summary
about: "Review Radar"
---

# Phase 5 Plan 02: Dependabot dependency fixes Summary

**Owner PRs #25, #27 and #28 cut the open Dependabot alerts from about 26 to 4. The 4 left are postcss copies bundled inside Next.**

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Alerts closed | Partial | 4 open alerts remain (below). Checked with the Dependabot API on 2026-11-24. All other alerts are closed. |

## Task Results

Task 1 (checkpoint:human-action, owner): done by the owner on their own PRs from `main`. Factory did not build it.

| PR | Merged | Change |
|----|--------|--------|
| #25 `chore: update deps and fix frontend warnings` | 2026-11-24 | `frontend/package-lock.json`: postcss, nanoid, ws, browserslist, source-map-js, postcss-selector-parser and other transitive bumps; frontend warning fixes |
| #27 `chore: fix python requirements` | 2026-11-24 | `backend/requirements.txt` and `requirements-dev.txt`: `python-multipart` 0.0.31, `python-dotenv` 1.2.2 |
| #28 `chore(frontend):upgrade-next-15` | 2026-11-24 | `next` 14 to 15.5.29; edits to `package.json`, lockfile, `tsconfig.json`, `next-env.d.ts`, auth callback route, dashboard pages, `lib/supabase/server.ts` and `subscription.ts` (Next 15 async request APIs) |

Stale duplicate Dependabot PRs #7 and #14: both CLOSED.

## Remaining open alerts

| Alert | Package | Severity | Patched in |
|-------|---------|----------|------------|
| 27 | postcss | medium | 8.5.10 |
| 46 | postcss | high | 8.5.12 |
| 47 | postcss | high | 8.5.18 |
| 48 | postcss | medium | 8.5.23 |

All four are in `frontend/package-lock.json` at `node_modules/next/node_modules/postcss` (8.4.31). Next 15.5.29 pins that copy, so the owner cannot raise it with a normal bump.

## Deviations from Plan

- Plan expected the Next 15 bump to be separate and manually tested. It was a separate PR (#28). This summary has no record of the manual test result: the owner did not report one.
- Alert count is not zero, so AC-1 is partial, not pass.

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Close 05-02 with 4 postcss alerts open | Alerts sit in the copy bundled in Next; no fix without a newer Next release or an npm `overrides` entry | Alerts stay open; logged as deferred |

## Next Phase Readiness

**Ready:** Phase 5 has 2 plans and 2 summaries. Code-scanning alerts closed (0 open) by 05-01; Dependabot down to 4.

**Concerns:**
- 4 postcss alerts stay open until a Next release bumps its bundled postcss, or the owner adds an `overrides` entry to `frontend/package.json` (protected path, owner only) and tests the build, or dismisses them with a reason.
- 05-01 follow-up: the tsc gate in `factory.config.yml` still needs `-p frontend` (deferred issue in STATE.md).
- PR #26 added the missing `url_validation` helper after 05-01 (the factory PR had left it out).

**Blockers:** None.

---
*Phase: 05-security-alerts, Plan: 02*
*Completed: 2026-11-24*
