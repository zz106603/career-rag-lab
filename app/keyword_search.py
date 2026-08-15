import re
from collections import Counter

from qdrant_client import QdrantClient

from app.config import Settings, get_settings
from app.langchain_retrieval import SearchFilters, build_qdrant_filter
from app.search import InvalidSearchInputError, SearchPayloadError, SearchResult


TOKEN_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9.+#_-]*|[가-힣]+|\d+")
KOREAN_PARTICLES = {"은", "는", "이", "가", "을", "를", "에", "에서", "와", "과", "의"}


class KeywordSearchService:
    """Chunk의 실제 단어 일치도를 Dense score와 분리해 관찰한다."""

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
        query_terms = tuple(
            term for term in tokenize(query) if term not in KOREAN_PARTICLES
        )
        if not query_terms:
            return []

        results: list[SearchResult] = []
        offset = None
        while True:
            records, offset = self.client.scroll(
                self.collection_name,
                scroll_filter=build_qdrant_filter(filters),
                limit=256,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            for record in records:
                result = _score_record(record.payload, query_terms)
                if result is not None:
                    results.append(result)
            if offset is None:
                break
        return sorted(
            results,
            key=lambda item: (
                -item.score,
                item.source,
                int(item.metadata.get("chunk_index", 0)),
            ),
        )[:top_k]


def create_keyword_search_service(
    *,
    settings: Settings | None = None,
    qdrant_client: QdrantClient | None = None,
) -> KeywordSearchService:
    active_settings = settings or get_settings()
    return KeywordSearchService(
        qdrant_client or QdrantClient(url=active_settings.qdrant_url),
        active_settings.qdrant_collection,
    )


def tokenize(text: str) -> list[str]:
    return [match.group(0).casefold() for match in TOKEN_PATTERN.finditer(text)]


def _score_record(
    payload: dict | None, query_terms: tuple[str, ...]
) -> SearchResult | None:
    if not isinstance(payload, dict):
        raise SearchPayloadError("Keyword result payload is missing")
    content = payload.get("content")
    metadata = payload.get("metadata")
    if not isinstance(content, str) or not isinstance(metadata, dict):
        raise SearchPayloadError("Keyword result requires content and metadata")
    source = metadata.get("source")
    if not isinstance(source, str):
        raise SearchPayloadError("Keyword result requires string source")
    counts = Counter(tokenize(content))
    matched_occurrences = sum(counts[term] for term in set(query_terms))
    if matched_occurrences == 0:
        return None
    matched_terms = sum(term in counts for term in set(query_terms))
    # 서로 다른 질문 단어를 많이 포함한 Chunk를 우선하고 반복 출현은 작은
    # tie-break 가중치만 준다. 이 점수는 Cosine score와 직접 비교하지 않는다.
    score = matched_terms / len(set(query_terms)) + min(matched_occurrences, 9) / 100
    result_metadata = dict(metadata)
    result_metadata["matched_terms"] = sorted(
        term for term in set(query_terms) if term in counts
    )
    return SearchResult(
        content=content,
        source=source,
        score=score,
        metadata=result_metadata,
    )
