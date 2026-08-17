import argparse
import json
from pathlib import Path

from app.evaluation import load_evaluation_questions
from app.hybrid_search import create_hybrid_search_service
from app.hybrid_search import HybridSearchService
from app.search import SearchResult


PROJECT_ROOT = Path(__file__).parents[1]
QUESTIONS_PATH = PROJECT_ROOT / "data" / "evaluation" / "questions.json"
OUTPUT_PATH = PROJECT_ROOT / "data" / "evaluation" / "hybrid-comparison.json"
RECORDED_PATH = PROJECT_ROOT / "data" / "evaluation" / "keyword-comparison.json"


class RecordedSearchService:
    def __init__(self, sources_by_query: dict[str, list[str]], search_type: str) -> None:
        self.sources_by_query = sources_by_query
        self.search_type = search_type

    def search(self, query: str, *, top_k: int, filters=None) -> list[SearchResult]:
        # 이전 평가 파일은 동일 문서의 여러 청크를 source 단위로 기록했다.
        # 한 검색기의 중복 문서가 RRF 점수를 여러 번 받지 않도록 먼저 제거한다.
        unique_sources = list(dict.fromkeys(self.sources_by_query[query]))
        return [
            SearchResult(
                content=f"기록된 {self.search_type} 결과: {source}",
                source=source,
                score=1.0 / rank,
                # 저장된 보고서는 Chunk가 아닌 source 순위이므로 같은 source를
                # 두 검색에서 같은 후보로 융합한다.
                metadata={"chunk_id": source},
            )
            for rank, source in enumerate(
                unique_sources[:top_k], start=1
            )
        ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Dense·Sparse Hybrid 순위 비교")
    parser.add_argument("--live-api", action="store_true")
    args = parser.parse_args()
    questions = [
        item
        for item in load_evaluation_questions(QUESTIONS_PATH)
        if item.category == "exact_keyword"
    ]
    if args.live_api:
        service = create_hybrid_search_service()
        evaluation_mode = "live_chunk_ranks"
        embedding_calls = len(questions)
    else:
        recorded = json.loads(RECORDED_PATH.read_text(encoding="utf-8"))
        cases_by_id = {item["question_id"]: item for item in recorded["cases"]}
        dense = {
            question.question: cases_by_id[question.id]["dense_sources"]
            for question in questions
        }
        sparse = {
            question.question: cases_by_id[question.id]["sparse_sources"]
            for question in questions
        }
        service = HybridSearchService(
            RecordedSearchService(dense, "dense"),
            RecordedSearchService(sparse, "sparse"),
        )
        evaluation_mode = "recorded_actual_source_ranks"
        embedding_calls = 0
    cases = []
    for question in questions:
        result = service.search(question.question, top_k=3, candidate_k=6)
        expected = set(question.expected_sources)
        dense_sources = _unique_sources(result.dense)
        sparse_sources = _unique_sources(result.sparse)
        hybrid_sources = _unique_sources(result.hybrid)
        cases.append(
            {
                "question_id": question.id,
                "question": question.question,
                "expected_sources": list(question.expected_sources),
                "dense_sources": dense_sources,
                "sparse_sources": sparse_sources,
                "hybrid_sources": hybrid_sources,
                "dense_first_relevant_rank": _first_rank(dense_sources, expected),
                "sparse_first_relevant_rank": _first_rank(sparse_sources, expected),
                "hybrid_first_relevant_rank": _first_rank(hybrid_sources, expected),
                "hybrid_results": [
                    {
                        "source": item.source,
                        "rrf_score": item.score,
                        "dense_rank": item.metadata["dense_rank"],
                        "sparse_rank": item.metadata["sparse_rank"],
                    }
                    for item in result.hybrid
                ],
            }
        )
    report = {
        "scope": "exact_keyword",
        "evaluation_mode": evaluation_mode,
        "fusion": {"method": "rrf", "k": 60, "weights": {"dense": 1, "sparse": 1}},
        "top_k": 3,
        "candidate_k": 6,
        "embedding_calls": embedding_calls,
        "generation_calls": 0,
        "cases": cases,
    }
    OUTPUT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for case in cases:
        print(
            f"{case['question_id']} dense={case['dense_first_relevant_rank']} "
            f"sparse={case['sparse_first_relevant_rank']} "
            f"hybrid={case['hybrid_first_relevant_rank']} "
            f"sources={case['hybrid_sources']}"
        )
    print(f"report={OUTPUT_PATH}")


def _unique_sources(results) -> list[str]:
    return list(dict.fromkeys(item.source for item in results))


def _first_rank(sources: list[str], expected: set[str]) -> int | None:
    return next(
        (rank for rank, source in enumerate(sources, start=1) if source in expected),
        None,
    )


if __name__ == "__main__":
    main()
