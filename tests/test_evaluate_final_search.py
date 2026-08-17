from app.evaluate_final_search import evaluate_final_search, fuse_source_ranks
from app.evaluation import EvaluationQuestion


def test_fuse_source_ranks_promotes_source_found_by_both_searches() -> None:
    result = fuse_source_ranks(
        ["expected.md", "dense-only.md"],
        ["sparse-only.md", "expected.md"],
    )

    assert result[0] == "expected.md"
    assert result == fuse_source_ranks(
        ["expected.md", "dense-only.md"],
        ["sparse-only.md", "expected.md"],
    )


def test_evaluate_final_search_records_question_changes_and_metrics() -> None:
    questions = [
        EvaluationQuestion("q1", "multi_document", "query", ("a.md", "b.md"), True),
        EvaluationQuestion("q2", "unanswerable", "unknown", (), False),
    ]
    baseline = {
        "refusal_accuracy": 0.8,
        "answer_source_accuracy": 0.4,
        "cases": [
            {"question_id": "q1", "retrieval_sources": ["a.md", "other.md"]},
            {"question_id": "q2", "retrieval_sources": ["other.md"]},
        ]
    }

    report = evaluate_final_search(
        questions,
        baseline,
        lambda question: ["b.md", "a.md"] if question.id == "q1" else [],
    )

    assert report["baseline"]["mean_source_recall"] == 0.5
    assert report["hybrid"]["mean_source_recall"] == 1.0
    assert report["change_counts"] == {
        "improved": 1,
        "worsened": 0,
        "unchanged": 0,
        "not_scored": 1,
    }
    assert report["embedding_calls"] == 0
    assert report["remaining_failures"] == []
    assert report["recorded_generation_baseline"]["recomputed"] is False
    assert report["recommended_settings"]["reranker"] == "보류"
