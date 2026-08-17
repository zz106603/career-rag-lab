import json
from collections.abc import Callable
from pathlib import Path

from app.evaluation import EvaluationQuestion, load_evaluation_questions
from app.sparse_search import create_sparse_search_service


PROJECT_ROOT = Path(__file__).parents[1]
QUESTIONS_PATH = PROJECT_ROOT / "data" / "evaluation" / "questions.json"
BASELINE_PATH = PROJECT_ROOT / "data" / "evaluation" / "baseline.json"
OUTPUT_PATH = PROJECT_ROOT / "data" / "evaluation" / "final-search-evaluation.json"
RRF_K = 60
TOP_K = 3
CANDIDATE_K = 6


def fuse_source_ranks(
    dense_sources: list[str], sparse_sources: list[str], *, top_k: int = TOP_K
) -> list[str]:
    """서로 다른 score 대신 source 최초 순위로 최종 평가용 RRF를 계산한다."""
    scores: dict[str, float] = {}
    best_ranks: dict[str, int] = {}
    for sources in (dense_sources, sparse_sources):
        for rank, source in enumerate(dict.fromkeys(sources), start=1):
            scores[source] = scores.get(source, 0.0) + 1.0 / (RRF_K + rank)
            best_ranks[source] = min(best_ranks.get(source, rank), rank)
    return sorted(scores, key=lambda source: (-scores[source], best_ranks[source], source))[
        :top_k
    ]


def evaluate_final_search(
    questions: list[EvaluationQuestion],
    baseline: dict,
    sparse_sources_for: Callable[[EvaluationQuestion], list[str]],
) -> dict:
    baseline_by_id = {case["question_id"]: case for case in baseline["cases"]}
    cases = []
    for question in questions:
        before_sources = list(baseline_by_id[question.id]["retrieval_sources"])
        sparse_sources = sparse_sources_for(question)
        hybrid_sources = fuse_source_ranks(before_sources, sparse_sources)
        before = _case_metrics(before_sources, question.expected_sources)
        after = _case_metrics(hybrid_sources, question.expected_sources)
        cases.append(
            {
                "question_id": question.id,
                "category": question.category,
                "answerable": question.answerable,
                "expected_sources": list(question.expected_sources),
                "dense_sources": before_sources,
                "sparse_sources": sparse_sources,
                "hybrid_sources": hybrid_sources,
                "before": before,
                "after": after,
                "change": _classify_change(before, after, question.answerable),
            }
        )

    answerable_cases = [case for case in cases if case["answerable"]]
    remaining_failures = [
        {
            "question_id": case["question_id"],
            "category": case["category"],
            "source_recall": case["after"]["source_recall"],
            "missing_sources": sorted(
                set(case["expected_sources"]) - set(case["hybrid_sources"])
            ),
            "cause": "Top 3 source 후보에 다중 문서 기대 출처가 모두 포함되지 않음",
        }
        for case in answerable_cases
        if case["after"]["source_recall"] < 1.0
    ]
    return {
        "evaluation_mode": "recorded_actual_dense_plus_live_local_sparse_source_rrf",
        "scope": "all_evaluation_questions",
        "fusion": {"method": "rrf", "k": RRF_K, "top_k": TOP_K},
        "embedding_calls": 0,
        "generation_calls": 0,
        "baseline": _summarize(answerable_cases, "before"),
        "hybrid": _summarize(answerable_cases, "after"),
        "recorded_generation_baseline": {
            "refusal_accuracy": baseline["refusal_accuracy"],
            "answer_source_accuracy": baseline["answer_source_accuracy"],
            "recomputed": False,
            "reason": "이번 평가는 검색 결합만 비교하며 생성 API를 다시 호출하지 않음",
        },
        "change_counts": {
            status: sum(case["change"] == status for case in cases)
            for status in ("improved", "worsened", "unchanged", "not_scored")
        },
        "remaining_failures": remaining_failures,
        "recommended_settings": {
            "chunking": "structure_500 유지",
            "retrieval": "Dense + Sparse RRF(k=60)",
            "candidate_k": CANDIDATE_K,
            "top_k": TOP_K,
            "metadata_filter": "질문에서 조건을 명시적으로 알 수 있을 때만 검색 전에 적용",
            "reranker": "보류",
            "generation_guard": "threshold를 통과한 근거가 없으면 생성하지 않음",
        },
        "application_note": (
            "career-fit-ai에서는 검색 근거를 생성 답변과 분리해 관찰하고, "
            "Hybrid 후보 결합 뒤에도 기존 근거 부족 분기를 유지한다."
        ),
        "cases": cases,
    }


def _case_metrics(sources: list[str], expected_sources: tuple[str, ...]) -> dict:
    if not expected_sources:
        return {"first_relevant_rank": None, "reciprocal_rank": None, "source_recall": None}
    expected = set(expected_sources)
    first_rank = next(
        (rank for rank, source in enumerate(sources, 1) if source in expected), None
    )
    return {
        "first_relevant_rank": first_rank,
        "reciprocal_rank": 1.0 / first_rank if first_rank is not None else 0.0,
        "source_recall": len(expected.intersection(sources)) / len(expected),
    }


def _classify_change(before: dict, after: dict, answerable: bool) -> str:
    if not answerable:
        return "not_scored"
    before_quality = before["reciprocal_rank"] + before["source_recall"]
    after_quality = after["reciprocal_rank"] + after["source_recall"]
    if after_quality > before_quality:
        return "improved"
    if after_quality < before_quality:
        return "worsened"
    return "unchanged"


def _summarize(cases: list[dict], key: str) -> dict:
    values = [case[key] for case in cases]
    return {
        "question_count": len(values),
        "hit_at_3": sum(value["first_relevant_rank"] is not None for value in values)
        / len(values),
        "mrr": sum(value["reciprocal_rank"] for value in values) / len(values),
        "mean_source_recall": sum(value["source_recall"] for value in values)
        / len(values),
    }


def main() -> None:
    questions = load_evaluation_questions(QUESTIONS_PATH)
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    sparse_service = create_sparse_search_service()
    report = evaluate_final_search(
        questions,
        baseline,
        lambda question: list(
            dict.fromkeys(
                result.source
                for result in sparse_service.search(question.question, top_k=CANDIDATE_K)
            )
        ),
    )
    OUTPUT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"baseline_mrr={report['baseline']['mrr']:.3f} "
        f"hybrid_mrr={report['hybrid']['mrr']:.3f} "
        f"baseline_recall={report['baseline']['mean_source_recall']:.3f} "
        f"hybrid_recall={report['hybrid']['mean_source_recall']:.3f} "
        f"changes={report['change_counts']}"
    )
    print(f"report={OUTPUT_PATH}")


if __name__ == "__main__":
    main()
