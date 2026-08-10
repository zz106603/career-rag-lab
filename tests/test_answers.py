from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.answers import (
    ANSWER_INSTRUCTIONS,
    REFUSAL_ANSWER,
    AnswerGenerationError,
    AnswerService,
    RetrievalPipelineError,
    build_answer_prompt,
)
from app.config import Settings
from app.search import SearchResult


def make_settings() -> Settings:
    return Settings(
        qdrant_url="http://localhost:6333",
        qdrant_collection="documents",
        openai_api_key="test-key",
        embedding_model="text-embedding-3-small",
        embedding_dimensions=2,
        embedding_batch_size=100,
        chat_model="gpt-5-nano",
        answer_max_output_tokens=300,
        answer_top_k=3,
        answer_score_threshold=0.4,
    )


def make_result(
    score: float, source: str = "project.md", content: str = "근거 내용"
) -> SearchResult:
    return SearchResult(
        content=content,
        source=source,
        score=score,
        metadata={"section": "성과", "chunk_id": f"chunk-{score}"},
    )


def test_answer_uses_only_evidence_above_threshold_and_returns_retrieval() -> None:
    search_service = Mock()
    high = make_result(0.8, content="장애 대응을 자동화했다.")
    low = make_result(0.2, source="other.md", content="관련 없는 내용")
    search_service.search.return_value = [high, low]
    openai_client = Mock()
    openai_client.responses.create.return_value = SimpleNamespace(
        output_text="장애 대응 자동화 경험이 있습니다."
    )
    service = AnswerService(search_service, openai_client, make_settings())

    result = service.answer("장애 대응 경험은?", top_k=2, score_threshold=0.4)

    assert result.status == "answered"
    assert result.generated is True
    assert result.sources == ["project.md"]
    assert result.retrieval == [high, low]
    search_service.search.assert_called_once_with("장애 대응 경험은?", top_k=2)
    call = openai_client.responses.create.call_args.kwargs
    assert call["model"] == "gpt-5-nano"
    assert call["reasoning"] == {"effort": "minimal"}
    assert call["instructions"] == ANSWER_INSTRUCTIONS
    assert call["max_output_tokens"] == 300
    assert "장애 대응을 자동화했다." in call["input"]
    assert "관련 없는 내용" not in call["input"]


def test_insufficient_evidence_skips_generation_but_preserves_retrieval() -> None:
    search_service = Mock()
    low = make_result(0.29)
    search_service.search.return_value = [low]
    openai_client = Mock()
    service = AnswerService(search_service, openai_client, make_settings())

    result = service.answer("AWS 자격 번호는?")

    assert result.status == "insufficient_evidence"
    assert result.answer == REFUSAL_ANSWER
    assert result.sources == []
    assert result.retrieval == [low]
    assert result.generated is False
    openai_client.responses.create.assert_not_called()


def test_no_retrieval_skips_generation() -> None:
    search_service = Mock()
    search_service.search.return_value = []
    openai_client = Mock()

    result = AnswerService(search_service, openai_client, make_settings()).answer(
        "문서에 없는 경험은?"
    )

    assert result.status == "insufficient_evidence"
    openai_client.responses.create.assert_not_called()


def test_duplicate_sources_are_returned_once_in_evidence_order() -> None:
    search_service = Mock()
    search_service.search.return_value = [
        make_result(0.9, "first.md"),
        make_result(0.8, "first.md"),
        make_result(0.7, "second.md"),
    ]
    openai_client = Mock()
    openai_client.responses.create.return_value = SimpleNamespace(output_text="답변")

    result = AnswerService(search_service, openai_client, make_settings()).answer("질문")

    assert result.sources == ["first.md", "second.md"]


def test_retrieval_and_generation_failures_are_distinct() -> None:
    search_service = Mock()
    search_service.search.side_effect = RuntimeError("qdrant unavailable")
    service = AnswerService(search_service, Mock(), make_settings())

    with pytest.raises(RetrievalPipelineError):
        service.answer("질문")

    search_service.search.side_effect = None
    search_service.search.return_value = [make_result(0.8)]
    openai_client = Mock()
    openai_client.responses.create.side_effect = RuntimeError("openai unavailable")
    service = AnswerService(search_service, openai_client, make_settings())

    with pytest.raises(AnswerGenerationError):
        service.answer("질문")


def test_empty_generation_is_rejected() -> None:
    search_service = Mock()
    search_service.search.return_value = [make_result(0.8)]
    openai_client = Mock()
    openai_client.responses.create.return_value = SimpleNamespace(output_text="  ")

    with pytest.raises(AnswerGenerationError, match="empty"):
        AnswerService(search_service, openai_client, make_settings()).answer("질문")


def test_prompt_separates_question_and_evidence_with_source() -> None:
    prompt = build_answer_prompt("무엇을 했나요?", [make_result(0.8)])

    assert prompt.startswith("[질문]\n무엇을 했나요?")
    assert "[검색 근거]\n[검색 근거 1]" in prompt
    assert "출처: project.md" in prompt
    assert "섹션: 성과" in prompt
