import json
from pathlib import Path

from app.evaluation import load_evaluation_questions
from app.keyword_search import create_keyword_search_service
from app.sparse_search import create_sparse_search_service


PROJECT_ROOT = Path(__file__).parents[1]
QUESTIONS_PATH = PROJECT_ROOT / "data" / "evaluation" / "questions.json"
BASELINE_PATH = PROJECT_ROOT / "data" / "evaluation" / "baseline.json"
OUTPUT_PATH = PROJECT_ROOT / "data" / "evaluation" / "keyword-comparison.json"


def main() -> None:
    questions = [
        item
        for item in load_evaluation_questions(QUESTIONS_PATH)
        if item.category == "exact_keyword"
    ]
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    dense_by_id = {item["question_id"]: item for item in baseline["cases"]}
    service = create_keyword_search_service()
    sparse_service = create_sparse_search_service()
    cases = []
    for question in questions:
        keyword_results = service.search(question.question, top_k=3)
        sparse_results = sparse_service.search(question.question, top_k=3)
        keyword_sources = [item.source for item in keyword_results]
        sparse_sources = [item.source for item in sparse_results]
        expected = set(question.expected_sources)
        cases.append(
            {
                "question_id": question.id,
                "question": question.question,
                "expected_sources": list(question.expected_sources),
                "dense_sources": dense_by_id[question.id]["retrieval_sources"],
                "keyword_sources": keyword_sources,
                "sparse_sources": sparse_sources,
                "keyword_first_relevant_rank": next(
                    (
                        rank
                        for rank, source in enumerate(keyword_sources, start=1)
                        if source in expected
                    ),
                    None,
                ),
                "keyword_results": [
                    {
                        "source": item.source,
                        "score": item.score,
                        "matched_terms": item.metadata["matched_terms"],
                    }
                    for item in keyword_results
                ],
                "sparse_first_relevant_rank": next(
                    (
                        rank
                        for rank, source in enumerate(sparse_sources, start=1)
                        if source in expected
                    ),
                    None,
                ),
                "sparse_results": [
                    {"source": item.source, "score": item.score}
                    for item in sparse_results
                ],
            }
        )
    report = {
        "scope": "exact_keyword",
        "top_k": 3,
        "external_api_calls": 0,
        "cases": cases,
    }
    OUTPUT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for case in cases:
        print(
            f"{case['question_id']} dense={case['dense_sources']} "
            f"keyword={case['keyword_sources']} "
            f"keyword_rank={case['keyword_first_relevant_rank']} "
            f"sparse={case['sparse_sources']} "
            f"sparse_rank={case['sparse_first_relevant_rank']}"
        )
    print(f"report={OUTPUT_PATH}")


if __name__ == "__main__":
    main()
