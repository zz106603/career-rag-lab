import argparse
import json
from dataclasses import asdict
from pathlib import Path

from app.answers import AnswerResult, REFUSAL_ANSWER
from app.evaluation import evaluate_pipeline, load_evaluation_questions
from app.pipeline import create_default_answer_service
from app.search import SearchResult


PROJECT_ROOT = Path(__file__).parents[1]
DEFAULT_QUESTIONS = PROJECT_ROOT / "data" / "evaluation" / "questions.json"
DEFAULT_REPORT = PROJECT_ROOT / "data" / "evaluation" / "baseline.json"
DEFAULT_RECORDED_REPORT = (
    PROJECT_ROOT / "data" / "evaluation" / "pipeline-comparison.json"
)


class RecordedPipeline:
    """이미 실제 실행한 결과를 재사용해 외부 API 없이 지표를 계산한다."""

    def __init__(self, cases: list[dict]) -> None:
        self._cases = {case["question_id"]: case for case in cases}
        self._question_ids: dict[str, str] = {}

    def bind_questions(self, questions) -> "RecordedPipeline":
        self._question_ids = {item.question: item.id for item in questions}
        return self

    def answer(self, query: str, *, top_k: int | None = None) -> AnswerResult:
        case = self._cases[self._question_ids[query]]
        sources = list(case["answer_sources"])
        generated = bool(case["generated"])
        retrieval_sources = list(case["retrieval_sources"])
        if top_k is not None:
            retrieval_sources = retrieval_sources[:top_k]
        return AnswerResult(
            status="answered" if generated else "insufficient_evidence",
            answer="기록된 생성 답변" if generated else REFUSAL_ANSWER,
            sources=sources,
            retrieval=[
                SearchResult("기록된 검색 근거", source, 0.0, {})
                for source in retrieval_sources
            ],
            generated=generated,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="LangChain Dense Search 기준선 평가")
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument(
        "--recorded-report", type=Path, default=DEFAULT_RECORDED_REPORT
    )
    parser.add_argument(
        "--live-api",
        action="store_true",
        help="기록 재사용 대신 실제 OpenAI·Qdrant 기본 경로를 다시 실행",
    )
    args = parser.parse_args()

    questions = load_evaluation_questions(args.questions)
    if args.live_api:
        pipeline = create_default_answer_service()
    else:
        recorded = json.loads(args.recorded_report.read_text(encoding="utf-8"))
        pipeline = RecordedPipeline(recorded["langchain"]["cases"]).bind_questions(
            questions
        )
    metrics = evaluate_pipeline(
        questions,
        pipeline,
        top_k=args.top_k,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "evaluation_mode": "live_api" if args.live_api else "recorded_actual_run",
        "top_k": args.top_k,
        **asdict(metrics),
    }
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"hit_at_{args.top_k}={metrics.hit_at_k:.3f}")
    print(f"mrr={metrics.mean_reciprocal_rank:.3f}")
    print(f"answerability_accuracy={metrics.refusal_accuracy:.3f}")
    print(f"source_accuracy={metrics.answer_source_accuracy:.3f}")
    print(f"report={args.output}")


if __name__ == "__main__":
    main()
