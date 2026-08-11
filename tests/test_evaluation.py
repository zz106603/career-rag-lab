from dataclasses import replace

import pytest

from app.answers import AnswerResult, REFUSAL_ANSWER
from app.evaluation import (
    EvaluationQuestion,
    compare_pipelines,
    report_to_dict,
)
from app.evaluate_pipelines import clone_as_langchain_collection
from app.evaluate_baseline import RecordedPipeline
from app.search import SearchResult
from qdrant_client import QdrantClient, models


QUESTIONS = [
    EvaluationQuestion("q1", "semantic", "경험?", ("a.md",), True),
    EvaluationQuestion("q2", "unanswerable", "없는 사실?", (), False),
]


def _result(*, source: str | None, generated: bool) -> AnswerResult:
    retrieval = (
        [SearchResult("근거", source, 0.8, {"section": "경험"})]
        if source
        else []
    )
    return AnswerResult(
        status="answered" if generated else "insufficient_evidence",
        answer="답변" if generated else REFUSAL_ANSWER,
        sources=[source] if source and generated else [],
        retrieval=retrieval,
        generated=generated,
    )


class StubPipeline:
    def __init__(self, results: dict[str, AnswerResult]) -> None:
        self.results = results
        self.calls: list[tuple[str, int | None]] = []

    def answer(self, query: str, *, top_k: int | None = None) -> AnswerResult:
        self.calls.append((query, top_k))
        return self.results[query]


def test_compare_pipelines_records_side_by_side_metrics_and_api_scope() -> None:
    correct = StubPipeline(
        {"경험?": _result(source="a.md", generated=True), "없는 사실?": _result(source=None, generated=False)}
    )
    wrong = StubPipeline(
        {"경험?": _result(source="wrong.md", generated=True), "없는 사실?": _result(source="wrong.md", generated=True)}
    )

    report = compare_pipelines(QUESTIONS, correct, wrong, top_k=3)

    assert report.manual.mean_source_recall == 1.0
    assert report.manual.hit_at_k == 1.0
    assert report.manual.mean_reciprocal_rank == 1.0
    assert report.manual.refusal_accuracy == 1.0
    assert report.manual.answer_source_accuracy == 1.0
    assert report.manual.embedding_calls == 2
    assert report.manual.generation_calls == 1
    assert report.langchain.mean_source_recall == 0.5
    assert report.langchain.hit_at_k == 0.0
    assert report.langchain.mean_reciprocal_rank == 0.0
    assert report.langchain.refusal_accuracy == 0.5
    assert report.langchain.answer_source_accuracy == 0.0
    assert correct.calls == [("경험?", 3), ("없는 사실?", 3)]
    assert wrong.calls == correct.calls


def test_source_recall_requires_all_expected_documents() -> None:
    question = replace(QUESTIONS[0], expected_sources=("a.md", "b.md"))
    pipeline = StubPipeline({"경험?": _result(source="a.md", generated=True)})

    report = compare_pipelines([question], pipeline, pipeline)

    assert report.manual.cases[0].source_recall == 0.5
    assert report.manual.cases[0].hit_at_k is True
    assert report.manual.cases[0].first_relevant_rank == 1
    assert report.manual.cases[0].reciprocal_rank == 1.0
    assert report.manual.cases[0].answer_sources_correct is False


def test_empty_question_set_is_rejected() -> None:
    pipeline = StubPipeline({})

    with pytest.raises(ValueError, match="questions must not be empty"):
        compare_pipelines([], pipeline, pipeline)


def test_report_is_json_compatible_shape() -> None:
    pipeline = StubPipeline(
        {"경험?": _result(source="a.md", generated=True), "없는 사실?": _result(source=None, generated=False)}
    )

    data = report_to_dict(compare_pipelines(QUESTIONS, pipeline, pipeline))

    assert data["manual"]["cases"][0]["question_id"] == "q1"
    assert data["langchain"]["embedding_calls"] == 2


def test_rank_and_unexpected_sources_are_recorded() -> None:
    result = AnswerResult(
        status="answered",
        answer="답변",
        sources=["a.md"],
        retrieval=[
            SearchResult("오검색", "wrong.md", 0.9, {}),
            SearchResult("정답", "a.md", 0.8, {}),
        ],
        generated=True,
    )
    pipeline = StubPipeline({"경험?": result})

    report = compare_pipelines([QUESTIONS[0]], pipeline, pipeline)
    case = report.manual.cases[0]

    assert case.first_relevant_rank == 2
    assert case.reciprocal_rank == 0.5
    assert case.unexpected_sources == ("wrong.md",)


def test_recorded_pipeline_reuses_actual_case_without_api_call() -> None:
    pipeline = RecordedPipeline(
        [
            {
                "question_id": "q1",
                "retrieval_sources": ["a.md", "wrong.md"],
                "answer_sources": ["a.md"],
                "generated": True,
            }
        ]
    ).bind_questions([QUESTIONS[0]])

    result = pipeline.answer("경험?", top_k=1)

    assert result.generated is True
    assert result.sources == ["a.md"]
    assert [item.source for item in result.retrieval] == ["a.md"]


def test_clone_reuses_vectors_and_nests_langchain_metadata() -> None:
    client = QdrantClient(":memory:")
    client.create_collection(
        "manual",
        vectors_config=models.VectorParams(size=2, distance=models.Distance.COSINE),
    )
    client.upsert(
        "manual",
        points=[
            models.PointStruct(
                id=1,
                vector=[1.0, 0.0],
                payload={"content": "근거", "source": "a.md", "section": "경험"},
            )
        ],
        wait=True,
    )

    clone_as_langchain_collection(
        client, source="manual", target="langchain", vector_size=2
    )

    points, _ = client.scroll("langchain", with_vectors=True)
    assert points[0].vector == [1.0, 0.0]
    assert points[0].payload == {
        "content": "근거",
        "metadata": {"source": "a.md", "section": "경험"},
    }
