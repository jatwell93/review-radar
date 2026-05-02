# Enterprise Plan Audit Report

**Plan:** `.paul/phases/01-free-tier-mvp/01-05-PLAN.md`
**Audited:** 2026-05-02
**Verdict:** Conditionally acceptable → approved (after fixes applied)

---

## 1. Executive Verdict

**Conditionally acceptable — approved after 5 upgrades applied.**

The plan is structurally sound: scoped to config files and a frontend component, no new dependencies, stateless architecture maintained. However, two must-have bugs in the CSV export implementation would cause silent failures in production (Safari downloads) and data corruption for the target user (pharmacy owners on Windows Excel). Three strongly-recommended items would leave a health-blind backend and undocumented UX degradation on free tier. These have been applied. Plan is approved for APPLY.

---

## 2. What Is Solid

- **Frontend-only export**: Correct decision. No backend PDF/CSV endpoint means no server state, no storage, no new attack surface. Consistent with stateless Phase 1 architecture.
- **`window.print()` for PDF**: Zero-dependency, zero-maintenance, correct for MVP. Print CSS + `print:hidden` Tailwind is the right approach.
- **`sync: false` on secrets in render.yaml**: Correct. API key and ALLOWED_ORIGINS never touch version control. This is the expected pattern for IaC secret management.
- **`base = "frontend"` subdirectory Netlify config**: Correct. Netlify's Next.js auto-detection works from a subdirectory base with this config.
- **BOM concern identified for input in 01-02 applied consistently**: The prior BOM fix to the CSV parser is the right standard to apply on the output side too — now remediated.
- **`autonomous: true` on all tasks**: Appropriate. No tasks require human checkpoints; all are deterministic file creates/edits.

---

## 3. Enterprise Gaps Identified

### Gap 1 — CSV UTF-8 BOM missing (Must-Have)
The plan's original `new Blob([csv], ...)` call had no BOM prefix. Windows Excel opens UTF-8 CSV files without BOM and defaults to Windows-1252 encoding, corrupting any non-ASCII characters in review text. The prior plan (01-02) enforced BOM handling on CSV input parsing — the same compliance standard must apply to CSV output. Pharmacy owners running Windows are the primary target persona.

### Gap 2 — CSV `link.click()` cross-browser failure (Must-Have)
The original plan created a detached `<a>` element (`document.createElement('a')`) and called `.click()` on it without appending to `document.body`. Safari requires the element to be in the DOM for programmatic click to function. Additionally, `URL.revokeObjectURL(url)` was called synchronously immediately after `.click()` — the browser may not have queued the download before the blob URL was invalidated, causing a failed download on slower browsers with no visible error.

### Gap 3 — CSV formula injection (Strongly Recommended)
Review text is user-originated data (Google review content). Cells beginning with `=`, `+`, `-`, `@`, `\t`, or `\r` are interpreted as formulas by Excel and LibreOffice Calc. A review beginning with `=HYPERLINK("http://evil.com","click here")` would execute without warning when the pharmacy owner opens the CSV. This is a documented OWASP injection category. While risk is low (pharmacy owns their own data), reports are often forwarded to accountants, partners, or franchisors — broadening the exposure surface.

### Gap 4 — `healthCheckPath` absent from render.yaml (Strongly Recommended)
The FastAPI backend already exposes `GET /health` returning `{"status": "ok", "service": "review-radar-api"}`. Without `healthCheckPath` in render.yaml, Render performs TCP-level health checks only — a process that has entered an error state but hasn't exited (e.g., due to exhausted ANTHROPIC_API_KEY quota causing uncaught async exceptions in Starlette) would not trigger automatic restart. This leaves the service silently broken for all users until manually restarted.

### Gap 5 — Render free tier cold start undocumented (Strongly Recommended)
Render free tier services spin down after 15 minutes of inactivity. The first request after idle triggers a cold start with 30-60 seconds of latency before uvicorn is ready to serve. The PROJECT.md core value statement is "actionable insights in under 30 seconds." A cold start blows through that entire SLA before the file is even uploaded. This conflict is not acknowledged anywhere in the plan, no mitigation is noted, and no operator decision is documented.

---

## 4. Upgrades Applied to Plan

### Must-Have (Release-Blocking)

| # | Finding | Plan Section Modified | Change Applied |
|---|---------|----------------------|----------------|
| 1 | UTF-8 BOM missing in CSV Blob | Task 1 action — CSV implementation | Changed `new Blob([csv], ...)` to `new Blob(["\uFEFF" + csv], ...)` with explanatory comment referencing 01-02 BOM standard |
| 2 | `link.click()` cross-browser bug — detached element + synchronous revokeObjectURL | Task 1 action — CSV implementation | Added `document.body.appendChild(link)` before click, `document.body.removeChild(link)` after, and deferred `revokeObjectURL` in `setTimeout(() => ..., 100)` |

### Strongly Recommended

| # | Finding | Plan Section Modified | Change Applied |
|---|---------|----------------------|----------------|
| 3 | CSV formula injection — user review text not sanitized against spreadsheet formula triggers | Task 1 action — CSV implementation | Added `sanitizeCell()` helper that escapes double quotes AND prepends a space to cells beginning with `=`, `+`, `-`, `@`, `\t`, or `\r` |
| 4 | `healthCheckPath` absent from render.yaml | Task 3 action — render.yaml template | Added `healthCheckPath: /health` to service definition with explanatory comment |
| 5 | Render free tier cold start conflict with product SLA | Task 3 action — render.yaml template | Added inline comment documenting 15-min spin-down behavior, 30-60s cold start impact, and upgrade path |

### Deferred (Can Safely Defer)

| # | Finding | Rationale for Deferral |
|---|---------|----------------------|
| 6 | Netlify security headers (CSP, X-Frame-Options, X-Content-Type-Options) | No auth tokens, no session state, no sensitive data stored in frontend. Stateless SPA with no persistent user context. Low attack surface for Phase 1. Add before Phase 2 when auth is introduced. |
| 7 | GDPR/PII notice on CSV export | Pharmacy owners are downloading their own business data (Google reviews they are the controller of). No personal health data. Deferred to Phase 2 when user sessions and stored reports are introduced. |

---

## 5. Audit & Compliance Readiness

**Evidence produced:** All export actions are client-side with no server logging — acceptable for stateless Phase 1. No server-side audit trail is required or appropriate until Phase 2 introduces auth.

**Silent failure prevention:**
- Must-have fix #2 (link.click) eliminates the silent download failure on Safari.
- Strongly recommended fix #4 (healthCheckPath) enables Render to detect and restart crashed services.
- The free-tier cold start (fix #5) is now documented — operators know what to expect and can plan accordingly.

**Post-incident reconstruction:** CSV filename is fixed (`review-radar-report.csv`) with no timestamp — operators cannot distinguish exports by time. Low risk for Phase 1 (no stored sessions), acceptable. Timestamp in filename is a Phase 2 concern.

**Ownership:** Task actions are specific enough to implement without ambiguity. Secrets management uses Render/Netlify dashboard — correct for free tier IaC without a vault.

**What would fail a real audit before fixes:** The cross-browser download bug (Gap 2) would produce intermittent Safari failures with no visible error. The missing BOM (Gap 1) would corrupt pharmacy owner exports on Windows. These are production-observable defects, not hypotheticals.

---

## 6. Final Release Bar

**What must be true before this plan ships (all now applied):**
- UTF-8 BOM prepended to CSV Blob output
- `link.click()` uses DOM-appended element with deferred `revokeObjectURL`
- Formula injection sanitization applied to review text cells
- `healthCheckPath: /health` present in render.yaml
- Render cold start limitation documented in render.yaml

**Remaining risks after fixes:**
- Recharts SVG charts may render blank in Safari/Firefox print preview (noted as "acceptable for MVP" in plan — this is a known, documented limitation, not a hidden risk)
- Render free tier cold start is documented but not mitigated — operational decision deferred to the operator

**Sign-off:** I would approve this plan for production execution with the 5 upgrades applied. The remaining deferred items are appropriate for Phase 1 scope. No hidden blocking risks remain.

---

**Summary:** Applied 2 must-have + 3 strongly-recommended upgrades. Deferred 2 items.
**Plan status:** Updated and ready for APPLY

---
*Audit performed by PAUL Enterprise Audit Workflow*
*Audit template version: 1.0*
