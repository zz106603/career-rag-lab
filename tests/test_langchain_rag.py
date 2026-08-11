from types import SimpleNamespace
from unittest.mock import Mock

from langchain_core.runnables import RunnableLambda
import pytest

from app.answers import (
    REFUSAL_ANSWER,
    AnswerGenerationError,
    AnswerService,
    RetrievalPipelineError,
)
from app.langchain_rag import LangChainRagService
from app.search import SearchResult
from tests.test_answers import make_settings


def make_result(
    score: float, source: str = "project.md", content: str = "근거 내용"
) -> SearchResult:
    return SearchResult(
        content=content,
        source=source,
        score=score,
        metadata={"section": "성과", "chunk_id": f"chunk-{score}"},
    )


class RecordingModel:
    def __init__(self, output: str = "근거 기반 답변") -> None:
        self.output = output
        self.prompts: list[str] = []

    def runnable(self) -> RunnableLambda:
        def invoke(prompt: object) -> str:
            self.prompts.append(prompt.to_string())
            return self.output

        return RunnableLambda(invoke)


def test_chain_preserves_retrieval_filters_evidence_and_generates_answer() -> None:
    retrieval_service = Mock()
    high = make_result(0.8, content="장애 대응을 자동화했다.")
    low = make_result(0.2, source="other.md", content="관련 없는 내용")
    retrieval_service.search.return_value = [high, low]
    model = RecordingModel()
    service = LangChainRagService(
        retrieval_service, model.runnable(), make_settings()
    )

    result = service.answer("장애 대응 경험은?", top_k=2, score_threshold=0.4)

    assert result.status == "answered"
    assert result.answer == "근거 기반 답변"
    assert result.sources == ["project.md"]
    assert result.retrieval == [high, low]
    assert result.generated is True
    retrieval_service.search.assert_called_once_with("장애 대응 경험은?", top_k=2)
    assert "장애 대응을 자동화했다." in model.prompts[0]
    assert "관련 없는 내용" not in model.prompts[0]


def test_chain_skips_generation_when_evidence_is_insufficient() -> None:
    retrieval_service = Mock()
    low = make_result(0.2)
    retrieval_service.search.return_value = [low]
    model = RecordingModel()
    service = LangChainRagService(
        retrieval_service, model.runnable(), make_settings()
    )

    result = service.answer("문서에 없는 경험은?", score_threshold=0.4)

    assert result.status == "insufficient_evidence"
    assert result.answer == REFUSAL_ANSWER
    assert result.sources == []
    assert result.retrieval == [low]
    assert result.generated is False
    assert model.prompts == []


def test_chain_deduplicates_sources_in_evidence_order() -> None:
    retrieval_service = Mock()
    retrieval_service.search.return_value = [
        make_result(0.9, "first.md"),
        make_result(0.8, "first.md"),
        make_result(0.7, "second.md"),
    ]
    service = LangChainRagService(
        retrieval_service, RecordingModel().runnable(), make_settings()
    )

    result = service.answer("질문")

    assert result.sources == ["first.md", "second.md"]


def test_chain_distinguishes_retrieval_and_generation_failures() -> None:
    retrieval_service = Mock()
    retrieval_service.search.side_effect = RuntimeError("qdrant unavailable")
    service = LangChainRagService(
        retrieval_service, RecordingModel().runnable(), make_settings()
    )

    with pytest.raises(RetrievalPipelineError):
        service.answer("질문")

    retrieval_service.search.side_effect = None
    retrieval_service.search.return_value = [make_result(0.8)]

    def fail_generation(_: object) -> str:
        raise RuntimeError("openai unavailable")

    service = LangChainRagService(
        retrieval_service, RunnableLambda(fail_generation), make_settings()
    )
    with pytest.raises(AnswerGenerationError):
        service.answer("질문")


def test_chain_rejects_empty_generation() -> None:
    retrieval_service = Mock()
    retrieval_service.search.return_value = [make_result(0.8)]
    service = LangChainRagService(
        retrieval_service, RecordingModel("  ").runnable(), make_settings()
    )

    with pytest.raises(AnswerGenerationError, match="empty"):
        service.answer("질문")


def test_manual_and_langchain_services_keep_same_answer_result_contract() -> None:
    evidence = [make_result(0.8)]
    manual_retrieval = Mock()
    manual_retrieval.search.return_value = evidence
    openai_client = Mock()
    openai_client.responses.create.return_value = SimpleNamespace(
        output_text="같은 답변"
    )
    manual = AnswerService(manual_retrieval, openai_client, make_settings())

    langchain_retrieval = Mock()
    langchain_retrieval.search.return_value = evidence
    langchain = LangChainRagService(
        langchain_retrieval, RecordingModel("같은 답변").runnable(), make_settings()
    )

    assert langchain.answer("질문") == manual.answer("질문")
