# Enterprise Plan Audit Report

**Plan:** `.paul/phases/02-paid-tier-core/02-02-PLAN.md`
**Audited:** 2026-05-03
**Verdict:** Conditionally acceptable → approved after fixes applied

---

## 1. Executive Verdict

**Conditionally acceptable** — approved after automatic remediation.

The core architecture is sound: Stripe hosted checkout, webhook-driven state updates via service-role Supabase writes, RLS-only reads from client, and clean separation between frontend auth (02-01) and payment state. However, three release-blocking gaps would cause real production incidents before the fixes were applied:

1. An active subscriber could be double-charged by clicking Upgrade again.
2. Payment failures would be invisible to the system — users would retain Premium access for the full Stripe retry window (up to 14 days) after their card declines.
3. A missing env var would produce a cryptic `AuthenticationError` on the first API call rather than a clear startup failure.

All three have been resolved in the plan. After the 3 must-have + 4 strongly-recommended fixes, this plan is approved for APPLY.

---

## 2. What Is Solid

- **Webhook signature validation correctly specified**: Raw body via `await request.body()` with explicit "do NOT use Pydantic model" instruction. `stripe.Webhook.construct_event()` with `SignatureVerificationError` catch is exactly right. This prevents spoofed events and replay attacks.
- **Service-role-only DB writes**: All subscription state mutations happen in the backend webhook using the service role key (bypasses RLS). No client-side insert/update policies. This is the correct trust boundary — client can only read its own row.
- **Upsert idempotency for checkout.session.completed**: Upsert keyed on `user_id` is idempotent for Stripe webhook retries. If Stripe fires the same event twice, the second upsert is a no-op.
- **Boundaries section is strong**: Explicitly protecting middleware (auth-only, no subscription hot-path queries), free tier routes, and auth pages. "Middleware stays auth-only" is the right call — querying Supabase on every request for subscription status would be expensive and fragile.
- **Checkpoint placement**: Human-action checkpoint correctly positioned between code tasks and verification. Env var setup and SQL execution are necessarily manual — this is the right gate.

---

## 3. Enterprise Gaps Identified

| # | Gap | Severity | Root Cause |
|---|-----|----------|------------|
| 1 | Double-billing: active subscriber can initiate new checkout | Must-have | No subscription status check before creating Stripe session |
| 2 | Payment failure invisible: `customer.subscription.updated` not handled | Must-have | Only `deleted` handled; `past_due`/`unpaid` transitions missed |
| 3 | Env vars validated at request time, not startup | Must-have | `stripe.api_key = os.getenv(...)` silently accepts `None` |
| 4 | `current_period_end` unavailable on session object | Strongly rec. | Must call `stripe.Subscription.retrieve()` to get it |
| 5 | `updated_at` not auto-maintained by DB trigger | Strongly rec. | Relies on manual `updated_at=now()` in Python code |
| 6 | `getSubscriptionStatus()` has no try/catch | Strongly rec. | Supabase query failure crashes dashboard page |
| 7 | Success page claims "You're Premium" before webhook fires | Strongly rec. | Webhook is async; Stripe redirects immediately after payment |

---

## 4. Upgrades Applied to Plan

### Must-Have (Release-Blocking)

| # | Finding | Plan Section Modified | Change Applied |
|---|---------|----------------------|----------------|
| 1 | Double-billing: checkout-session endpoint doesn't gate on existing active subscription | Task 1 action, AC section | Added: query `subscriptions` for `status='active'` before creating session; return 409 `{"error": "subscription_already_active"}` if active. Added AC-6. |
| 2 | Payment failure not reflected: `customer.subscription.updated` not handled | Task 1 action, human-action checkpoint, AC section | Added: `customer.subscription.updated` handler that updates `subscriptions.status` to Stripe's status value. Added `customer.subscription.updated` to production webhook event list. Added AC-7. |
| 3 | Startup env var validation missing | Task 1 action | Added: module-level validation loop over all 6 required env vars with `RuntimeError` on missing. Placed before route definitions. |

### Strongly Recommended

| # | Finding | Plan Section Modified | Change Applied |
|---|---------|----------------------|----------------|
| 1 | `current_period_end` not available on session object | Task 1 action | Added: `stripe.Subscription.retrieve(stripe_subscription_id)` call to get `sub.current_period_end`; added `datetime.utcfromtimestamp()` conversion note. Also added explicit note: unhandled Supabase exception → 500 (so Stripe retries). |
| 2 | `updated_at` not auto-maintained by Postgres trigger | Task 2 SQL | Added `set_updated_at()` trigger function + `subscriptions_set_updated_at` trigger to SQL block in Task 2. |
| 3 | `getSubscriptionStatus()` crashes on Supabase error | Task 2 subscription.ts action | Wrapped body in `try/catch`; returns `'inactive'` on error. Added `'past_due'` to `SubscriptionStatus` union type. |
| 4 | Success page copy implies Premium active before webhook fires | Task 2 success page action | Changed copy to "Payment received! Your account is being activated..." and explicitly noted not to say "You're Premium" on this page. |

### Deferred (Can Safely Defer)

| # | Finding | Rationale for Deferral |
|---|---------|------------------------|
| 1 | Rate limiting on `/stripe/checkout-session` endpoint | The 409 gate (must-have #1) limits damage to already-subscribed users. Unauthenticated abuse blocked by JWT validation. Rate limiting is a hardening concern for a later security phase. |
| 2 | Stripe Customer Portal for self-service cancellation | Already noted in SCOPE LIMITS. Users can cancel via Stripe email receipts or by contacting support. Add in a post-v0.2 UX pass. |
| 3 | Immutable subscription event log table | SOC 2 ideal: a `subscription_events` append-only table. The `subscriptions` row with `updated_at` is sufficient for v0.2 audit trail. Revisit before SOC 2 preparation. |
| 4 | Stripe idempotency keys on checkout session creation | Reduces duplicate sessions on network retries. Low-risk for v0.2 given the active-subscription gate. Add when implementing retry logic. |

---

## 5. Audit & Compliance Readiness

**Strengths:**
- `subscriptions` table has `created_at` and `updated_at` — sufficient audit trail for v0.2
- Webhook signature validation prevents spoofed events — correct for PCI boundary
- Service-role-only writes enforce a single trusted mutation path
- Startup env var validation (after fix) ensures configuration errors surface at deploy time, not randomly at runtime

**Remaining gaps (acceptable for v0.2):**
- No immutable event log — a future `subscription_events` table would allow full payment history reconstruction
- No alerting on webhook failures — Stripe Dashboard provides retry visibility, sufficient for now
- Success page timing (after fix) is UX-correct but a polling mechanism would be a better UX improvement (out of scope)

---

## 6. Final Release Bar

**Must be true before shipping:**
- [x] (applied) Active subscription gate on `/stripe/checkout-session`
- [x] (applied) `customer.subscription.updated` webhook handler
- [x] (applied) Startup-time env var validation with `RuntimeError`
- [x] (applied) `stripe.Subscription.retrieve()` for `current_period_end`
- [x] (applied) `getSubscriptionStatus()` try/catch
- [x] (applied) `updated_at` Postgres trigger
- [x] (applied) Success page copy is webhook-timing-safe

**Remaining risks (accepted):**
- No self-service cancel UI — users must contact support or use Stripe receipt email
- No rate limiting on checkout endpoint — low risk given auth + subscription gate
- No immutable event log — Stripe Dashboard is backup audit source

**Sign-off:** After the 3 must-have and 4 strongly-recommended fixes, I would approve this plan for production deployment to a v0.2 paid tier audience. The Stripe hosted checkout + webhook-driven state model is the industry-standard approach. The architecture is clean, the trust boundaries are correct, and the remaining deferred items are genuine v0.2 trade-offs, not gaps.

---

**Summary:** Applied 3 must-have + 4 strongly-recommended upgrades. Deferred 4 items.
**Plan status:** Updated and ready for APPLY

---
*Audit performed by PAUL Enterprise Audit Workflow*
*Audit template version: 1.0*
