from dataclasses import asdict
from typing import Annotated, Any, Literal

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.answers import (
    AnswerGenerationError,
    RetrievalPipelineError,
)
from app.langchain_rag import LangChainRagService
from app.langchain_retrieval import LangChainRetrievalService, SearchFilters
from app.pipeline import create_default_answer_service, create_default_search_service

app = FastAPI(title="career-rag-lab")


@app.get("/health")
def health() -> dict[str, str]:
    """외부 서비스와 무관하게 FastAPI 자체가 응답 가능한지 확인한다."""
    return {"status": "ok"}


class SearchFilterRequest(BaseModel):
    document_type: str | None = Field(default=None, min_length=1)
    project_name: str | None = Field(default=None, min_length=1)
    source: str | None = Field(default=None, min_length=1)

    def to_domain(self) -> SearchFilters:
        return SearchFilters(**self.model_dump())


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=100)
    score_threshold: float | None = Field(default=None, ge=-1.0, le=1.0)
    filters: SearchFilterRequest | None = None


class SearchResponse(BaseModel):
    query: str
    results: list[dict[str, Any]]


class AnswerRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int | None = Field(default=None, ge=1, le=20)
    score_threshold: float | None = Field(default=None, ge=-1.0, le=1.0)
    filters: SearchFilterRequest | None = None


class AnswerResponse(BaseModel):
    status: Literal["answered", "insufficient_evidence"]
    answer: str
    sources: list[str]
    retrieval: list[dict[str, Any]]
    generated: bool


def get_search_service() -> LangChainRetrievalService:
    return create_default_search_service()


def get_answer_service() -> LangChainRagService:
    return create_default_answer_service()


@app.exception_handler(RetrievalPipelineError)
def handle_retrieval_failure(
    _request: Any, _error: RetrievalPipelineError
) -> JSONResponse:
    """검색 단계 실패를 답변 생성 실패와 구분하되 내부 예외는 노출하지 않는다."""
    return JSONResponse(
        status_code=502,
        content={"detail": {"code": "retrieval_failed", "message": "검색에 실패했습니다."}},
    )


@app.exception_handler(AnswerGenerationError)
def handle_generation_failure(
    _request: Any, _error: AnswerGenerationError
) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content={
            "detail": {
                "code": "generation_failed",
                "message": "답변 생성에 실패했습니다.",
            }
        },
    )


@app.post("/search", response_model=SearchResponse)
def search(
    request: SearchRequest,
    service: Annotated[LangChainRetrievalService, Depends(get_search_service)],
) -> SearchResponse:
    """LLM 호출 없이 검색된 근거와 score를 그대로 반환한다."""
    results = service.search(
        request.query,
        top_k=request.top_k,
        score_threshold=request.score_threshold,
        filters=request.filters.to_domain() if request.filters else None,
    )
    return SearchResponse(
        query=request.query,
        results=[asdict(result) for result in results],
    )


@app.post("/answer", response_model=AnswerResponse)
def answer(
    request: AnswerRequest,
    service: Annotated[LangChainRagService, Depends(get_answer_service)],
) -> AnswerResponse:
    """검색 근거가 있을 때만 답변을 생성하고 retrieval을 함께 반환한다."""
    result = service.answer(
        request.query,
        top_k=request.top_k,
        score_threshold=request.score_threshold,
        filters=request.filters.to_domain() if request.filters else None,
    )
    return AnswerResponse(
        status=result.status,
        answer=result.answer,
        sources=result.sources,
        retrieval=[asdict(item) for item in result.retrieval],
        generated=result.generated,
    )
