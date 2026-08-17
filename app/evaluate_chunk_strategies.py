import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from app.chunking import Chunk, chunk_by_langchain_recursive, chunk_by_structure
from app.documents import Document, load_markdown_directory
from app.evaluation import EvaluationQuestion, load_evaluation_questions
from app.keyword_search import KOREAN_PARTICLES, tokenize


PROJECT_ROOT = Path(__file__).parents[1]
DOCUMENTS_PATH = PROJECT_ROOT / "data" / "documents"
QUESTIONS_PATH = PROJECT_ROOT / "data" / "evaluation" / "questions.json"
OUTPUT_PATH = PROJECT_ROOT / "data" / "evaluation" / "chunk-strategy-comparison.json"
TOP_K = 3


@dataclass(frozen=True)
class ChunkStrategy:
    name: str
    description: str
    split: Callable[[Document], list[Chunk]]


STRATEGIES = (
    ChunkStrategy(
        "small_recursive_200_20",
        "LangChain recursive, chunk_size=200, overlap=20",
        lambda document: chunk_by_langchain_recursive(document, 200, 20),
    ),
    ChunkStrategy(
        "large_recursive_800_80",
        "LangChain recursive, chunk_size=800, overlap=80",
        lambda document: chunk_by_langchain_recursive(document, 800, 80),
    ),
    ChunkStrategy(
        "structure_500",
        "Markdown section 우선, max_chars=500, overlap=0",
        lambda document: chunk_by_structure(document, 500),
    ),
)


def search_chunks(query: str, chunks: list[Chunk], top_k: int = TOP_K) -> list[Chunk]:
    """Embedding 비용 없이 Chunk 경계의 영향을 비교하는 동일 lexical 검색이다."""
    query_terms = {
        term for term in tokenize(query) if term not in KOREAN_PARTICLES
    }
    if not query_terms:
        return []
    scored: list[tuple[float, Chunk]] = []
    for chunk in chunks:
        counts = Counter(tokenize(chunk.content))
        matched_terms = sum(term in counts for term in query_terms)
        if matched_terms == 0:
            continue
        occurrences = sum(counts[term] for term in query_terms)
        score = matched_terms / len(query_terms) + min(occurrences, 9) / 100
        scored.append((score, chunk))
    scored.sort(
        key=lambda item: (
            -item[0],
            item[1].metadata.source,
            item[1].metadata.chunk_index,
        )
    )
    return [chunk for _, chunk in scored[:top_k]]


def evaluate_strategy(
    strategy: ChunkStrategy,
    documents: list[Document],
    questions: list[EvaluationQuestion],
) -> dict:
    chunks = [chunk for document in documents for chunk in strategy.split(document)]
    original_chars = sum(len(document.content) for document in documents)
    indexed_chars = sum(len(chunk.content) for chunk in chunks)
    cases = []
    category_values: dict[str, list[tuple[float, float, float]]] = defaultdict(list)

    for question in questions:
        results = search_chunks(question.question, chunks)
        # 같은 문서의 Chunk가 여러 개여도 문서 검색 순위는 최초 등장만 센다.
        sources = list(dict.fromkeys(chunk.metadata.source for chunk in results))
        if not question.answerable:
            cases.append(
                {
                    "question_id": question.id,
                    "category": question.category,
                    "retrieval_sources": sources,
                    "first_relevant_rank": None,
                    "source_recall": None,
                }
            )
            continue
        expected = set(question.expected_sources)
        first_rank = next(
            (rank for rank, source in enumerate(sources, 1) if source in expected),
            None,
        )
        hit = 1.0 if first_rank is not None else 0.0
        reciprocal_rank = 1.0 / first_rank if first_rank is not None else 0.0
        recall = len(expected.intersection(sources)) / len(expected)
        category_values[question.category].append((hit, reciprocal_rank, recall))
        cases.append(
            {
                "question_id": question.id,
                "category": question.category,
                "retrieval_sources": sources,
                "first_relevant_rank": first_rank,
                "source_recall": recall,
            }
        )

    all_values = [value for values in category_values.values() for value in values]
    return {
        "strategy": strategy.name,
        "description": strategy.description,
        "indexing": {
            "chunk_count": len(chunks),
            "original_chars": original_chars,
            "indexed_chars": indexed_chars,
            "duplicated_chars": indexed_chars - original_chars,
            "relative_embedding_input": indexed_chars / original_chars,
        },
        "overall": _summarize(all_values),
        "by_category": {
            category: _summarize(values)
            for category, values in sorted(category_values.items())
        },
        "cases": cases,
    }


def _summarize(values: list[tuple[float, float, float]]) -> dict:
    count = len(values)
    return {
        "question_count": count,
        "hit_at_3": sum(value[0] for value in values) / count,
        "mrr": sum(value[1] for value in values) / count,
        "mean_source_recall": sum(value[2] for value in values) / count,
    }


def main() -> None:
    documents = load_markdown_directory(DOCUMENTS_PATH)
    questions = load_evaluation_questions(QUESTIONS_PATH)
    results = [evaluate_strategy(strategy, documents, questions) for strategy in STRATEGIES]
    report = {
        "evaluation_mode": "offline_lexical_proxy",
        "reason": "Chunk별 재Embedding 없이 같은 lexical 검색기로 경계 영향만 비교",
        "top_k": TOP_K,
        "embedding_calls": 0,
        "generation_calls": 0,
        "strategies": results,
    }
    OUTPUT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for result in results:
        print(
            f"{result['strategy']} chunks={result['indexing']['chunk_count']} "
            f"input={result['indexing']['relative_embedding_input']:.3f} "
            f"hit@3={result['overall']['hit_at_3']:.3f} "
            f"mrr={result['overall']['mrr']:.3f} "
            f"recall={result['overall']['mean_source_recall']:.3f}"
        )
    print(f"report={OUTPUT_PATH}")


if __name__ == "__main__":
    main()
