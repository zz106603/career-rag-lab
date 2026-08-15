from qdrant_client import QdrantClient, models

from app.keyword_search import KeywordSearchService
from app.langchain_retrieval import SearchFilters


def make_service() -> KeywordSearchService:
    client = QdrantClient(":memory:")
    client.create_collection(
        "documents",
        vectors_config=models.VectorParams(size=2, distance=models.Distance.COSINE),
    )
    client.upsert(
        "documents",
        points=[
            models.PointStruct(
                id=1,
                vector=[1.0, 0.0],
                payload={
                    "content": "Playwright로 브라우저 테스트를 자동화했다.",
                    "metadata": {
                        "source": "dashboard.md",
                        "document_type": "project",
                        "project_name": "대시보드",
                        "chunk_index": 0,
                    },
                },
            ),
            models.PointStruct(
                id=2,
                vector=[0.0, 1.0],
                payload={
                    "content": "pytest 테스트 원칙을 정리했다.",
                    "metadata": {
                        "source": "skills.md",
                        "document_type": "profile",
                        "project_name": None,
                        "chunk_index": 0,
                    },
                },
            ),
        ],
        wait=True,
    )
    return KeywordSearchService(client, "documents")


def test_keyword_search_finds_exact_english_term_without_embedding() -> None:
    results = make_service().search("Playwright를 어디에 사용했나요?", top_k=2)

    assert results[0].source == "dashboard.md"
    assert "playwright" in results[0].metadata["matched_terms"]


def test_keyword_search_applies_same_metadata_filter() -> None:
    service = make_service()

    assert service.search(
        "테스트", filters=SearchFilters(document_type="profile")
    )[0].source == "skills.md"
    assert service.search(
        "Playwright", filters=SearchFilters(document_type="profile")
    ) == []


def test_keyword_search_returns_only_matching_chunks() -> None:
    assert make_service().search("Kafka", top_k=3) == []
