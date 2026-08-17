from dataclasses import asdict
from typing import Annotated, Any, Literal

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.answers import (
    AnswerGenerationError,
    RetrievalPipelineError,
)
from app.hybrid_search import HybridSearchService, create_hybrid_search_service
from app.langchain_rag import LangChainRagService
from app.langchain_retrieval import LangChainRetrievalService, SearchFilters
from app.keyword_search import KeywordSearchService, create_keyword_search_service
from app.pipeline import create_default_answer_service, create_default_search_service
from app.sparse_search import SparseSearchService, create_sparse_search_service

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


class KeywordSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=100)
    filters: SearchFilterRequest | None = None


class HybridSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=100)
    candidate_k: int | None = Field(default=None, ge=1, le=200)
    filters: SearchFilterRequest | None = None


class SearchResponse(BaseModel):
    query: str
    results: list[dict[str, Any]]


class HybridSearchResponse(BaseModel):
    query: str
    dense: list[dict[str, Any]]
    sparse: list[dict[str, Any]]
    hybrid: list[dict[str, Any]]


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


def get_keyword_search_service() -> KeywordSearchService:
    return create_keyword_search_service()


def get_sparse_search_service() -> SparseSearchService:
    return create_sparse_search_service()


def get_hybrid_search_service() -> HybridSearchService:
    return create_hybrid_search_service()


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


@app.post("/search/keyword", response_model=SearchResponse)
def keyword_search(
    request: KeywordSearchRequest,
    service: Annotated[
        KeywordSearchService, Depends(get_keyword_search_service)
    ],
) -> SearchResponse:
    """Embedding 없이 실제 단어가 일치한 Chunk와 keyword score를 반환한다."""
    results = service.search(
        request.query,
        top_k=request.top_k,
        filters=request.filters.to_domain() if request.filters else None,
    )
    return SearchResponse(
        query=request.query,
        results=[asdict(result) for result in results],
    )


@app.post("/search/sparse", response_model=SearchResponse)
def sparse_search(
    request: KeywordSearchRequest,
    service: Annotated[SparseSearchService, Depends(get_sparse_search_service)],
) -> SearchResponse:
    """Qdrant sparse vector 검색 결과와 score를 Dense 결과와 분리한다."""
    results = service.search(
        request.query,
        top_k=request.top_k,
        filters=request.filters.to_domain() if request.filters else None,
    )
    return SearchResponse(
        query=request.query,
        results=[asdict(result) for result in results],
    )


@app.post("/search/hybrid", response_model=HybridSearchResponse)
def hybrid_search(
    request: HybridSearchRequest,
    service: Annotated[HybridSearchService, Depends(get_hybrid_search_service)],
) -> HybridSearchResponse:
    """Dense·Sparse 원본 후보와 RRF 결합 결과를 함께 반환한다."""
    result = service.search(
        request.query,
        top_k=request.top_k,
        candidate_k=request.candidate_k,
        filters=request.filters.to_domain() if request.filters else None,
    )
    return HybridSearchResponse(
        query=request.query,
        dense=[asdict(item) for item in result.dense],
        sparse=[asdict(item) for item in result.sparse],
        hybrid=[asdict(item) for item in result.hybrid],
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
