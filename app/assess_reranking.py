import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).parents[1]
BASELINE_PATH = PROJECT_ROOT / "data" / "evaluation" / "baseline.json"
HYBRID_PATH = PROJECT_ROOT / "data" / "evaluation" / "hybrid-comparison.json"
OUTPUT_PATH = PROJECT_ROOT / "data" / "evaluation" / "reranking-assessment.json"


@dataclass(frozen=True)
class RerankingAssessment:
    decision: str
    reason: str
    baseline_mrr: float
    hybrid_exact_keyword_mrr: float
    rank_improvement_headroom: float
    evaluated_question_count: int


def assess_reranking(
    baseline: dict[str, Any], hybrid: dict[str, Any]
) -> RerankingAssessment:
    """현재 순위 지표에 reranker가 개선할 여지가 있는지 판단한다."""
    ranks = [
        case["hybrid_first_relevant_rank"]
        for case in hybrid["cases"]
        if case["hybrid_first_relevant_rank"] is not None
    ]
    if not ranks:
        raise ValueError("hybrid report has no answerable cases")

    hybrid_mrr = sum(1.0 / rank for rank in ranks) / len(ranks)
    baseline_mrr = float(baseline["mean_reciprocal_rank"])
    headroom = max(0.0, 1.0 - hybrid_mrr)
    should_defer = baseline_mrr == 1.0 and headroom == 0.0
    return RerankingAssessment(
        decision="defer" if should_defer else "evaluate_model",
        reason=(
            "기준선과 Hybrid 평가에서 기대 출처가 이미 모두 1위라 순위 지표의 "
            "추가 개선 여지가 없다."
            if should_defer
            else "기대 출처가 1위가 아닌 사례가 있어 reranker 비교 평가가 필요하다."
        ),
        baseline_mrr=baseline_mrr,
        hybrid_exact_keyword_mrr=hybrid_mrr,
        rank_improvement_headroom=headroom,
        evaluated_question_count=len(ranks),
    )


def build_report(
    baseline: dict[str, Any], hybrid: dict[str, Any]
) -> dict[str, Any]:
    assessment = assess_reranking(baseline, hybrid)
    return {
        "assessment": asdict(assessment),
        "before_reranking": [
            {
                "question_id": case["question_id"],
                "hybrid_sources": case["hybrid_sources"],
                "first_relevant_rank": case["hybrid_first_relevant_rank"],
            }
            for case in hybrid["cases"]
        ],
        # 이번 판단에서는 모델을 적용하지 않았으므로 가상의 after 순위를 만들지 않는다.
        "after_reranking": None,
        "candidates": [
            {
                "type": "hosted_cross_encoder",
                "cost": "요청별 외부 API 비용과 문서 외부 전송",
                "decision": "not_selected",
            },
            {
                "type": "local_cross_encoder",
                "cost": "모델 의존성·다운로드·추론 시간 증가",
                "decision": "not_selected",
            },
            {
                "type": "lexical_heuristic",
                "cost": "낮음",
                "decision": "not_selected",
                "reason": "이미 사용 중인 Sparse 신호를 반복해 독립적인 관련성 판단이 아니다.",
            },
        ],
        "external_api_calls": 0,
        "new_dependencies": [],
        "reconsider_when": [
            "Hybrid 평가에서 기대 출처가 1위가 아닌 질문이 생길 때",
            "Chunk 단위 relevance 정답을 마련해 precision 개선을 측정할 수 있을 때",
            "문서 수 증가로 초기 후보의 관련 없는 Chunk가 답변 품질을 낮출 때",
        ],
    }


def main() -> None:
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    hybrid = json.loads(HYBRID_PATH.read_text(encoding="utf-8"))
    report = build_report(baseline, hybrid)
    OUTPUT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    assessment = report["assessment"]
    print(
        f"decision={assessment['decision']} "
        f"baseline_mrr={assessment['baseline_mrr']:.3f} "
        f"hybrid_mrr={assessment['hybrid_exact_keyword_mrr']:.3f} "
        f"headroom={assessment['rank_improvement_headroom']:.3f}"
    )
    print(f"report={OUTPUT_PATH}")


if __name__ == "__main__":
    main()
