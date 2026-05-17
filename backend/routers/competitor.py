import logging
import os
from datetime import datetime, timezone

from services.sentiment import score_review, classify
from services.keybert_service import extract_topics
from services.scraper import scrape_with_fallback

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from supabase import create_client

logger = logging.getLogger(__name__)

# Validate all required env vars at startup — fail fast rather than cryptic errors at request time
_REQUIRED_ENV_VARS = [
    "SUPABASE_URL",
    "SUPABASE_SERVICE_ROLE_KEY",
    "GOSOM_API_URL",
]
for _var in _REQUIRED_ENV_VARS:
    if not os.getenv(_var):
        raise RuntimeError(f"Missing required environment variable: {_var}")

SCAN_LIMIT = 10  # competitor scans per user per calendar month


def _get_current_month() -> str:
    """Return current UTC month as 'YYYY-MM'. Uses UTC to ensure consistent boundaries across Render hosts."""
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _get_supabase_admin():
    return create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
    )


class CompetitorScrapeRequest(BaseModel):
    # audit-added: max_length=2000 prevents unbounded URL payload abuse
    url: str = Field(max_length=2000)

    @field_validator("url")
    @classmethod
    def must_be_google_maps_url(cls, v):
        if not (
            v.startswith("https://www.google.com/maps")
            or v.startswith("https://maps.google.com")
        ):
            raise ValueError("URL must be a Google Maps place URL")
        return v


class GapReview(BaseModel):
    # audit-added: max_length=2000 prevents unbounded text from causing VADER/KeyBERT CPU/memory DoS
    # (same pattern as SaveAnalysisRequest.narrative — same risk, same fix)
    text: str = Field(default="", max_length=2000)
    # audit-added: ge=0, le=5 mirrors the Google star rating range; prevents absurd renders
    rating: float = Field(default=0.0, ge=0, le=5)

class GapRequest(BaseModel):
    # audit-added: max_length=500 prevents oversized name from memory abuse or display issues
    name: str = Field(default="", max_length=500)
    # audit-added: ge=0, le=5 prevents nonsense star ratings rendering as "999.0 ★ Google"
    overall_rating: float = Field(default=0.0, ge=0, le=5)
    reviews: list[GapReview] = Field(default_factory=list, max_length=500)


router = APIRouter(prefix="/competitor", tags=["competitor"])


@router.post("/scrape")
async def scrape_competitor(request: Request, body: CompetitorScrapeRequest):
    # --- Auth ---
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Missing or invalid Authorization header"
        )
    token = auth_header.removeprefix("Bearer ").strip()

    supabase = _get_supabase_admin()
    try:
        user_response = supabase.auth.get_user(token)
        if not user_response or not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        user = user_response.user
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # --- Premium gate ---
    # Use .limit(1).execute() — not maybe_single() (see 02-02 decision log)
    sub_result = (
        supabase.table("subscriptions")
        .select("status")
        .eq("user_id", str(user.id))
        .limit(1)
        .execute()
    )
    sub_data = sub_result.data[0] if sub_result.data else None
    if not sub_data or sub_data.get("status") != "active":
        raise HTTPException(status_code=403, detail="premium_required")

    # --- Rate limit ---
    month = _get_current_month()
    scan_result = (
        supabase.table("competitor_scans")
        .select("count")
        .eq("user_id", str(user.id))
        .eq("scan_month", month)
        .limit(1)
        .execute()
    )
    current_count = scan_result.data[0]["count"] if scan_result.data else 0
    if current_count >= SCAN_LIMIT:
        # Retry-After: first day of next month (RFC 9110 §10.6.30)
        year, mon = int(month[:4]), int(month[5:])
        if mon == 12:
            retry_after = f"{year + 1}-01-01"
        else:
            retry_after = f"{year}-{mon + 1:02d}-01"
        raise HTTPException(
            status_code=429,
            detail={"error": "scan_limit_reached", "limit": SCAN_LIMIT, "month": month},
            headers={"Retry-After": retry_after},
        )

    # --- Scrape ---
    # scrape_with_fallback tries gosom first, falls back to Outscraper if 502 and key set
    # If this raises, the exception propagates before the upsert below — quota not consumed (AC-5)
    raw = await scrape_with_fallback(body.url)

    # --- Increment quota ---
    # Only reached if _scrape_with_fallback returned without raising — failed scrapes don't consume quota
    # Known MVP trade-off: two simultaneous requests both reading count=N-1 can both proceed (TOCTOU).
    # Acceptable at pharmacy-owner scale; atomic increment via RPC deferred.
    supabase.table("competitor_scans").upsert(
        {"user_id": str(user.id), "scan_month": month, "count": current_count + 1},
        on_conflict="user_id,scan_month",
    ).execute()

    reviews = [
        {"text": r.get("text", ""), "rating": float(r.get("rating", 0))}
        for r in raw.get("reviews", [])
    ]
    return {
        "name": raw.get("name", ""),
        "overall_rating": float(raw.get("overall_rating", 0)),
        "reviews": reviews,
    }


@router.get("/usage")
async def get_usage(request: Request):
    """Return current month's scan count for the authenticated premium user."""
    # --- Auth ---
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Missing or invalid Authorization header"
        )
    token = auth_header.removeprefix("Bearer ").strip()

    supabase = _get_supabase_admin()
    try:
        user_response = supabase.auth.get_user(token)
        if not user_response or not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        user = user_response.user
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # --- Premium gate ---
    sub_result = (
        supabase.table("subscriptions")
        .select("status")
        .eq("user_id", str(user.id))
        .limit(1)
        .execute()
    )
    sub_data = sub_result.data[0] if sub_result.data else None
    if not sub_data or sub_data.get("status") != "active":
        raise HTTPException(status_code=403, detail="premium_required")

    # --- Fetch current month count ---
    month = _get_current_month()
    scan_result = (
        supabase.table("competitor_scans")
        .select("count")
        .eq("user_id", str(user.id))
        .eq("scan_month", month)
        .limit(1)
        .execute()
    )
    current_count = scan_result.data[0]["count"] if scan_result.data else 0
    return {"count": current_count, "limit": SCAN_LIMIT, "month": month}


@router.post("/gap")
async def gap_analysis(request: Request, body: GapRequest):
    # --- Auth (same pattern as scrape_competitor) ---
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Missing or invalid Authorization header"
        )
    token = auth_header.removeprefix("Bearer ").strip()

    supabase = _get_supabase_admin()
    try:
        user_response = supabase.auth.get_user(token)
        if not user_response or not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        user = user_response.user
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # --- Premium gate ---
    sub_result = (
        supabase.table("subscriptions")
        .select("status")
        .eq("user_id", str(user.id))
        .limit(1)
        .execute()
    )
    sub_data = sub_result.data[0] if sub_result.data else None
    if not sub_data or sub_data.get("status") != "active":
        raise HTTPException(status_code=403, detail="premium_required")

    # --- Run VADER on competitor reviews ---
    # Filter to reviews with non-empty text; empty text → VADER score of 0.0 is correct
    # but adding empty strings to KeyBERT degrades output
    texts = [r.text for r in body.reviews if r.text.strip()]
    if texts:
        scores = [score_review(t) for t in texts]
        vader_score = round(sum(scores) / len(scores), 4)
        dist: dict[str, int] = {"positive": 0, "neutral": 0, "negative": 0}
        for s in scores:
            dist[classify(s)] += 1
    else:
        vader_score = 0.0
        dist = {"positive": 0, "neutral": 0, "negative": 0}

    # --- KeyBERT topic extraction on competitor reviews ---
    # extract_topics returns [] on empty input or any model failure — always safe to call
    topics = extract_topics(texts, top_n=5)

    # --- Fetch user's latest saved analysis ---
    # Returns None if user has no analyses — frontend handles own: null gracefully
    analysis_result = (
        supabase.table("analyses")
        .select("overall_score, distribution, total_reviews, created_at")
        .eq("user_id", str(user.id))
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    own_data = analysis_result.data[0] if analysis_result.data else None

    return {
        "competitor": {
            "name": body.name,
            "overall_rating": body.overall_rating,
            "vader_score": vader_score,
            "distribution": dist,
            "topics": topics,
            "review_count": len(body.reviews),
        },
        "own": own_data,
    }
