from unittest.mock import Mock

from fastapi.testclient import TestClient

from app.main import app, get_search_service
from app.langchain_retrieval import SearchFilters
from app.search import SearchResult


def test_search_api_returns_retrieval_without_generated_answer() -> None:
    service = Mock()
    service.search.return_value = [
        SearchResult(
            content="검색된 원문",
            source="source.md",
            score=0.91,
            metadata={"section": "성과", "chunk_id": "chunk-1"},
        )
    ]
    app.dependency_overrides[get_search_service] = lambda: service
    try:
        response = TestClient(app).post(
            "/search",
            json={
                "query": "어떤 성과가 있나요?",
                "top_k": 3,
                "score_threshold": 0.7,
                "filters": {"document_type": "project", "source": "source.md"},
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "query": "어떤 성과가 있나요?",
        "results": [
            {
                "content": "검색된 원문",
                "source": "source.md",
                "score": 0.91,
                "metadata": {"section": "성과", "chunk_id": "chunk-1"},
            }
        ],
    }
    assert "answer" not in response.json()
    service.search.assert_called_once_with(
        "어떤 성과가 있나요?",
        top_k=3,
        score_threshold=0.7,
        filters=SearchFilters(document_type="project", source="source.md"),
    )


def test_search_api_validates_top_k_and_threshold() -> None:
    client = TestClient(app)

    assert client.post("/search", json={"query": "질문", "top_k": 0}).status_code == 422
    assert (
        client.post(
            "/search", json={"query": "질문", "score_threshold": 1.1}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/search", json={"query": "질문", "filters": {"source": ""}}
        ).status_code
        == 422
    )
