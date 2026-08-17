import pytest

from app.assess_reranking import assess_reranking, build_report


def test_defers_reranker_when_relevant_sources_are_already_first() -> None:
    baseline = {"mean_reciprocal_rank": 1.0}
    hybrid = {
        "cases": [
            {
                "question_id": "q1",
                "hybrid_sources": ["expected.md", "other.md"],
                "hybrid_first_relevant_rank": 1,
            }
        ]
    }

    report = build_report(baseline, hybrid)

    assert report["assessment"]["decision"] == "defer"
    assert report["assessment"]["rank_improvement_headroom"] == 0.0
    assert report["after_reranking"] is None
    assert report["external_api_calls"] == 0


def test_requests_model_evaluation_when_hybrid_has_rank_headroom() -> None:
    assessment = assess_reranking(
        {"mean_reciprocal_rank": 1.0},
        {
            "cases": [
                {"hybrid_first_relevant_rank": 1},
                {"hybrid_first_relevant_rank": 2},
            ]
        },
    )

    assert assessment.decision == "evaluate_model"
    assert assessment.hybrid_exact_keyword_mrr == 0.75
    assert assessment.rank_improvement_headroom == 0.25


def test_rejects_report_without_answerable_hybrid_cases() -> None:
    with pytest.raises(ValueError, match="no answerable cases"):
        assess_reranking(
            {"mean_reciprocal_rank": 1.0},
            {"cases": [{"hybrid_first_relevant_rank": None}]},
        )
