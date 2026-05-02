# Review Radar

## What This Is

Review Radar is a pharmacy-focused sentiment analytics web application. Owners upload a CSV of their Google reviews and receive a structured breakdown of what customers love, what they're complaining about, and a plain-English narrative summary they can act on immediately — no data science knowledge required. Paid users can also scrape competitor reviews to identify gaps in their own offering and compare performance over time.

## Core Value

Pharmacy owners get actionable, plain-English insights from their Google reviews in under 30 seconds — surfacing what's working, what isn't, and where competitors are beating them.

## Current State

| Attribute | Value |
|-----------|-------|
| Type | Application |
| Version | 0.1.0 |
| Status | v0.1 Free Tier MVP shipped — Phase 2 next |
| Last Updated | 2026-05-02 |

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

### Active (In Progress)
None yet.

### Planned (Next)
- [ ] Phase 2: Supabase auth (email + Google OAuth)
- [ ] Phase 2: Stripe yearly subscription ($20/yr) + webhook handling
- [ ] Phase 2: Persistent analysis storage (Supabase Postgres with RLS)
- [ ] Phase 2: KeyBERT topic extraction — top positive and negative themes
- [ ] Phase 2: Historical comparison UI
- [ ] Phase 2: Multi-location support

### Out of Scope (v1)
- User accounts and authentication (Phase 2)
- KeyBERT topic extraction (Phase 2)
- Competitor scraping (Phase 3)
- Historical comparison (Phase 2)
- Scheduled re-analysis / n8n automation (Phase 4)
- Stripe billing (Phase 2)

## Target Users

**Primary:** Independent pharmacy owners and managers
- Not technical — needs plain-English output with zero jargon
- Time-poor — won't read 200 reviews individually
- Motivated by operational improvement and competitive awareness
- Already in the Pharm IQ ecosystem

**Secondary:** Small pharmacy chains (1–5 locations)

## Context

**Business Context:**
Review Radar is part of the Pharm IQ suite — a growing collection of pharmacy management tools including Expiry Mat, Heat Map, Basket & Script Calculator, and Pay Calculator. Freemium model: free tier (VADER, stateless) validates the concept; paid tier ($20/yr) adds persistence, KeyBERT, Claude, and competitor analysis.

**Technical Context:**
Frontend on Netlify (Next.js static), backend on Render (FastAPI Python), no shared infrastructure with other Pharm IQ tools yet. Phase 1 is entirely stateless — no database required. Claude Haiku API is the only paid external dependency in v1.

## Constraints

### Technical Constraints
- Python backend cannot run natively on Netlify — separate Render service required
- Claude Haiku API key required for narrative summary (ANTHROPIC_API_KEY env var)
- Google review CSV format may vary slightly — parser must be tolerant of minor format differences
- Free tier must be stateless — no writes to any database

### Business Constraints
- Phase 1 scope is free tier MVP only — paid features explicitly deferred
- Must pass plain-English test: a non-technical pharmacy owner understands the output without explanation
- Part of Pharm IQ brand — must be consistent with existing tool aesthetic

### Compliance Constraints
- Review data uploaded by users is not persisted (free tier) — no data retention risk in v1

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

## Success Metrics

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Analysis time (upload → results) | < 30 seconds | Not measured yet | Config ready — pending live deploy |
| Plain-English test | Non-technical owner understands output immediately | Not tested yet | Pending user testing after deploy |
| Free tier zero-friction | Works without creating an account | ✓ | Shipped — Phase 1 |
| Deployment | Live on Netlify + Render | Config shipped | netlify.toml + render.yaml committed; manual repo connect remaining |

## Tech Stack

| Layer | Technology | Notes |
|-------|------------|-------|
| Frontend framework | Next.js (App Router) | TypeScript throughout |
| Frontend styling | Tailwind CSS | Consistent with Pharm IQ suite |
| Frontend hosting | Netlify | Static + edge functions |
| Backend framework | FastAPI (Python) | REST API, auto-docs |
| Backend hosting | Render | Free tier initially |
| Sentiment analysis | VADER (vaderSentiment) | Free tier NLP |
| Topic extraction | KeyBERT | Paid tier only (Phase 2) |
| Qualitative narrative | Claude Haiku (Anthropic API) | ~$0.01–0.04 per analysis |
| Auth / Database | Supabase | Paid tier only (Phase 2) |
| Payments | Stripe | Paid tier only (Phase 2) |
| Competitor scraper | gosom/google-maps-scraper | Paid tier only (Phase 3) |

---
*PROJECT.md — Updated when requirements or context change*
*Last updated: 2026-05-02 after Phase 1 (Free Tier MVP)*
