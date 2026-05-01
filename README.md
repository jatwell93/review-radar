# Review Radar

**Part of the [Pharm IQ](https://pharmiq.com.au) suite**

Turn your Google reviews into actionable insights. Upload your pharmacy's reviews and get sentiment analysis, key themes, and plain-English recommendations — in under 30 seconds.

## What it does

- **Sentiment analysis** — overall score, trend over time, distribution breakdown
- **Theme extraction** — what customers are actually talking about
- **Plain-English summary** — business-advisor narrative, no jargon
- **Export** — download PDF or CSV report

## Stack

| Layer | Tech |
|-------|------|
| Frontend | Next.js (App Router) + Tailwind CSS |
| Backend | FastAPI (Python) |
| NLP | VADER + KeyBERT + Claude Haiku |
| Auth/DB | Supabase (paid tier) |
| Payments | Stripe |
| Hosting | Netlify (frontend) + Render (backend) |

## Project structure

```
review-radar/
├── frontend/          # Next.js app
├── backend/           # FastAPI service
├── PLANNING.md        # Full planning document
└── README.md
```

## Development

See `PLANNING.md` for full architecture, data flow, and phased build plan.

### Prerequisites
- Node.js 20+
- Python 3.11+
- Anthropic API key (for Claude Haiku)

### Quick start

```bash
# Frontend
cd frontend
npm install
npm run dev

# Backend
cd backend
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn main:app --reload
```

## Build phases

- [x] Phase 0 — Ideation & planning
- [ ] Phase 1 — Free tier MVP (CSV → VADER → charts → export)
- [ ] Phase 2 — Paid tier (auth, Stripe, KeyBERT, history)
- [ ] Phase 3 — Competitor analysis (scraper + gap UI)
- [ ] Phase 4 — Automation (n8n, scheduled reports)
