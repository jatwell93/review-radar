import os

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from supabase import create_client
from typing import Annotated

from routers.analyze import Distribution, TimelineEntry, ReviewItem

# Validate required env vars at import time — fail fast rather than cryptic errors at request time
_REQUIRED_ENV_VARS = [
    "SUPABASE_URL",
    "SUPABASE_SERVICE_ROLE_KEY",
]
for _var in _REQUIRED_ENV_VARS:
    if not os.getenv(_var):
        raise RuntimeError(f"Missing required environment variable: {_var}")


def _get_supabase_admin():
    return create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
    )


class SaveAnalysisRequest(BaseModel):
    overall_score: float
    total_reviews: int
    distribution: Distribution
    timeline: Annotated[list[TimelineEntry], Field(max_length=120)]  # max 10yr monthly
    top_reviews: Annotated[list[ReviewItem], Field(max_length=10)]
    bottom_reviews: Annotated[list[ReviewItem], Field(max_length=10)]
    narrative: str | None = Field(default=None, max_length=2000)


router = APIRouter(prefix="/analyses", tags=["analyses"])


@router.post("/")
async def save_analysis(request: Request, body: SaveAnalysisRequest):
    # Extract and validate Bearer token
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = auth_header.removeprefix("Bearer ").strip()

    # Validate token against Supabase — get_user() raises on invalid tokens in supabase-py v2
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

    # Premium gate: check subscriptions table
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

    # Insert as a distinct historical record (not upsert — each save is unique)
    try:
        result = supabase.table("analyses").insert({
            "user_id": str(user.id),
            "overall_score": body.overall_score,
            "total_reviews": body.total_reviews,
            "distribution": body.distribution.model_dump(),
            "timeline": [e.model_dump() for e in body.timeline],
            "top_reviews": [r.model_dump() for r in body.top_reviews],
            "bottom_reviews": [r.model_dump() for r in body.bottom_reviews],
            "narrative": body.narrative,
            # created_at intentionally omitted — let Supabase default handle it
        }).execute()
        inserted_id = result.data[0]["id"] if result.data else None
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to save analysis")

    return JSONResponse(status_code=201, content={"id": inserted_id})
