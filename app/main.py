from dataclasses import asdict
from typing import Annotated, Any

from fastapi import Depends, FastAPI
from pydantic import BaseModel, Field

from app.search import SearchService, create_search_service

app = FastAPI(title="career-rag-lab")


@app.get("/health")
def health() -> dict[str, str]:
    """외부 서비스와 무관하게 FastAPI 자체가 응답 가능한지 확인한다."""
    return {"status": "ok"}


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=100)
    score_threshold: float | None = Field(default=None, ge=-1.0, le=1.0)


class SearchResponse(BaseModel):
    query: str
    results: list[dict[str, Any]]


def get_search_service() -> SearchService:
    return create_search_service()


@app.post("/search", response_model=SearchResponse)
def search(
    request: SearchRequest,
    service: Annotated[SearchService, Depends(get_search_service)],
) -> SearchResponse:
    """LLM 호출 없이 검색된 근거와 score를 그대로 반환한다."""
    results = service.search(
        request.query,
        top_k=request.top_k,
        score_threshold=request.score_threshold,
    )
    return SearchResponse(
        query=request.query,
        results=[asdict(result) for result in results],
    )
