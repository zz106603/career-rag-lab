import hashlib
from collections import Counter

from qdrant_client import QdrantClient, models

from app.config import Settings, get_settings
from app.keyword_search import KOREAN_PARTICLES, tokenize
from app.langchain_retrieval import SearchFilters, build_qdrant_filter
from app.search import InvalidSearchInputError, SearchPayloadError, SearchResult


SPARSE_VECTOR_NAME = "text-sparse"


def encode_sparse(text: str) -> models.SparseVector:
    """동일 token을 문서와 질문에서 같은 결정적 sparse index로 변환한다."""
    counts = Counter(
        term for term in tokenize(text) if term not in KOREAN_PARTICLES
    )
    by_index: dict[int, float] = {}
    for term, count in counts.items():
        index = int.from_bytes(
            hashlib.sha256(term.encode("utf-8")).digest()[:4], "big"
        )
        by_index[index] = by_index.get(index, 0.0) + float(count)
    indices = sorted(by_index)
    return models.SparseVector(
        indices=indices,
        values=[by_index[index] for index in indices],
    )


class SparseSearchService:
    """Qdrant sparse vector score를 Dense·Keyword 결과와 분리해 반환한다."""

    def __init__(self, client: QdrantClient, collection_name: str) -> None:
        self.client = client
        self.collection_name = collection_name

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        filters: SearchFilters | None = None,
    ) -> list[SearchResult]:
        if not query.strip():
            raise InvalidSearchInputError("query must not be empty")
        if top_k <= 0:
            raise InvalidSearchInputError("top_k must be greater than 0")
        vector = encode_sparse(query)
        if not vector.indices:
            return []
        response = self.client.query_points(
            collection_name=self.collection_name,
            query=vector,
            using=SPARSE_VECTOR_NAME,
            query_filter=build_qdrant_filter(filters),
            limit=top_k,
            with_payload=True,
            with_vectors=False,
        )
        return [_to_result(point.payload, point.score) for point in response.points]


def create_sparse_search_service(
    *,
    settings: Settings | None = None,
    qdrant_client: QdrantClient | None = None,
) -> SparseSearchService:
    active_settings = settings or get_settings()
    return SparseSearchService(
        qdrant_client or QdrantClient(url=active_settings.qdrant_url),
        active_settings.qdrant_collection,
    )


def _to_result(payload: dict | None, score: float) -> SearchResult:
    if not isinstance(payload, dict):
        raise SearchPayloadError("Sparse result payload is missing")
    content = payload.get("content")
    metadata = payload.get("metadata")
    if not isinstance(content, str) or not isinstance(metadata, dict):
        raise SearchPayloadError("Sparse result requires content and metadata")
    source = metadata.get("source")
    if not isinstance(source, str):
        raise SearchPayloadError("Sparse result requires string source")
    result_metadata = dict(metadata)
    result_metadata.pop("source", None)
    return SearchResult(content, source, float(score), result_metadata)
