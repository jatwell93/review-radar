# MIGRATION (run once in Supabase SQL editor before deploying):
# ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS pharmacy_url TEXT;

import logging
import os

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from supabase import create_client

from services.scraper import scrape_with_fallback
from services.sentiment import run_sentiment_pipeline
from services.narrative import generate_narrative

logger = logging.getLogger(__name__)

# Validate required env vars at import time — fail fast rather than cryptic errors at request time
_REQUIRED_ENV_VARS = ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "N8N_WEBHOOK_SECRET"]
for _var in _REQUIRED_ENV_VARS:
    if not os.getenv(_var):
        raise RuntimeError(f"Missing required environment variable: {_var}")


def _get_supabase_admin():
    return create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
    )


class PharmacyUrlRequest(BaseModel):
    url: str = Field(max_length=2000)

    @field_validator("url")
    @classmethod
    def must_be_google_maps_url(cls, v):
        if not (v.startswith("https://www.google.com/maps") or v.startswith("https://maps.google.com")):
            raise ValueError("URL must be a Google Maps place URL")
        return v


def _verify_n8n_secret(request: Request):
    secret = os.getenv("N8N_WEBHOOK_SECRET", "")
    if not secret or request.headers.get("X-N8N-Secret") != secret:
        raise HTTPException(status_code=401, detail="Invalid or missing N8N secret")


router = APIRouter(prefix="/automation", tags=["automation"])


@router.patch("/pharmacy-url")
async def set_pharmacy_url(request: Request, body: PharmacyUrlRequest):
    # --- Auth ---
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
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

    # --- Store pharmacy URL ---
    supabase.table("subscriptions").update(
        {"pharmacy_url": body.url}
    ).eq("user_id", str(user.id)).execute()

    return {"pharmacy_url": body.url}


@router.get("/pharmacy-url")
async def get_pharmacy_url(request: Request):
    # --- Auth ---
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
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
        .select("status, pharmacy_url")
        .eq("user_id", str(user.id))
        .limit(1)
        .execute()
    )
    sub_data = sub_result.data[0] if sub_result.data else None
    if not sub_data or sub_data.get("status") != "active":
        raise HTTPException(status_code=403, detail="premium_required")

    return {"pharmacy_url": sub_data.get("pharmacy_url")}


@router.get("/eligible-users")
async def get_eligible_users(request: Request):
    _verify_n8n_secret(request)

    supabase = _get_supabase_admin()
    result = (
        supabase.table("subscriptions")
        .select("user_id, pharmacy_url")
        .eq("status", "active")
        .not_.is_("pharmacy_url", "null")
        .execute()
    )

    users = []
    for row in (result.data or []):
        user_id = row["user_id"]
        try:
            user_resp = supabase.auth.admin.get_user_by_id(user_id)
            email = user_resp.user.email if user_resp and user_resp.user else None
        except Exception:
            logger.warning("Could not fetch email for user_id=%s — skipping", user_id)
            continue
        users.append({"user_id": user_id, "email": email, "pharmacy_url": row["pharmacy_url"]})

    return users


@router.post("/rerun/{user_id}")
async def rerun_analysis(user_id: str, request: Request):
    _verify_n8n_secret(request)

    supabase = _get_supabase_admin()

    # Fetch pharmacy URL for this user — must be active subscriber with URL set
    sub_result = (
        supabase.table("subscriptions")
        .select("pharmacy_url")
        .eq("user_id", user_id)
        .eq("status", "active")
        .not_.is_("pharmacy_url", "null")
        .limit(1)
        .execute()
    )
    sub_data = sub_result.data[0] if sub_result.data else None
    if not sub_data:
        raise HTTPException(status_code=404, detail="No active subscription with pharmacy_url for this user")

    pharmacy_url = sub_data["pharmacy_url"]

    # --- Scrape ---
    raw = await scrape_with_fallback(pharmacy_url)
    reviews = [
        {"text": r.get("text", ""), "rating": float(r.get("rating", 0))}
        for r in raw.get("reviews", [])
    ]

    # --- Sentiment pipeline ---
    result = run_sentiment_pipeline(reviews)

    # --- Narrative (non-blocking) ---
    narrative = None
    try:
        narrative = generate_narrative(result)
    except Exception:
        logger.warning("Narrative generation failed for user_id=%s — proceeding without", user_id)

    # --- Save analysis ---
    try:
        insert_result = supabase.table("analyses").insert({
            "user_id": user_id,
            "overall_score": result["overall_score"],
            "total_reviews": result["total_reviews"],
            "distribution": result["distribution"],
            "timeline": result["timeline"],
            "top_reviews": result["top_reviews"],
            "bottom_reviews": result["bottom_reviews"],
            "narrative": narrative,
        }).execute()
        inserted_id = insert_result.data[0]["id"] if insert_result.data else None
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to save analysis") from exc

    return {
        "user_id": user_id,
        "analysis_id": inserted_id,
        "pharmacy_name": raw.get("name", ""),
        "overall_score": result["overall_score"],
        "total_reviews": result["total_reviews"],
        "distribution": result["distribution"],
        "narrative": narrative,
    }
