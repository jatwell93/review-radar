# Review Radar — PLANNING.md

**Part of the Pharm IQ suite**
**Status:** Ideation complete — ready to build
**Last updated:** 2026-05-02

---

## 1. Problem Statement

Pharmacy owners accumulate Google reviews but lack time to read them all. The raw star rating hides the signal: *why* customers are happy or unhappy, which operational areas need work, and how competitors are positioning themselves. Reading 200 reviews is noise. Knowing that 34% of negative reviews mention wait times and 60% of positive ones mention staff friendliness is actionable.

---

## 2. Target Users

- Independent pharmacy owners and managers
- Small pharmacy chains (1–5 locations)
- Already exists within the Pharm IQ ecosystem — these users know the brand

**User maturity:** Not technical. Needs clean UX with no jargon. Insights must be plain-English.

---

## 3. Solution Overview

**Review Radar** is a sentiment analytics tool that turns Google review data into structured, actionable insights. It analyses a pharmacy's own reviews to surface what's working and what isn't, and lets paid users scrape competitor reviews to identify gaps in their own offering.

### Free Tier (no account required)
- Upload a CSV of Google reviews (exported from Google Business Profile)
- VADER sentiment analysis: overall score, sentiment distribution, timeline trend
- Top 5 most positive and most negative reviews surfaced
- Plain-English summary of key patterns
- Download PDF or CSV report — stateless, no data stored

### Paid Tier ($20/year, part of Pharm IQ suite)
- Everything in Free
- Account + persistent history (compare analyses over time)
- KeyBERT topic extraction: "what are people actually talking about?"
- Claude Haiku qualitative theming: narrative summary of patterns across all reviews
- Competitor analysis: enter a competitor's Google Maps URL → scrape their reviews → full analysis
- Side-by-side gap comparison: where are they outperforming you?
- Multi-location support
- Scheduled re-analysis (v2)
- Automated reports via email (v2)

---

## 4. Tech Stack

### Frontend
- **Framework:** Next.js (App Router)
- **Styling:** Tailwind CSS
- **Hosting:** Netlify (static + edge functions for lightweight proxying)
- **Language:** TypeScript throughout

### Backend
- **Framework:** FastAPI (Python)
- **Hosting:** Render (standard instance, always-on for paid tier)
- **Auth:** Supabase Auth (email/password + Google OAuth)
- **Database:** Supabase Postgres (Row Level Security for multi-tenant isolation)

### NLP Pipeline
| Layer | Tool | Tier |
|-------|------|------|
| Sentiment scoring | VADER | Free + Paid |
| Topic/keyword extraction | KeyBERT | Paid |
| Qualitative narrative | Claude Haiku API | Paid |

### Competitor Scraper
- **Tool:** `gosom/google-maps-scraper` — Go binary deployed as a separate Render worker service
- **Fallback:** Outscraper API (paid, ~$0.002/review) if gosom is blocked by Google
- **Rate limit:** 10 competitor scans/month per paid user (protects margins, easy to raise)
- **Tier:** Paid only

### Payments
- **Provider:** Stripe
- **Model:** Yearly subscription ($20/yr)
- **Suite bundle:** $60/yr for all Pharm IQ tools (v2 consideration)
- **Automation add-on:** +$5/yr (v2)

---

## 5. Data Flow

### Free (stateless)
```
User uploads CSV
  → Next.js sends to FastAPI /analyse
    → Parse reviews
    → VADER scores each review
    → Aggregate: overall score, distribution, timeline, top/bottom 5
    → Claude Haiku: 3-sentence plain-English summary
  → Return JSON to frontend
  → Render charts + summary
  → User downloads PDF/CSV
  → Nothing stored
```

### Paid (persistent)
```
Authenticated user uploads CSV (or triggers competitor scrape)
  → FastAPI /analyse (full pipeline)
    → VADER + KeyBERT + Claude Haiku
    → Competitor scraper service (if competitor URL provided)
  → Results stored in Supabase (linked to user, timestamped)
  → Frontend renders full dashboard
  → Historical comparisons pulled from Supabase on demand
```

---

## 6. NLP Output Specification

The goal is **actionable, plain-English insights**. Every output must answer a real question.

| Output | Answers | Tool |
|--------|---------|------|
| Overall sentiment score (0–100) | "How are we doing overall?" | VADER |
| Sentiment trend (last N reviews) | "Are things getting better or worse?" | VADER |
| Top positive themes | "What do customers love?" | KeyBERT |
| Top negative themes | "What keeps coming up as a problem?" | KeyBERT |
| Representative quotes per theme | "Show me examples" | Extraction |
| Narrative summary | "Tell me the story in plain English" | Claude Haiku |
| Competitor gap analysis | "Where are they beating us?" | All of the above, compared |

**Claude Haiku prompt design (example):**
```
You are analysing Google reviews for a pharmacy.
Based on the following sentiment data and topics, write a 3-4 sentence
plain-English summary that a non-technical pharmacy owner can act on.
Focus on what is working, what needs improvement, and one specific
recommendation. Do not use jargon or scores — speak like a business advisor.

Data: {json_summary}
```

---

## 7. Google Review CSV Format

Google Business Profile allows owners to export reviews. Expected columns:
- `reviewer_name`
- `rating` (1–5)
- `review_text`
- `date`

The app should be tolerant of minor format variations and surface clear error messages for malformed files.

---

## 8. Competitor Scraper Architecture

**Service:** `gosom/google-maps-scraper` deployed as a Render worker
**Input:** Google Maps URL of competitor pharmacy
**Output:** Array of `{rating, text, date}` objects
**Communication:** Internal REST call from FastAPI → scraper service
**Error handling:**
- If scraper returns 0 results or errors → surface friendly message to user
- Auto-fallback to Outscraper API (configurable env flag)
- Scraper errors do not crash the main analysis — graceful degradation

**Deployment note:** The Go binary needs a Dockerfile on Render. The `gosom` repo supports Docker deployment.

---

## 9. Pricing & Margin Model

| Users | Revenue/yr | Infra (est.) | Claude API (heavy) | Net margin |
|-------|-----------|--------------|---------------------|------------|
| 50 | $1,000 | ~$300 | ~$50 | ~$650 (65%) |
| 200 | $4,000 | ~$400 | ~$200 | ~$3,400 (85%) |
| 500 | $10,000 | ~$600 | ~$500 | ~$8,900 (89%) |

**Margin protection levers:**
- Rate limit competitor scans (10/month default)
- Rate limit Claude calls (per-user monthly quota, raise on request)
- Use Haiku not Sonnet for all automated analysis
- Render free tier for early stage, upgrade as revenue warrants

---

## 10. Pharm IQ Suite Context

Review Radar sits inside the Pharm IQ brand alongside:
- **Expiry Mat** — expiry date manager
- **Heat Map** — sales/customer heat map
- **Basket & Script Calculator** — basket size and prescription calculator
- **Pay Calculator** — staff pay calculator

**Suite considerations:**
- Shared auth (Supabase) across tools eventually
- Shared billing (Stripe, one subscription covers the suite)
- Consistent design system (Tailwind + shared component library)
- Single landing page for Pharm IQ suite with per-tool CTAs

---

## 11. Phased Build Plan

### Phase 1 — Free Tier MVP
- [ ] Project scaffold: Next.js + FastAPI + Tailwind
- [ ] CSV upload and parsing (with validation)
- [ ] VADER pipeline + aggregation logic
- [ ] Results dashboard: score, charts, top/bottom reviews
- [ ] Claude Haiku narrative summary
- [ ] PDF/CSV export
- [ ] Deploy: Netlify (frontend) + Render (backend)

### Phase 2 — Paid Tier Core
- [ ] Supabase auth (email + Google OAuth)
- [ ] Stripe yearly subscription integration
- [ ] Persistent analysis storage (Supabase)
- [ ] KeyBERT topic extraction
- [ ] Historical comparison UI
- [ ] Multi-location support

### Phase 3 — Competitor Analysis
- [ ] gosom scraper service deployment (Render worker, Dockerised)
- [ ] Competitor URL input + scrape flow
- [ ] Gap analysis UI: side-by-side comparison
- [ ] Fallback to Outscraper on scraper failure

### Phase 4 — Automation (v2)
- [ ] n8n integration for scheduled jobs
- [ ] Weekly re-analysis + email delivery
- [ ] "Sentiment dropped" alerts
- [ ] Pharm IQ suite billing consolidation

---

## 12. Open Questions / Deferred Decisions

- **Suite-wide auth:** Will Review Radar share a Supabase project with other Pharm IQ tools, or run independently until a consolidation phase?
- **Bundle pricing:** $60/yr suite vs $20/yr per tool — needs a landing page strategy decision before launch
- **PDF report design:** What does the ideal one-page report look like? Worth sketching before building
- **Multi-location UX:** How does a user with 3 pharmacy locations manage separate review sets? Single dashboard or per-location views?
- **gosom scraper ToS risk:** Monitor; have Outscraper API key ready as env var from day one

---

## 13. Success Criteria (MVP)

- A pharmacy owner can upload a CSV of their Google reviews and within 30 seconds receive a sentiment score, a chart, the top themes, and a plain-English summary they can act on
- The free tier works without creating an account
- The insight output passes a plain-English test: show it to a non-technical pharmacy owner and they understand it immediately without explanation
