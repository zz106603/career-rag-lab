from unittest.mock import Mock

from fastapi.testclient import TestClient

from app.answers import (
    AnswerGenerationError,
    AnswerResult,
    REFUSAL_ANSWER,
    RetrievalPipelineError,
)
from app.main import app, get_answer_service
from app.search import SearchResult


def test_answer_api_separates_answer_sources_and_retrieval() -> None:
    retrieval = SearchResult(
        content="검색 원문",
        source="project.md",
        score=0.81,
        metadata={"section": "성과"},
    )
    service = Mock()
    service.answer.return_value = AnswerResult(
        status="answered",
        answer="근거 기반 답변",
        sources=["project.md"],
        retrieval=[retrieval],
        generated=True,
    )
    app.dependency_overrides[get_answer_service] = lambda: service
    try:
        response = TestClient(app).post(
            "/answer",
            json={"query": "질문", "top_k": 3, "score_threshold": 0.4},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "status": "answered",
        "answer": "근거 기반 답변",
        "sources": ["project.md"],
        "retrieval": [
            {
                "content": "검색 원문",
                "source": "project.md",
                "score": 0.81,
                "metadata": {"section": "성과"},
            }
        ],
        "generated": True,
    }


def test_answer_api_exposes_refusal_without_generation() -> None:
    service = Mock()
    service.answer.return_value = AnswerResult(
        status="insufficient_evidence",
        answer=REFUSAL_ANSWER,
        sources=[],
        retrieval=[],
        generated=False,
    )
    app.dependency_overrides[get_answer_service] = lambda: service
    try:
        response = TestClient(app).post("/answer", json={"query": "없는 경험"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "insufficient_evidence"
    assert response.json()["generated"] is False
    service.answer.assert_called_once_with(
        "없는 경험", top_k=None, score_threshold=None
    )


def test_answer_api_distinguishes_retrieval_and_generation_failures() -> None:
    client = TestClient(app, raise_server_exceptions=False)
    service = Mock()
    app.dependency_overrides[get_answer_service] = lambda: service
    try:
        service.answer.side_effect = RetrievalPipelineError("hidden retrieval error")
        retrieval_response = client.post("/answer", json={"query": "질문"})

        service.answer.side_effect = AnswerGenerationError("hidden generation error")
        generation_response = client.post("/answer", json={"query": "질문"})
    finally:
        app.dependency_overrides.clear()

    assert retrieval_response.status_code == 502
    assert retrieval_response.json()["detail"]["code"] == "retrieval_failed"
    assert generation_response.status_code == 502
    assert generation_response.json()["detail"]["code"] == "generation_failed"
    assert "hidden" not in retrieval_response.text
    assert "hidden" not in generation_response.text
