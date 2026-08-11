import argparse
import json
from dataclasses import replace
from pathlib import Path

from qdrant_client import QdrantClient, models

from app.answers import create_answer_service
from app.config import get_settings
from app.evaluation import (
    compare_pipelines,
    load_evaluation_questions,
    report_to_dict,
)
from app.langchain_rag import create_langchain_rag_service
from app.langchain_retrieval import create_langchain_retrieval_service
from app.search import create_search_service


PROJECT_ROOT = Path(__file__).parents[1]
DEFAULT_QUESTIONS = PROJECT_ROOT / "data" / "evaluation" / "questions.json"
DEFAULT_REPORT = PROJECT_ROOT / "data" / "evaluation" / "pipeline-comparison.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="수동·LangChain RAG 평가")
    parser.add_argument("--langchain-collection", default="career_documents_langchain")
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument(
        "--prepare-langchain-collection",
        action="store_true",
        help="수동 Collection 벡터를 재사용해 LangChain payload Collection을 최초 생성",
    )
    args = parser.parse_args()

    settings = get_settings()
    client = QdrantClient(url=settings.qdrant_url)
    if args.prepare_langchain_collection:
        clone_as_langchain_collection(
            client,
            source=settings.qdrant_collection,
            target=args.langchain_collection,
            vector_size=settings.embedding_dimensions,
        )

    langchain_settings = replace(
        settings, qdrant_collection=args.langchain_collection
    )
    report = compare_pipelines(
        load_evaluation_questions(args.questions),
        create_answer_service(
            settings=settings,
            search_service=create_search_service(
                settings=settings, qdrant_client=client
            ),
        ),
        create_langchain_rag_service(
            settings=langchain_settings,
            retrieval_service=create_langchain_retrieval_service(
                settings=langchain_settings, qdrant_client=client
            ),
        ),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report_to_dict(report), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _print_summary(report_to_dict(report), args.output)


def clone_as_langchain_collection(
    client: QdrantClient,
    *,
    source: str,
    target: str,
    vector_size: int,
) -> None:
    """같은 벡터를 재사용하고 payload 구조만 LangChain 형식으로 바꾼다."""
    if client.collection_exists(target):
        raise ValueError(f"Target collection already exists: {target}")
    points, next_offset = client.scroll(
        collection_name=source,
        limit=10_000,
        with_payload=True,
        with_vectors=True,
    )
    if next_offset is not None:
        raise ValueError("Source collection exceeds the single evaluation batch")
    if not points:
        raise ValueError(f"Source collection is empty: {source}")
    client.create_collection(
        collection_name=target,
        vectors_config=models.VectorParams(
            size=vector_size,
            distance=models.Distance.COSINE,
        ),
    )
    converted = []
    for point in points:
        payload = dict(point.payload or {})
        content = payload.pop("content", None)
        source_name = payload.pop("source", None)
        if not isinstance(content, str) or not isinstance(source_name, str):
            raise ValueError("Source point requires content and source")
        converted.append(
            models.PointStruct(
                id=point.id,
                vector=point.vector,
                payload={
                    "content": content,
                    "metadata": {"source": source_name, **payload},
                },
            )
        )
    client.upsert(collection_name=target, points=converted, wait=True)


def _print_summary(data: dict, output: Path) -> None:
    print("pipeline     source_recall  refusal_accuracy  source_accuracy  embed  generate")
    for name in ("manual", "langchain"):
        item = data[name]
        print(
            f"{name:<12} {item['mean_source_recall']:.3f}          "
            f"{item['refusal_accuracy']:.3f}             "
            f"{item['answer_source_accuracy']:.3f}            "
            f"{item['embedding_calls']:<5}  {item['generation_calls']}"
        )
    print(f"report: {output}")


if __name__ == "__main__":
    main()
