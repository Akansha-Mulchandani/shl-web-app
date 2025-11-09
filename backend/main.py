from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from .recommender import Recommender, Recommendation
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="SHL Assessment Recommender API")

# Enable CORS for local dev (frontend on different origin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

recommender = Recommender()


class RecommendRequest(BaseModel):
    query: str


class RecommendedAssessment(BaseModel):
    url: str
    adaptive_support: str
    description: Optional[str] = None
    duration: Optional[int] = None
    remote_support: str
    test_type: List[str] = []


class RecommendResponse(BaseModel):
    recommended_assessments: List[RecommendedAssessment]


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/")
def root():
    return {
        "name": "SHL Assessment Recommender API",
        "docs": "/docs",
        "health": "/health",
        "recommend": "/recommend"
    }


@app.post("/recommend", response_model=RecommendResponse)
def recommend(req: RecommendRequest):
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query must not be empty")
    recs = recommender.recommend(query, k=10)
    # Enforce 5-10 results
    recs = recs[:10]
    if len(recs) < 5:
        recs = recs + recs[: max(0, 5 - len(recs))]
    items = [
        RecommendedAssessment(
            url=r.assessment_url,
            adaptive_support=r.adaptive_support,
            description=r.description,
            duration=r.duration,
            remote_support=r.remote_support,
            test_type=r.test_type,
        )
        for r in recs
    ]
    return RecommendResponse(recommended_assessments=items)
