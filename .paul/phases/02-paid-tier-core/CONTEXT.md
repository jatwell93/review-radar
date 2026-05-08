---
phase: 02-paid-tier-core
type: context
status: discuss-complete
created: 2026-05-02
---

# Phase 2: Paid Tier Core — Discussion Context

## Vision Statement

A pharmacy owner logs in to their account, navigates to the premium section, runs an analysis, and compares it to previous runs using side-by-side score cards. KeyBERT topics surface what customers keep talking about. An enhanced Claude narrative helps them understand what changed and take action — not just describe their score, but plan from it.

## User Story

> As a pharmacy owner, I log in to my Review Radar account, upload this month's reviews, and immediately see how my score changed since last time. I can see what topics my customers keep mentioning (good and bad). Claude tells me what's improved, what's still a problem, and gives me 2-3 things to focus on this month.

## Goals

1. **Auth + gating** — email login via Supabase; premium section only accessible to active $20/yr subscribers
2. **Persistent history** — every analysis is saved to the user's account; they can return and see past runs
3. **Side-by-side comparison** — current run vs most recent previous run; score cards, distribution delta
4. **KeyBERT topics** — the primary new analytical feature; surfaces top positive and negative themes as keyword clusters extracted from review text
5. **Planning-oriented Claude narrative** — compares this run to the previous run, frames output as actionable: what changed, what to focus on, 2-3 suggested actions

## Confirmed Decisions

| Decision | Detail |
|----------|--------|
| Auth provider | Supabase (email only — no Google OAuth for now) |
| Single app | No white-labelling or per-pharmacy subdomains |
| Subscription model | Stripe $20/yr — existing roadmap |
| Comparison scope | Current vs previous run only — no competitor context |
| Competitor context | Deferred to Phase 3 (scraper required) |
| Multi-location | Deferred — single account, single pharmacy for Phase 2 |
| KeyBERT placement | Premium only — free tier gets VADER + Claude summary, paid adds KeyBERT topics |

## Deferred Items

| Item | Phase |
|------|-------|
| Competitor score comparison in Claude narrative | Phase 3 |
| Multi-location support | Phase 2+ or Phase 3 |
| Google OAuth | Later (email sufficient for launch) |
| Historical trend beyond current vs last | Later (history list will show all runs) |

## Out of Scope for Phase 2

- Competitor scraping (Phase 3)
- Scheduled/automated re-analysis (Phase 4)
- n8n integration (Phase 4)
- Bundle pricing with Pharm IQ suite (Phase 4)

## Proposed Plan Breakdown

| Plan | Name | Scope |
|------|------|-------|
| 02-01 | Auth | Supabase project setup, email auth, session middleware, protected routes |
| 02-02 | Payments | Stripe $20/yr subscription, checkout flow, webhook handling, premium gating middleware |
| 02-03 | History | Supabase Postgres schema, RLS policies, save analysis on completion, history list UI |
| 02-04 | KeyBERT | Python KeyBERT service, FastAPI endpoint, topic display in premium dashboard |
| 02-05 | Compare + Narrative v2 | Side-by-side score cards (current vs last), distribution delta, enhanced Claude prompt (comparison + planning framing) |

## Architecture Notes

- **Backend**: FastAPI on Render — all new endpoints added to existing service; no new service needed for Phase 2
- **Database**: Supabase Postgres (new) — analyses table with user_id foreign key; RLS ensures users see only their own data
- **Auth flow**: Supabase client-side SDK in Next.js; JWT passed to FastAPI for authenticated endpoints; middleware on premium routes
- **KeyBERT**: Python package installed on Render backend; runs in-process (no separate worker needed at free-tier scale); returns top N topic clusters per sentiment polarity
- **Stripe**: Checkout Session flow (not Elements); webhook on FastAPI to update subscription status in Supabase; premium check reads subscription_status from DB

## Success Criteria for Phase 2

- [ ] Owner can sign up, log in, and access their account
- [ ] Non-subscribers see a paywall when navigating to premium section
- [ ] Subscribers can run analyses that are saved and retrievable
- [ ] Premium dashboard shows KeyBERT topics alongside existing VADER charts
- [ ] Running a second analysis shows a side-by-side comparison to the previous run
- [ ] Claude narrative explicitly references what changed and suggests 2-3 actions

---
*Phase 2 discussion complete — ready for /paul:plan*
