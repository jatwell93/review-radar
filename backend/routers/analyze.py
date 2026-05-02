from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from services.csv_parser import parse_reviews
from services.sentiment import run_sentiment_pipeline


class ReviewItem(BaseModel):
    text: str
    score: float


class TimelineEntry(BaseModel):
    month: str
    avg_score: float
    count: int


class Distribution(BaseModel):
    positive: int
    neutral: int
    negative: int


class AnalysisResponse(BaseModel):
    total_reviews: int
    overall_score: float
    distribution: Distribution
    timeline: list[TimelineEntry]
    top_reviews: list[ReviewItem]
    bottom_reviews: list[ReviewItem]


router = APIRouter(prefix="/analyze", tags=["analyze"])


@router.post("/", response_model=AnalysisResponse)
async def analyze(file: UploadFile = File(...)):
    try:
        # Validate file type
        filename = file.filename or ""
        content_type = file.content_type or ""
        if not filename.endswith(".csv") and "csv" not in content_type:
            raise HTTPException(status_code=422, detail="Only CSV files are accepted.")

        contents = await file.read()

        if len(contents) == 0:
            raise HTTPException(status_code=422, detail="Uploaded file is empty.")

        if len(contents) > 10 * 1024 * 1024:
            raise HTTPException(status_code=422, detail="File exceeds 10 MB limit.")

        try:
            reviews = parse_reviews(contents)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

        result = run_sentiment_pipeline(reviews)
        return AnalysisResponse(**result)

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Analysis failed. Please check your file and try again.",
        )
