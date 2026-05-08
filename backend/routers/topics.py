import os

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from supabase import create_client
from typing import Annotated

from routers.analyze import ReviewItem
from services.keybert_service import extract_topics


def _get_supabase_admin():
    return create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
    )


class TopicsRequest(BaseModel):
    top_reviews: Annotated[list[ReviewItem], Field(max_length=10)]
    bottom_reviews: Annotated[list[ReviewItem], Field(max_length=10)]


class TopicsResponse(BaseModel):
    positive_topics: list[str]
    negative_topics: list[str]


router = APIRouter(prefix="/topics", tags=["topics"])


@router.post("/", response_model=TopicsResponse)
async def get_topics(request: Request, body: TopicsRequest):
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

    positive_topics = extract_topics([r.text for r in body.top_reviews])
    negative_topics = extract_topics([r.text for r in body.bottom_reviews])

    return TopicsResponse(positive_topics=positive_topics, negative_topics=negative_topics)
