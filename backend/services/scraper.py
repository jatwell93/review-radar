import csv
import io
import json
import logging
import os
import time

import asyncio
import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# gosom job lifecycle timeouts
# Individual HTTP requests (create job, poll, download) each have _GOSOM_REQUEST_TIMEOUT.
# The total time we wait for a job to reach "completed" is _GOSOM_POLL_TIMEOUT.
_GOSOM_REQUEST_TIMEOUT = 30.0   # seconds per HTTP request to gosom
_GOSOM_POLL_TIMEOUT = 180.0     # seconds max for job to complete (3 min ceiling)
_GOSOM_POLL_INTERVAL = 5.0      # seconds between status poll requests

_OUTSCRAPER_REVIEWS_URL = "https://api.app.outscraper.com/maps/reviews"
_OUTSCRAPER_REQUEST_TIMEOUT = 30.0   # seconds — synchronous API, no job polling
_OUTSCRAPER_REVIEW_LIMIT = 100       # max reviews fetched per Outscraper request


def parse_gosom_csv(csv_text: str) -> dict:
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


async def call_gosom(url: str) -> str:
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


async def call_outscraper(url: str, api_key: str) -> dict:
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


async def scrape_with_fallback(url: str) -> dict:
    """Try gosom first; fall back to Outscraper on 502."""
    try:
        csv_text = await call_gosom(url)
        return parse_gosom_csv(csv_text)
    except HTTPException as exc:
        if exc.status_code != 502:
            raise  # auth/validation errors — not an availability problem
    except Exception:
        raise HTTPException(status_code=502, detail="scraper_response_invalid")

    # gosom returned 502 — attempt Outscraper
    outscraper_key = os.getenv("OUTSCRAPER_API_KEY")
    if not outscraper_key:
        raise HTTPException(status_code=502, detail="scraper_unavailable")
    logger.warning("gosom unavailable (502), falling back to Outscraper for %s", url)
    return await call_outscraper(url, outscraper_key)
