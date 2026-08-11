import json
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

from app.answers import AnswerResult


class AnswerPipeline(Protocol):
    """수동 서비스와 LangChain 서비스가 공유하는 평가용 최소 계약."""

    def answer(self, query: str, *, top_k: int | None = None) -> AnswerResult: ...


@dataclass(frozen=True)
class EvaluationQuestion:
    id: str
    category: str
    question: str
    expected_sources: tuple[str, ...]
    answerable: bool


@dataclass(frozen=True)
class CaseMetrics:
    question_id: str
    category: str
    retrieval_sources: tuple[str, ...]
    answer_sources: tuple[str, ...]
    hit_at_k: bool | None
    first_relevant_rank: int | None
    reciprocal_rank: float | None
    unexpected_sources: tuple[str, ...]
    source_recall: float
    refusal_correct: bool
    answer_sources_correct: bool
    generated: bool


@dataclass(frozen=True)
class PipelineMetrics:
    cases: tuple[CaseMetrics, ...]
    mean_source_recall: float
    hit_at_k: float
    mean_reciprocal_rank: float
    refusal_accuracy: float
    answer_source_accuracy: float
    embedding_calls: int
    generation_calls: int


@dataclass(frozen=True)
class ComparisonReport:
    manual: PipelineMetrics
    langchain: PipelineMetrics


def load_evaluation_questions(path: Path) -> list[EvaluationQuestion]:
    """JSON 평가 집합을 실행 중 변경되지 않는 모델로 변환한다."""
    items = json.loads(path.read_text(encoding="utf-8"))
    return [
        EvaluationQuestion(
            id=item["id"],
            category=item["category"],
            question=item["question"],
            expected_sources=tuple(item["expected_sources"]),
            answerable=item["answerable"],
        )
        for item in items
    ]


def compare_pipelines(
    questions: Sequence[EvaluationQuestion],
    manual: AnswerPipeline,
    langchain: AnswerPipeline,
    *,
    top_k: int | None = None,
) -> ComparisonReport:
    """동일한 질문 순서와 옵션으로 두 파이프라인을 각각 평가한다."""
    return ComparisonReport(
        manual=evaluate_pipeline(
            questions, manual, top_k=top_k
        ),
        langchain=evaluate_pipeline(
            questions, langchain, top_k=top_k
        ),
    )


def evaluate_pipeline(
    questions: Sequence[EvaluationQuestion],
    pipeline: AnswerPipeline,
    *,
    top_k: int | None = None,
) -> PipelineMetrics:
    """하나의 RAG 경로를 검색 지표와 답변 지표로 나누어 평가한다."""
    return _evaluate(
        questions,
        lambda query: pipeline.answer(query, top_k=top_k),
    )


def report_to_dict(report: ComparisonReport) -> dict:
    """평가 결과를 JSON으로 기록할 수 있는 기본 타입으로 변환한다."""
    return asdict(report)


def _evaluate(
    questions: Sequence[EvaluationQuestion],
    run: Callable[[str], AnswerResult],
) -> PipelineMetrics:
    cases = tuple(_score_case(question, run(question.question)) for question in questions)
    count = len(cases)
    if count == 0:
        raise ValueError("questions must not be empty")
    answerable_cases = tuple(case for case in cases if case.hit_at_k is not None)
    if not answerable_cases:
        raise ValueError("at least one answerable question is required")
    return PipelineMetrics(
        cases=cases,
        mean_source_recall=sum(case.source_recall for case in cases) / count,
        hit_at_k=(
            sum(bool(case.hit_at_k) for case in answerable_cases)
            / len(answerable_cases)
        ),
        mean_reciprocal_rank=(
            sum(case.reciprocal_rank or 0.0 for case in answerable_cases)
            / len(answerable_cases)
        ),
        refusal_accuracy=sum(case.refusal_correct for case in cases) / count,
        answer_source_accuracy=(
            sum(case.answer_sources_correct for case in cases) / count
        ),
        # 현재 두 검색 경로 모두 질문 하나마다 Embedding API를 한 번 호출한다.
        embedding_calls=count,
        # 근거 부족 분기는 모델 호출 전이므로 실제 생성된 경우만 과금 범위에 센다.
        generation_calls=sum(case.generated for case in cases),
    )


def _score_case(
    question: EvaluationQuestion, result: AnswerResult
) -> CaseMetrics:
    retrieval_sources = tuple(dict.fromkeys(item.source for item in result.retrieval))
    expected = set(question.expected_sources)
    retrieved = set(retrieval_sources)
    answer_sources = set(result.sources)
    first_relevant_rank = next(
        (
            rank
            for rank, source in enumerate(retrieval_sources, start=1)
            if source in expected
        ),
        None,
    )
    source_recall = len(expected & retrieved) / len(expected) if expected else 1.0
    refusal_correct = result.generated is question.answerable
    # 답변 불가 질문은 출처 없이 거절해야 하고, 답변 가능 질문은 기대 출처를
    # 모두 사용하면서 관련 없는 출처를 답변 근거로 포함하지 않아야 한다.
    answer_sources_correct = (
        answer_sources == expected if question.answerable else not answer_sources
    )
    return CaseMetrics(
        question_id=question.id,
        category=question.category,
        retrieval_sources=retrieval_sources,
        answer_sources=tuple(result.sources),
        hit_at_k=first_relevant_rank is not None if expected else None,
        first_relevant_rank=first_relevant_rank,
        reciprocal_rank=(
            1.0 / first_relevant_rank if first_relevant_rank is not None else None
        ),
        unexpected_sources=tuple(
            source for source in retrieval_sources if source not in expected
        ),
        source_recall=source_recall,
        refusal_correct=refusal_correct,
        answer_sources_correct=answer_sources_correct,
        generated=result.generated,
    )
