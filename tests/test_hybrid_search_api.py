from unittest.mock import Mock

from fastapi.testclient import TestClient

from app.hybrid_search import HybridSearchResult
from app.langchain_retrieval import SearchFilters
from app.main import app, get_hybrid_search_service
from app.search import SearchResult


def test_hybrid_api_returns_component_and_fused_results() -> None:
    dense = SearchResult("Dense", "dense.md", 0.8, {"chunk_id": "dense"})
    sparse = SearchResult("Sparse", "sparse.md", 2.0, {"chunk_id": "sparse"})
    fused = SearchResult(
        "Dense", "dense.md", 0.02, {"fusion_method": "rrf"}
    )
    service = Mock()
    service.search.return_value = HybridSearchResult([dense], [sparse], [fused])
    app.dependency_overrides[get_hybrid_search_service] = lambda: service
    try:
        response = TestClient(app).post(
            "/search/hybrid",
            json={
                "query": "RabbitMQ 경험",
                "top_k": 3,
                "candidate_k": 6,
                "filters": {"document_type": "project"},
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["dense"][0]["source"] == "dense.md"
    assert response.json()["sparse"][0]["source"] == "sparse.md"
    assert response.json()["hybrid"][0]["metadata"]["fusion_method"] == "rrf"
    service.search.assert_called_once_with(
        "RabbitMQ 경험",
        top_k=3,
        candidate_k=6,
        filters=SearchFilters(document_type="project"),
    )
