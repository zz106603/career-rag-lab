from unittest.mock import Mock

from fastapi.testclient import TestClient

from app.langchain_retrieval import SearchFilters
from app.main import app, get_keyword_search_service, get_sparse_search_service
from app.search import SearchResult


def test_keyword_search_api_keeps_results_separate_from_dense_search() -> None:
    service = Mock()
    service.search.return_value = [
        SearchResult("Playwright 근거", "dashboard.md", 0.51, {"matched_terms": ["playwright"]})
    ]
    app.dependency_overrides[get_keyword_search_service] = lambda: service
    try:
        response = TestClient(app).post(
            "/search/keyword",
            json={
                "query": "Playwright를 어디에 사용했나요?",
                "top_k": 3,
                "filters": {"document_type": "project"},
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["results"][0]["metadata"]["matched_terms"] == [
        "playwright"
    ]
    service.search.assert_called_once_with(
        "Playwright를 어디에 사용했나요?",
        top_k=3,
        filters=SearchFilters(document_type="project"),
    )


def test_sparse_search_api_keeps_results_separate() -> None:
    service = Mock()
    service.search.return_value = [
        SearchResult("Celery 근거", "project.md", 1.2, {})
    ]
    app.dependency_overrides[get_sparse_search_service] = lambda: service
    try:
        response = TestClient(app).post(
            "/search/sparse", json={"query": "Celery를 적용한 이유는?", "top_k": 3}
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["results"][0]["source"] == "project.md"
