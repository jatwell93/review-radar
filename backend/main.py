import os
from dotenv import load_dotenv

# Must run before any router imports — routers validate env vars at module level
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.analyze import router as analyze_router
from routers.narrative import router as narrative_router
from routers.stripe import router as stripe_router
from routers.analyses import router as analyses_router
from routers.topics import router as topics_router

app = FastAPI(title="Review Radar API")

allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze_router)
app.include_router(narrative_router)
app.include_router(stripe_router)
app.include_router(analyses_router)
app.include_router(topics_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "review-radar-api"}
