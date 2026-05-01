# Roadmap: Review Radar

## Overview

Review Radar ships in four milestones: a stateless free-tier MVP that proves the core value (v0.1), a paid tier with auth, billing, and richer NLP (v0.2), competitor analysis with scraping and gap comparison (v0.3), and an automation layer with scheduled reports and n8n workflows (v1.0). Each milestone is independently shippable and revenue-generating before the next begins.

## Current Milestone

**v0.1 Free Tier MVP** (v0.1.0)
Status: Not started
Phases: 0 of 1 complete

## Phases

| Phase | Name | Plans | Status | Completed |
|-------|------|-------|--------|-----------|
| 1 | Free Tier MVP | 5 | Not started | - |
| 2 | Paid Tier Core | TBD | Not started | - |
| 3 | Competitor Analysis | TBD | Not started | - |
| 4 | Automation & Suite | TBD | Not started | - |

## Phase Details

### Phase 1: Free Tier MVP

**Goal:** A pharmacy owner can upload a CSV of Google reviews and within 30 seconds receive a sentiment score, trend chart, top/bottom reviews, and a plain-English Claude Haiku summary — all without creating an account. Live on Netlify + Render.

**Depends on:** Nothing (first phase)
**Research:** Likely (VADER integration, Claude Haiku prompt design, Next.js chart library selection, Render FastAPI deployment)
**Research topics:** vaderSentiment Python API, recharts vs chart.js in Next.js, FastAPI file upload handling, Render free-tier cold start behaviour

**Scope:**
- Next.js + FastAPI project scaffold with Tailwind
- CSV ingestion with validation and error handling
- VADER sentiment pipeline: per-review scoring + aggregation (overall score, distribution, timeline, top/bottom 5)
- Results dashboard: sentiment score card, trend chart, distribution chart, review list
- Claude Haiku narrative summary (plain-English, business-advisor tone)
- PDF and CSV export
- Production deployment: Netlify (frontend) + Render (backend)

**Plans:**
- [ ] 01-01: Project scaffold — Next.js App Router + Tailwind + FastAPI skeleton + CORS + env setup
- [ ] 01-02: CSV ingestion + VADER pipeline — upload endpoint, parse/validate CSV, VADER scoring, aggregation logic
- [ ] 01-03: Results dashboard — sentiment score, charts (trend + distribution), top/bottom reviews UI
- [ ] 01-04: Claude Haiku narrative — summary endpoint, prompt design, frontend integration
- [ ] 01-05: Export + deploy — PDF/CSV export, Netlify deploy, Render deploy, smoke test

### Phase 2: Paid Tier Core

**Goal:** Users can create accounts, subscribe via Stripe ($20/yr), and access KeyBERT topic extraction with persistent analysis history and month-over-month comparison.

**Depends on:** Phase 1 (working free tier foundation)
**Research:** Likely (Supabase auth + RLS setup, Stripe subscription webhooks, KeyBERT Python integration)

**Scope:**
- Supabase auth (email + Google OAuth)
- Stripe yearly subscription + webhook handling
- Persistent analysis storage (Supabase Postgres with RLS)
- KeyBERT topic extraction: top positive and negative themes
- Historical comparison UI
- Multi-location support

**Plans:**
- [ ] To be defined during /paul:plan for Phase 2

### Phase 3: Competitor Analysis

**Goal:** Paid users can enter a competitor's Google Maps URL, trigger a review scrape via gosom, and receive a side-by-side gap analysis against their own pharmacy.

**Depends on:** Phase 2 (auth + paid tier gating)
**Research:** Likely (gosom REST API deployment on Render, Docker configuration, Outscraper fallback API)

**Scope:**
- gosom scraper deployed as Render worker (Dockerised)
- Competitor URL input + scrape flow
- Gap analysis UI: side-by-side sentiment + theme comparison
- Outscraper fallback when gosom is blocked
- Rate limiting: 10 competitor scans/month per user

**Plans:**
- [ ] To be defined during /paul:plan for Phase 3

### Phase 4: Automation & Suite Integration

**Goal:** Paid users receive scheduled weekly re-analysis reports by email, with alerts when sentiment drops. Review Radar integrated into Pharm IQ suite billing.

**Depends on:** Phase 3
**Research:** Likely (n8n self-hosted or cloud, Pharm IQ suite Stripe consolidation)

**Scope:**
- n8n integration for scheduled jobs
- Weekly re-analysis + email delivery
- Sentiment drop alerts
- Pharm IQ suite billing consolidation ($60/yr bundle)

**Plans:**
- [ ] To be defined during /paul:plan for Phase 4

---
*Roadmap created: 2026-05-02*
*Last updated: 2026-05-02*
