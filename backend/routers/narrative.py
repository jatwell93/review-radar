from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from routers.analyze import Distribution, ReviewItem
from services.narrative import generate_narrative


class NarrativeRequest(BaseModel):
    total_reviews: int
    overall_score: float
    distribution: Distribution
    top_reviews: list[ReviewItem]
    bottom_reviews: list[ReviewItem]


router = APIRouter(prefix="/narrative", tags=["narrative"])


@router.post("/")
async def narrative(data: NarrativeRequest):
    try:
        text = generate_narrative(data.model_dump())
        return {"narrative": text}
    except HTTPException:
        raise
    except ValueError:
        return JSONResponse(
            status_code=503,
            content={"detail": "Narrative service not configured"},
        )
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"detail": "Narrative generation failed. Please try again."},
        )
