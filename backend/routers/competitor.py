import csv
import io
import json
import logging
import os
import time
from datetime import datetime, timezone

from services.sentiment import score_review, classify
from services.keybert_service import extract_topics

import asyncio
import httpx
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

# gosom job lifecycle timeouts
# Individual HTTP requests (create job, poll, download) each have _GOSOM_REQUEST_TIMEOUT.
# The total time we wait for a job to reach "completed" is _GOSOM_POLL_TIMEOUT.
_GOSOM_REQUEST_TIMEOUT = 30.0   # seconds per HTTP request to gosom
_GOSOM_POLL_TIMEOUT = 180.0     # seconds max for job to complete (3 min ceiling)
_GOSOM_POLL_INTERVAL = 5.0      # seconds between status poll requests

_OUTSCRAPER_REVIEWS_URL = "https://api.app.outscraper.com/maps/reviews"
_OUTSCRAPER_REQUEST_TIMEOUT = 30.0   # seconds — synchronous API, no job polling
_OUTSCRAPER_REVIEW_LIMIT = 100       # max reviews fetched per Outscraper request

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


def _parse_gosom_csv(csv_text: str) -> dict:
    """Parse gosom CSV download into normalised scrape response.

    gosom CSV column names (based on gosom v0.x output — verify against a real
    download from GET /api/v1/jobs/{id}/download by inspecting the header row):
      title           — place name
      review_rating   — overall star rating (float)
      reviews         — JSON-encoded array of review objects (may be empty string)

    Each review object (field names may vary by gosom version):
      text / review_text / snippet — review body
      rating / review_rating / stars — individual star rating

    If the column names in a real download differ, adjust the .get() key names below.
    """
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = list(reader)

    if not rows:
        return {"name": "", "overall_rating": 0.0, "reviews": []}

    # First row = the scraped place (one job → one place URL → one row)
    place = rows[0]

    name = place.get("title") or place.get("name") or ""

    try:
        overall_rating = float(
            place.get("review_rating") or place.get("rating") or 0
        )
    except (ValueError, TypeError):
        overall_rating = 0.0

    # Reviews may be stored as a JSON string in the CSV cell, or absent entirely
    reviews = []
    reviews_raw = place.get("reviews") or place.get("user_reviews") or ""
    if reviews_raw:
        try:
            review_list = json.loads(reviews_raw)
            for r in (review_list or []):
                reviews.append({
                    "text": (
                        r.get("text")
                        or r.get("review_text")
                        or r.get("snippet")
                        or ""
                    ),
                    "rating": float(
                        r.get("rating")
                        or r.get("review_rating")
                        or r.get("stars")
                        or 0
                    ),
                })
        except (ValueError, TypeError, json.JSONDecodeError):
            # Reviews column not parseable — return empty (AC-7: 0 reviews is valid)
            reviews = []

    return {"name": name, "overall_rating": overall_rating, "reviews": reviews}


async def _call_gosom(url: str) -> str:
    """Submit a scrape job to gosom, poll until complete, return raw CSV text.

    gosom uses an async job-based REST API:
      POST /api/v1/jobs         → create job, get job ID
      GET  /api/v1/jobs/{id}   → poll status ("completed" / "running" / "failed")
      GET  /api/v1/jobs/{id}/download → download CSV results

    Full OpenAPI spec available at: {GOSOM_API_URL}/api/docs

    NOTE: The request body fields ("urls", "depth") and status values are based on
    the gosom API as documented. Verify against the running instance's /api/docs if
    behaviour differs. Adjust field names accordingly.
    """
    gosom_base = os.getenv("GOSOM_API_URL", "").rstrip("/")

    try:
        async with httpx.AsyncClient(timeout=_GOSOM_REQUEST_TIMEOUT) as client:
            # Step 1: Create scraping job
            # Body fields — verify against gosom /api/docs if job creation fails:
            #   "urls": list of Google Maps place URLs to scrape
            #   "depth": scrape depth (1 = place details + reviews)
            create_resp = await client.post(
                f"{gosom_base}/api/v1/jobs",
                json={"urls": [url], "depth": 1},
            )
            create_resp.raise_for_status()
            job_data = create_resp.json()

            # Extract job ID — field name may be "id", "jobId", or "job_id"
            job_id = (
                job_data.get("id")
                or job_data.get("jobId")
                or job_data.get("job_id")
            )
            if not job_id:
                raise ValueError(f"No job ID returned from gosom: {job_data}")

            # Step 2: Poll until completed or timeout
            deadline = time.monotonic() + _GOSOM_POLL_TIMEOUT
            while True:
                if time.monotonic() > deadline:
                    raise TimeoutError(
                        f"gosom job {job_id} did not complete within {_GOSOM_POLL_TIMEOUT}s"
                    )
                await asyncio.sleep(_GOSOM_POLL_INTERVAL)

                status_resp = await client.get(f"{gosom_base}/api/v1/jobs/{job_id}")
                status_resp.raise_for_status()
                status_data = status_resp.json()

                # Status values — verify against gosom /api/docs if polling stalls
                status = str(status_data.get("status", "")).lower()
                if status in ("completed", "done", "finished", "complete"):
                    break
                elif status in ("failed", "error", "cancelled", "canceled"):
                    raise ValueError(f"gosom job {job_id} ended with status: {status!r}")
                # else: still running — continue polling

            # Step 3: Download CSV results
            download_resp = await client.get(
                f"{gosom_base}/api/v1/jobs/{job_id}/download"
            )
            download_resp.raise_for_status()
            return download_resp.text

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="scraper_unavailable")


async def _call_outscraper(url: str, api_key: str) -> dict:
    """Call the Outscraper Maps Reviews API and normalise to stable scrape contract."""
    try:
        async with httpx.AsyncClient(timeout=_OUTSCRAPER_REQUEST_TIMEOUT) as client:
            resp = await client.get(
                _OUTSCRAPER_REVIEWS_URL,
                params={"query": url, "reviewsLimit": _OUTSCRAPER_REVIEW_LIMIT, "language": "en"},
                headers={"X-API-KEY": api_key},
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=502, detail="scraper_unavailable")
            data = resp.json().get("data") or []
            if not data:
                return {"name": "", "overall_rating": 0.0, "reviews": []}
            place = data[0]
            name = place.get("name") or ""
            overall_rating = float(place.get("rating") or 0)
            reviews_raw = place.get("reviews_data") or []
            reviews = [
                {
                    "text": r.get("review_text") or "",
                    "rating": float(r.get("review_rating") or 0),
                }
                for r in reviews_raw
            ]
            return {"name": name, "overall_rating": overall_rating, "reviews": reviews}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="scraper_unavailable")


async def _scrape_with_fallback(url: str) -> dict:
    """Try gosom first; fall back to Outscraper on 502."""
    try:
        csv_text = await _call_gosom(url)
        return _parse_gosom_csv(csv_text)
    except HTTPException as exc:
        if exc.status_code != 502:
            raise  # auth/validation errors — not an availability problem (AC-5)
    except Exception:
        raise HTTPException(status_code=502, detail="scraper_response_invalid")

    # gosom returned 502 — attempt Outscraper
    outscraper_key = os.getenv("OUTSCRAPER_API_KEY")
    if not outscraper_key:
        raise HTTPException(status_code=502, detail="scraper_unavailable")  # AC-2
    logger.warning("gosom unavailable (502), falling back to Outscraper for %s", url)
    return await _call_outscraper(url, outscraper_key)


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
    # _scrape_with_fallback tries gosom first, falls back to Outscraper if 502 and key set
    # If this raises, the exception propagates before the upsert below — quota not consumed (AC-5)
    raw = await _scrape_with_fallback(body.url)

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
