# Enterprise Plan Audit Report

**Plan:** .paul/phases/01-free-tier-mvp/01-01-PLAN.md
**Audited:** 2026-05-02
**Verdict:** Conditionally Acceptable — 3 must-haves and 3 strongly-recommended findings identified and applied.

---

## 1. Executive Verdict

**Conditionally acceptable.** The scaffold plan is architecturally sound — correct service split, explicit boundaries, pinned dependencies, and concrete verification steps. However, three must-have gaps would cause real failures in subsequent plans or at production deployment: missing CORS preflight testing (breaks 01-02 uploads), no virtual environment specification (causes environment conflicts), and no git-tracking verification for env files (sets a dangerous pattern for real secrets). Six findings applied automatically. Plan is production-safe after remediation.

---

## 2. What Is Solid

- **Pinned dependency versions** in requirements.txt — prevents non-reproducible builds across environments and CI. The decision to pre-install vaderSentiment and anthropic in 01-01 is correct: it avoids per-plan reinstalls and catches version conflicts early.
- **CORS configured from env var** (not hardcoded) — origin allowlist read from `ALLOWED_ORIGINS` at startup means production config requires no code change, only env var update.
- **Explicit boundary section** — clearly separates what this plan does from what subsequent plans own. No feature creep risk from this plan.
- **Verification steps are concrete and runnable** — each check is a real curl command with expected output, not a vague "confirm it works."
- **Env files created from .env.example templates** — correct pattern for separating secrets from templates.

---

## 3. Enterprise Gaps Identified

**Gap 1 — No git-tracking verification for env files (CRITICAL)**
The plan creates `backend/.env` and `frontend/.env.local` but never verifies these are gitignored. The project .gitignore does cover these patterns, but a plan that creates sensitive files must explicitly verify they aren't tracked. If `.env` appears in `git status` as an untracked file and someone runs `git add .`, a real API key (added later) could be committed. One verification step closes this permanently.

**Gap 2 — No virtual environment specification (CRITICAL)**
Task 2 specifies `pip install -r requirements.txt` without mentioning a venv. Running pip globally on a developer machine installs packages system-wide, can conflict with other projects, and doesn't mirror Render's isolated environment. If a developer has a global package at a different version, `vaderSentiment==3.3.2` may silently be overridden. Venv is non-negotiable for Python backend projects.

**Gap 3 — CORS preflight not tested (CRITICAL for 01-02)**
The plan verifies CORS for `GET /health` only. The CSV upload in 01-02 will use `POST` with `Content-Type: multipart/form-data` — browsers send an OPTIONS preflight before this request. If FastAPI's CORSMiddleware isn't correctly handling preflight (it should, but should be verified), the upload in 01-02 will fail with a CORS error that's confusing to debug. Testing OPTIONS preflight in 01-01 ensures the scaffold is ready for 01-02.

**Gap 4 — No runtime version pinning (STRONG)**
No Node.js or Python version is specified anywhere. "Node 20+" and "Python 3.11+" are mentioned in the README prerequisites but not enforced. A developer with Node 18 or Python 3.9 will get subtly different behavior. `.nvmrc` and `.python-version` are the standard mechanism for this — both tools read them automatically.

**Gap 5 — No `backend/runtime.txt` for Render (STRONG)**
Render uses `runtime.txt` to detect the Python version for a web service. Without it, Render defaults to its own choice (currently Python 3.7 on free tier). This will cause 01-05 deployment failures due to incompatible syntax (f-strings, typing features, FastAPI requirements). Creating it in the scaffold costs nothing and eliminates a deployment surprise.

**Gap 6 — `package-lock.json` not addressed (STRONG)**
`npm install` generates `package-lock.json`. The plan doesn't mention committing it. Without a lock file in git, CI installs and Netlify builds resolve to whatever npm resolves at that moment — potentially a newer minor version that breaks the build. Lock files must be committed.

---

## 4. Upgrades Applied to Plan

### Must-Have (Release-Blocking)

| # | Finding | Plan Section Modified | Change Applied |
|---|---------|----------------------|----------------|
| 1 | `backend/.env` and `.env.local` not verified as gitignored | `<verification>` | Added `git status` check confirming neither env file appears as tracked |
| 2 | No virtual environment specification for Python | Task 2 `<action>` and `<verify>` | Added explicit venv creation (`python -m venv .venv`) before pip install in both action and verify steps |
| 3 | CORS OPTIONS preflight not tested; will break 01-02 POST uploads | Task 2 `<verify>` and `<verification>` | Added `curl -X OPTIONS` preflight test with Content-Type header; added to verification checklist |

### Strongly Recommended

| # | Finding | Plan Section Modified | Change Applied |
|---|---------|----------------------|----------------|
| 4 | No Node.js or Python version pinned | Task 1 `<action>`, frontmatter `files_modified`, `<verification>` | Added `.nvmrc` (node 20) in Task 1 action; added `.python-version` (3.11) in Task 2 action; both added to files_modified and verification checklist |
| 5 | No `backend/runtime.txt` for Render Python detection | Task 2 `<action>`, frontmatter `files_modified`, `<verification>` | Added `backend/runtime.txt` with `python-3.11.0`; added to files_modified and verification checklist |
| 6 | `package-lock.json` not committed | Task 1 `<verify>` | Added explicit note to stage `frontend/package-lock.json` after `npm install` |

### Deferred (Can Safely Defer)

| # | Finding | Rationale for Deferral |
|---|---------|----------------------|
| 7 | CORS `allow_methods: ["*"]` and `allow_headers: ["*"]` too permissive | Acceptable for local dev scaffold. Production CORS tightening belongs in 01-05 (deploy plan) where allowed origins, methods, and headers will be set for the Render → Netlify configuration. |
| 8 | `/health` doesn't distinguish liveness vs readiness | Acceptable for MVP. Render health check configuration will be addressed in 01-05. Separate `/ready` endpoint is a post-MVP concern. |
| 9 | `ANTHROPIC_API_KEY=placeholder` has no startup validation | Scaffold only — Claude is not invoked in this plan. Startup validation logic belongs in 01-04 when the Claude integration is built and the key is actually required. |

---

## 5. Audit & Compliance Readiness

**Evidence produced:** The verification checklist now produces 14 checkable pass/fail outcomes, each with a concrete command. This is sufficient for developer sign-off but not yet for audit evidence — no structured test output is captured. Phase 1 is pre-test infrastructure, so this is acceptable.

**Silent failure risk:** Gap 2 (no venv) was the highest silent failure risk — pip installing globally can succeed with wrong package versions and produce test output that passes locally but fails on Render. Now mitigated.

**Post-incident reconstruction:** The scaffold plan produces no application logic, so post-incident reconstruction risk is low. The key artifact is the SUMMARY.md, which this plan correctly specifies with package versions and CORS configuration details.

**Ownership:** Clear. Each task has one owner (the executor). Boundaries section explicitly names what must not change.

---

## 6. Final Release Bar

**What must be true before this plan ships:**
- All 14 verification checklist items pass, including the OPTIONS preflight CORS test
- `git status` confirms no env files are tracked
- `frontend/package-lock.json` is committed
- `backend/runtime.txt`, `.nvmrc`, and `.python-version` exist

**Remaining risks if shipped as-is (before audit fixes):**
- 01-02 CSV upload would fail with CORS error on first attempt (no preflight verification)
- Developer machines in inconsistent states (no venv enforcement)
- Potential env file exposure in git history

**Sign-off statement:** After the 6 applied fixes, I would approve this plan for execution. It is a scaffold — its production risk is low relative to feature plans — but the patterns it establishes (venv, env hygiene, CORS correctness) protect all subsequent plans in Phase 1.

---

**Summary:** Applied 3 must-have + 3 strongly-recommended upgrades. Deferred 3 items.
**Plan status:** Updated and ready for APPLY.

---
*Audit performed by PAUL Enterprise Audit Workflow*
*Audit template version: 1.0*
