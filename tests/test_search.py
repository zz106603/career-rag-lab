from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from qdrant_client import QdrantClient, models

from app.config import Settings
from app.search import (
    InvalidSearchInputError,
    QdrantSearcher,
    QueryEmbeddingError,
    SearchService,
)


def make_settings(dimensions: int = 2) -> Settings:
    return Settings(
        qdrant_url="http://localhost:6333",
        qdrant_collection="documents",
        openai_api_key="test-key",
        embedding_model="text-embedding-3-small",
        embedding_dimensions=dimensions,
        embedding_batch_size=100,
    )


@pytest.fixture
def client() -> QdrantClient:
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
                    "content": "Python FastAPI 백엔드",
                    "source": "backend.md",
                    "section": "기술",
                    "chunk_id": "chunk-1",
                },
            ),
            models.PointStruct(
                id=2,
                vector=[0.8, 0.2],
                payload={
                    "content": "REST API 개발",
                    "source": "project.md",
                    "section": "구현",
                    "chunk_id": "chunk-2",
                },
            ),
            models.PointStruct(
                id=3,
                vector=[0.0, 1.0],
                payload={
                    "content": "무관한 내용",
                    "source": "other.md",
                    "section": "기타",
                    "chunk_id": "chunk-3",
                },
            ),
        ],
        wait=True,
    )
    return client


def test_search_returns_score_order_and_preserves_source_metadata(
    client: QdrantClient,
) -> None:
    results = QdrantSearcher(client, "documents").search([1.0, 0.0], top_k=2)

    assert [result.source for result in results] == ["backend.md", "project.md"]
    assert results[0].score >= results[1].score
    assert results[0].content == "Python FastAPI 백엔드"
    assert results[0].metadata == {"section": "기술", "chunk_id": "chunk-1"}


def test_manual_searcher_reads_langchain_nested_metadata() -> None:
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
                    "content": "중첩 metadata 문서",
                    "metadata": {"source": "nested.md", "section": "기술"},
                },
            )
        ],
        wait=True,
    )

    result = QdrantSearcher(client, "documents").search([1.0, 0.0])[0]

    assert result.source == "nested.md"
    assert result.metadata == {"section": "기술"}


def test_top_k_and_threshold_change_results(client: QdrantClient) -> None:
    searcher = QdrantSearcher(client, "documents")

    assert len(searcher.search([1.0, 0.0], top_k=1)) == 1
    assert len(searcher.search([1.0, 0.0], top_k=3)) == 3
    assert len(
        searcher.search([1.0, 0.0], top_k=3, score_threshold=0.99)
    ) == 1


def test_high_threshold_can_return_no_evidence(client: QdrantClient) -> None:
    results = QdrantSearcher(client, "documents").search(
        [0.7, 0.7], top_k=3, score_threshold=0.999
    )

    assert results == []


def test_search_rejects_invalid_options(client: QdrantClient) -> None:
    searcher = QdrantSearcher(client, "documents")

    with pytest.raises(InvalidSearchInputError, match="top_k"):
        searcher.search([1.0, 0.0], top_k=0)
    with pytest.raises(InvalidSearchInputError, match="threshold"):
        searcher.search([1.0, 0.0], score_threshold=1.1)


def test_service_embeds_question_once_and_forwards_options(client: QdrantClient) -> None:
    openai_client = Mock()
    openai_client.embeddings.create.return_value = SimpleNamespace(
        data=[SimpleNamespace(embedding=[1.0, 0.0])]
    )
    service = SearchService(
        QdrantSearcher(client, "documents"), openai_client, make_settings()
    )

    results = service.search("백엔드 경험은?", top_k=1, score_threshold=0.5)

    assert len(results) == 1
    openai_client.embeddings.create.assert_called_once_with(
        model="text-embedding-3-small",
        input=["백엔드 경험은?"],
        dimensions=2,
    )


def test_service_rejects_empty_query_and_wrong_embedding_dimension(
    client: QdrantClient,
) -> None:
    openai_client = Mock()
    openai_client.embeddings.create.return_value = SimpleNamespace(
        data=[SimpleNamespace(embedding=[1.0])]
    )
    service = SearchService(
        QdrantSearcher(client, "documents"), openai_client, make_settings()
    )

    with pytest.raises(InvalidSearchInputError, match="query"):
        service.search("   ")
    with pytest.raises(QueryEmbeddingError, match="dimension"):
        service.search("질문")
