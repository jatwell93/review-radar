# Review Radar

## What This Is

Review Radar is a pharmacy-focused sentiment analytics web application. Owners upload a CSV of their Google reviews and receive a structured breakdown of what customers love, what they're complaining about, and a plain-English narrative summary they can act on immediately — no data science knowledge required. Paid users accumulate analysis history, view month-over-month trend comparisons, and see KeyBERT-extracted topic themes. Phase 3 will add competitor scraping and gap analysis.

## Core Value

Pharmacy owners get actionable, plain-English insights from their Google reviews in under 30 seconds — surfacing what's working, what isn't, and where competitors are beating them.

## Current State

| Attribute | Value |
|-----------|-------|
| Type | Application |
| Version | 0.2.0 |
| Status | v0.2 Paid Tier Core shipped — Phase 3 (Competitor Analysis) next |
| Last Updated | 2026-05-08 |

## Requirements

### Core Features

- CSV upload → VADER sentiment analysis → score, distribution, timeline, top/bottom 5 reviews
- Claude Haiku narrative: plain-English 3-4 sentence business-advisor summary
- Results dashboard with charts (sentiment score, trend, distribution)
- PDF and CSV export of analysis report
- Stateless free tier — no account required

### Validated (Shipped)
- ✓ CSV upload → VADER sentiment analysis → score, distribution, timeline, top/bottom 5 reviews — Phase 1
- ✓ Claude Haiku narrative: plain-English 3-4 sentence business-advisor summary — Phase 1
- ✓ Results dashboard with charts (sentiment score card, trend line, distribution bar) — Phase 1
- ✓ PDF export via browser print dialog (print:hidden on UI chrome) — Phase 1
- ✓ CSV export with UTF-8 BOM + formula-injection sanitization — Phase 1
- ✓ Stateless free tier — no account required — Phase 1
- ✓ Netlify + Render deployment configs (netlify.toml + render.yaml) — Phase 1
- ✓ Supabase email auth (sign-up, login, logout) with session middleware protecting /dashboard/* — Phase 2
- ✓ Stripe $20/yr subscription + checkout + webhook activation + dashboard premium badge — Phase 2
- ✓ Persistent analysis storage (Supabase Postgres with RLS, auto-save, /dashboard/history) — Phase 2
- ✓ KeyBERT topic extraction — top positive and negative keyword themes for premium users — Phase 2
- ✓ Month-over-month trend comparison: score delta in narrative + Latest vs Previous card in history — Phase 2

### Active (In Progress)
None yet.

### Planned (Next)
- [ ] Phase 3: Competitor review scraping via gosom (Google Maps URL → review data)
- [ ] Phase 3: Side-by-side gap analysis: own pharmacy vs competitor sentiment + themes
- [ ] Phase 3: Outscraper fallback when gosom is blocked
- [ ] Phase 3: Rate limiting — 10 competitor scans/month per user
- [ ] Phase 4: n8n scheduled weekly re-analysis + email delivery
- [ ] Phase 4: Sentiment drop alerts
- [ ] Phase 4: Pharm IQ suite billing consolidation ($60/yr bundle)

### Out of Scope (deferred)
- Multi-location support — scoped to Phase 2 but not implemented; no schema/UX designed; deferred to Phase 3 or standalone plan
- Google OAuth — email auth sufficient for launch; OAuth deferred to future phase if demand
- User accounts and authentication (shipped Phase 2)
- KeyBERT topic extraction (shipped Phase 2)
- Competitor scraping (Phase 3)
- Historical comparison (shipped Phase 2)
- Scheduled re-analysis / n8n automation (Phase 4)
- Stripe billing (shipped Phase 2)

## Target Users

**Primary:** Independent pharmacy owners and managers
- Not technical — needs plain-English output with zero jargon
- Time-poor — won't read 200 reviews individually
- Motivated by operational improvement and competitive awareness
- Already in the Pharm IQ ecosystem

**Secondary:** Small pharmacy chains (1–5 locations)

## Context

**Business Context:**
Review Radar is part of the Pharm IQ suite — a growing collection of pharmacy management tools including Expiry Mat, Heat Map, Basket & Script Calculator, and Pay Calculator. Freemium model: free tier (VADER, stateless) validates the concept; paid tier ($20/yr) adds persistence, KeyBERT, Claude trend narratives, and competitor analysis.

**Technical Context:**
Frontend on Netlify (Next.js static), backend on Render (FastAPI Python), Supabase for auth + Postgres. Phase 1 was stateless. Phase 2 added Supabase auth + RLS, Stripe subscriptions, KeyBERT (lazy-loaded singleton, ~300MB PyTorch), and trend narrative. Phase 3 adds a gosom scraper as a Render worker (Dockerised).

## Constraints

### Technical Constraints
- Python backend cannot run natively on Netlify — separate Render service required
- Claude Haiku API key required for narrative summary (ANTHROPIC_API_KEY env var)
- Google review CSV format may vary slightly — parser must be tolerant of minor format differences
- Free tier must be stateless — no writes to any database
- Render free tier (512MB RAM) may OOM with KeyBERT/sentence-transformers (~300MB PyTorch) — monitor after deploy

### Business Constraints
- Phase 1 scope is free tier MVP only — paid features explicitly deferred
- Must pass plain-English test: a non-technical pharmacy owner understands the output without explanation
- Part of Pharm IQ brand — must be consistent with existing tool aesthetic

### Compliance Constraints
- Review data uploaded by users is not persisted (free tier) — no data retention risk in v1
- Premium users: analysis data stored in Supabase with RLS (users access own rows only)

## Key Decisions

| Decision | Rationale | Date | Status |
|----------|-----------|------|--------|
| FastAPI over Flask | Auto-docs, async support, Pydantic validation, same lightweight footprint | 2026-05-02 | Active |
| Next.js over Angular | Faster to build, native Netlify deployment, smaller bundle | 2026-05-02 | Active |
| VADER for free tier | Tuned for informal/social text, no GPU required, free | 2026-05-02 | Active |
| Claude Haiku for narrative | Negligible cost (~$0.01–0.04/analysis), high quality plain-English output | 2026-05-02 | Active |
| Stateless free tier | Removes auth complexity, lowers barrier to try the product | 2026-05-02 | Active |
| Render for backend | Easy Python deploys, free tier for early stage | 2026-05-02 | Active |
| Separate narrative endpoint (not merged into /analyze/) | Keeps VADER pipeline fast; AI latency (~3-5s) would block chart render if merged | 2026-05-02 | Active |
| UTF-8 BOM on CSV output | Windows Excel opens without character corruption; Google review text is Unicode | 2026-05-02 | Active |
| print:hidden on export/reset row | Buttons should not appear in PDF/print output; dashboard content prints as-is | 2026-05-02 | Active |
| render.yaml sync:false for secrets | ANTHROPIC_API_KEY and ALLOWED_ORIGINS must not be committed to version control | 2026-05-02 | Active |
| Render healthCheckPath: /health | App-level monitoring vs TCP-only; catches crashed-but-not-exited process | 2026-05-02 | Active |
| @supabase/ssr (not supabase-js) for Next.js App Router | Correct cookie handling for SSR; getUser() validates JWT server-side | 2026-05-03 | Active |
| getUser() over getSession() in middleware | getSession() reads cookie without server validation; getUser() validates JWT | 2026-05-03 | Active |
| Server action for logout | Client-side signOut + router.push can flash stale state before redirect | 2026-05-03 | Active |
| load_dotenv() before router imports | Routers validate env vars at module level; wrong order causes RuntimeError | 2026-05-03 | Active |
| Auto-save fires before narrative fetch | Narrative takes 5-10s; firing early ensures save completes even if user closes tab | 2026-05-08 | Active |
| INSERT not UPSERT for analyses | Each save is a distinct historical record — idempotency not desired | 2026-05-08 | Active |
| all-MiniLM-L6-v2 for KeyBERT | Smallest semantic model (~90MB), balances quality vs Render memory budget | 2026-05-08 | Active |
| Topics stateless, not stored | Avoids DB schema changes; stateless per-request extraction sufficient for MVP | 2026-05-08 | Active |
| Pre-save snapshot for trend context | Fetch prior analysis before saving current — prevents race condition (current → previous) | 2026-05-08 | Active |
| Trend threshold ±0.02 | Signals meaningful change vs noise; deferred to config if tuning needed | 2026-05-08 | Active |

## Success Metrics

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Analysis time (upload → results) | < 30 seconds | Not measured yet | Config ready — pending live deploy |
| Plain-English test | Non-technical owner understands output immediately | Not tested yet | Pending user testing after deploy |
| Free tier zero-friction | Works without creating an account | ✓ | Shipped — Phase 1 |
| Deployment | Live on Netlify + Render | Config shipped | netlify.toml + render.yaml committed; manual repo connect remaining |
| Paid tier | Users can subscribe and access premium features | ✓ | Shipped — Phase 2 |

## Tech Stack

| Layer | Technology | Notes |
|-------|------------|-------|
| Frontend framework | Next.js (App Router) | TypeScript throughout |
| Frontend styling | Tailwind CSS | Consistent with Pharm IQ suite |
| Frontend hosting | Netlify | Static + edge functions |
| Backend framework | FastAPI (Python) | REST API, auto-docs |
| Backend hosting | Render | Free tier initially; Starter tier if KeyBERT OOMs |
| Sentiment analysis | VADER (vaderSentiment) | Free tier NLP |
| Topic extraction | KeyBERT + sentence-transformers | Paid tier; lazy-loaded singleton |
| Qualitative narrative | Claude Haiku (Anthropic API) | ~$0.01–0.04 per analysis |
| Auth / Database | Supabase | Email auth + Postgres + RLS |
| Payments | Stripe | $20/yr subscription |
| Competitor scraper | gosom/google-maps-scraper | Paid tier only (Phase 3) |

---
*PROJECT.md — Updated when requirements or context change*
*Last updated: 2026-05-08 after Phase 2 (Paid Tier Core)*
