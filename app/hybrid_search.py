from dataclasses import dataclass

from qdrant_client import QdrantClient

from app.config import Settings, get_settings
from app.langchain_retrieval import (
    LangChainRetrievalService,
    SearchFilters,
    create_langchain_retrieval_service,
)
from app.search import InvalidSearchInputError, SearchResult
from app.sparse_search import SparseSearchService, create_sparse_search_service


RRF_K = 60


@dataclass(frozen=True)
class HybridSearchResult:
    """원본 두 검색 목록과 순위 융합 결과를 함께 보존한다."""

    dense: list[SearchResult]
    sparse: list[SearchResult]
    hybrid: list[SearchResult]


class HybridSearchService:
    def __init__(
        self,
        dense_service: LangChainRetrievalService,
        sparse_service: SparseSearchService,
    ) -> None:
        self.dense_service = dense_service
        self.sparse_service = sparse_service

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        candidate_k: int | None = None,
        filters: SearchFilters | None = None,
    ) -> HybridSearchResult:
        if not query.strip():
            raise InvalidSearchInputError("query must not be empty")
        if top_k <= 0:
            raise InvalidSearchInputError("top_k must be greater than 0")
        active_candidate_k = max(top_k * 2, 5) if candidate_k is None else candidate_k
        if active_candidate_k < top_k:
            raise InvalidSearchInputError("candidate_k must be at least top_k")
        dense = self.dense_service.search(
            query, top_k=active_candidate_k, filters=filters
        )
        sparse = self.sparse_service.search(
            query, top_k=active_candidate_k, filters=filters
        )
        return HybridSearchResult(
            dense=dense,
            sparse=sparse,
            hybrid=_reciprocal_rank_fusion(dense, sparse)[:top_k],
        )


def create_hybrid_search_service(
    *,
    settings: Settings | None = None,
    qdrant_client: QdrantClient | None = None,
) -> HybridSearchService:
    active_settings = settings or get_settings()
    active_client = qdrant_client or QdrantClient(url=active_settings.qdrant_url)
    return HybridSearchService(
        create_langchain_retrieval_service(
            settings=active_settings, qdrant_client=active_client
        ),
        create_sparse_search_service(
            settings=active_settings, qdrant_client=active_client
        ),
    )


def _reciprocal_rank_fusion(
    dense: list[SearchResult], sparse: list[SearchResult]
) -> list[SearchResult]:
    candidates: dict[str, dict] = {}
    for search_type, results in (("dense", dense), ("sparse", sparse)):
        for rank, result in enumerate(results, start=1):
            key = _candidate_key(result)
            state = candidates.setdefault(
                key,
                {
                    "result": result,
                    "score": 0.0,
                    "dense_rank": None,
                    "sparse_rank": None,
                    "dense_score": None,
                    "sparse_score": None,
                },
            )
            state["score"] += 1.0 / (RRF_K + rank)
            state[f"{search_type}_rank"] = rank
            state[f"{search_type}_score"] = result.score

    fused = []
    for state in candidates.values():
        original: SearchResult = state["result"]
        metadata = dict(original.metadata)
        metadata.update(
            {
                "fusion_method": "rrf",
                "dense_rank": state["dense_rank"],
                "sparse_rank": state["sparse_rank"],
                "dense_score": state["dense_score"],
                "sparse_score": state["sparse_score"],
            }
        )
        fused.append(
            SearchResult(
                content=original.content,
                source=original.source,
                score=state["score"],
                metadata=metadata,
            )
        )
    return sorted(
        fused,
        key=lambda item: (
            -item.score,
            min(
                rank
                for rank in (
                    item.metadata["dense_rank"],
                    item.metadata["sparse_rank"],
                )
                if rank is not None
            ),
            item.source,
            str(item.metadata.get("chunk_id", "")),
        ),
    )


def _candidate_key(result: SearchResult) -> str:
    chunk_id = result.metadata.get("chunk_id")
    return str(chunk_id) if chunk_id else f"{result.source}\n{result.content}"
