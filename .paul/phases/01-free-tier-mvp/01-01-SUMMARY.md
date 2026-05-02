---
plan: 01-01
phase: 01-free-tier-mvp
status: complete
executed: 2026-05-02
---

# 01-01 SUMMARY: Project Scaffold

## What Was Built

### Directory Structure
```
review-radar/
├── .nvmrc                        # Node 20 pin
├── .python-version               # Python 3.11 pin
├── frontend/
│   ├── package.json              # Next.js 14 + Tailwind + recharts
│   ├── package-lock.json         # Committed for reproducible CI
│   ├── next.config.mjs           # Minimal Next.js config (note: .mjs, not .ts — v14 limitation)
│   ├── tailwind.config.ts        # Pharm IQ palette (slate/emerald/rose)
│   ├── postcss.config.mjs        # tailwindcss + autoprefixer
│   ├── tsconfig.json             # @/* path alias → src/*
│   ├── .env.local                # NEXT_PUBLIC_API_URL=http://localhost:8000 (gitignored)
│   └── src/app/
│       ├── layout.tsx            # Inter font, nav bar (brand + "Part of Pharm IQ")
│       ├── page.tsx              # Placeholder: "Review Radar" heading + upload-zone div
│       └── globals.css           # @tailwind base/components/utilities
└── backend/
    ├── main.py                   # FastAPI app + CORSMiddleware + GET /health
    ├── requirements.txt          # Pinned: fastapi, uvicorn, dotenv, VADER, anthropic, httpx
    ├── runtime.txt               # python-3.11.0 (Render runtime detection)
    └── .env                      # ANTHROPIC_API_KEY + ALLOWED_ORIGINS (gitignored)
```

## Package Versions Pinned

### Frontend
| Package | Version |
|---------|---------|
| next | 14.2.3 |
| react / react-dom | ^18.3.1 |
| tailwindcss | ^3.4.3 |
| typescript | ^5.4.5 |
| recharts | ^2.12.7 (pre-installed for 01-03) |

### Backend
| Package | Version |
|---------|---------|
| fastapi | 0.111.0 |
| uvicorn[standard] | 0.29.0 |
| python-multipart | 0.0.9 |
| python-dotenv | 1.0.1 |
| vaderSentiment | 3.3.2 (pre-installed for 01-02) |
| anthropic | 0.26.0 (pre-installed for 01-04) |
| httpx | 0.27.0 |

## CORS Configuration

- Middleware: `fastapi.middleware.cors.CORSMiddleware`
- Origins: read from `ALLOWED_ORIGINS` env var (comma-split), defaults to `http://localhost:3000`
- allow_credentials: `True`
- allow_methods: `["*"]`
- allow_headers: `["*"]`
- OPTIONS preflight verified: returns 200 with full CORS headers (critical for CSV multipart uploads in 01-02)

## Local Dev Commands

```bash
# Frontend
cd frontend/
npm install
npm run dev          # http://localhost:3000

# Backend
cd backend/
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload    # http://localhost:8000
```

## Decisions & Deviations

| Item | Detail |
|------|--------|
| `next.config.mjs` not `.ts` | Next.js 14.2.3 does not support TypeScript config files. Used `.mjs` instead. Not a plan deviation — the plan specified "Next.js 14 config", and `.mjs` is the correct form for this version. |
| `recharts` pre-installed | Included in frontend deps now so 01-03 doesn't need a fresh install. |
| `vaderSentiment` + `anthropic` pre-installed | Same rationale — venv ready for 01-02 and 01-04. |

## Acceptance Criteria Results

| AC | Result |
|----|--------|
| AC-1: Frontend starts cleanly | PASS — `npm run build` exits 0, renders "Review Radar" heading |
| AC-2: Backend starts cleanly | PASS — `uvicorn` starts on :8000, `/health` returns `{"status":"ok","service":"review-radar-api"}` |
| AC-3: CORS allows frontend origin | PASS — GET and OPTIONS preflight both return `Access-Control-Allow-Origin: http://localhost:3000` |
| AC-4: Environment variables load | PASS — `.env.local` and `.env` present and read at startup |
