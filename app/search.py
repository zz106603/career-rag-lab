from dataclasses import dataclass
from typing import Any

from openai import OpenAI
from qdrant_client import QdrantClient

from app.config import Settings, get_settings
from app.embeddings import create_openai_client


class SearchError(ValueError):
    """검색 입력이나 저장된 Point를 신뢰할 수 없을 때 발생한다."""


class InvalidSearchInputError(SearchError):
    """질문, top_k 또는 threshold가 허용 범위를 벗어나면 발생한다."""


class QueryEmbeddingError(SearchError):
    """질문 Embedding 응답의 개수나 차원이 설정과 다를 때 발생한다."""


class SearchPayloadError(SearchError):
    """검색된 Point에 필수 payload가 없거나 형식이 잘못되면 발생한다."""


@dataclass(frozen=True)
class SearchResult:
    """LLM 답변과 섞이지 않는 하나의 검색 근거."""

    content: str
    source: str
    score: float
    metadata: dict[str, Any]


class QdrantSearcher:
    """질문 벡터로 Qdrant의 유사 Chunk만 조회한다."""

    def __init__(self, client: QdrantClient, collection_name: str) -> None:
        if not collection_name.strip():
            raise ValueError("collection_name must not be empty")
        self.client = client
        self.collection_name = collection_name

    def search(
        self,
        query_vector: list[float],
        *,
        top_k: int = 5,
        score_threshold: float | None = None,
    ) -> list[SearchResult]:
        _validate_search_options(query_vector, top_k, score_threshold)
        response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=top_k,
            score_threshold=score_threshold,
            with_payload=True,
            with_vectors=False,
        )

        # Qdrant가 Cosine score 내림차순으로 반환한 순서를 그대로 보존한다.
        return [_to_search_result(point.payload, point.score) for point in response.points]


class SearchService:
    """질문 Embedding과 벡터 검색을 연결하되 답변은 생성하지 않는다."""

    def __init__(
        self,
        searcher: QdrantSearcher,
        openai_client: OpenAI,
        settings: Settings,
    ) -> None:
        self.searcher = searcher
        self.openai_client = openai_client
        self.settings = settings

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        score_threshold: float | None = None,
    ) -> list[SearchResult]:
        if not query.strip():
            raise InvalidSearchInputError("query must not be empty")

        response = self.openai_client.embeddings.create(
            model=self.settings.embedding_model,
            input=[query],
            dimensions=self.settings.embedding_dimensions,
        )
        if len(response.data) != 1:
            raise QueryEmbeddingError("Query Embedding response must contain one item")
        vector = list(response.data[0].embedding)
        if len(vector) != self.settings.embedding_dimensions:
            raise QueryEmbeddingError(
                "Query Embedding dimension does not match the configured dimension"
            )
        return self.searcher.search(
            vector,
            top_k=top_k,
            score_threshold=score_threshold,
        )


def create_search_service(
    *,
    settings: Settings | None = None,
    openai_client: OpenAI | None = None,
    qdrant_client: QdrantClient | None = None,
) -> SearchService:
    active_settings = settings or get_settings()
    active_qdrant_client = qdrant_client or QdrantClient(
        url=active_settings.qdrant_url
    )
    return SearchService(
        searcher=QdrantSearcher(
            active_qdrant_client,
            collection_name=active_settings.qdrant_collection,
        ),
        openai_client=openai_client or create_openai_client(active_settings),
        settings=active_settings,
    )


def _validate_search_options(
    query_vector: list[float], top_k: int, score_threshold: float | None
) -> None:
    if not query_vector:
        raise InvalidSearchInputError("query_vector must not be empty")
    if top_k <= 0:
        raise InvalidSearchInputError("top_k must be greater than 0")
    if score_threshold is not None and not -1.0 <= score_threshold <= 1.0:
        raise InvalidSearchInputError("score_threshold must be between -1 and 1")


def _to_search_result(payload: dict[str, Any] | None, score: float) -> SearchResult:
    if not isinstance(payload, dict):
        raise SearchPayloadError("Search result payload is missing")
    content = payload.get("content")
    source = payload.get("source")
    if not isinstance(content, str) or not isinstance(source, str):
        raise SearchPayloadError("Search result requires string content and source")

    # content와 source는 자주 쓰는 최상위 필드로 올리고 나머지는 출처 추적용
    # metadata로 그대로 보존한다.
    metadata = {
        key: value for key, value in payload.items() if key not in {"content", "source"}
    }
    return SearchResult(
        content=content,
        source=source,
        score=float(score),
        metadata=metadata,
    )
