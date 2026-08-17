from app.chunking import chunk_by_fixed_size
from app.documents import Document, DocumentMetadata
from app.evaluate_chunk_strategies import ChunkStrategy, evaluate_strategy, search_chunks
from app.evaluation import EvaluationQuestion


def _document(source: str, content: str) -> Document:
    return Document(
        content,
        DocumentMetadata(source, source, "project", source.removesuffix(".md")),
    )


def test_search_chunks_uses_same_lexical_score_and_deterministic_order() -> None:
    chunks = chunk_by_fixed_size(_document("b.md", "RabbitMQ 처리"), 100, 0)
    chunks += chunk_by_fixed_size(_document("a.md", "RabbitMQ 처리"), 100, 0)

    results = search_chunks("RabbitMQ 처리", chunks, top_k=2)

    assert [result.metadata.source for result in results] == ["a.md", "b.md"]


def test_search_chunks_returns_empty_when_query_has_no_search_term() -> None:
    chunks = chunk_by_fixed_size(_document("a.md", "검색할 내용"), 100, 0)

    assert search_chunks("은 는", chunks) == []


def test_evaluate_strategy_records_quality_and_indexing_cost() -> None:
    strategy = ChunkStrategy(
        "fixed",
        "test",
        lambda document: chunk_by_fixed_size(document, 10, 2),
    )
    documents = [
        _document("expected.md", "target alpha text"),
        _document("other.md", "unrelated text"),
    ]
    questions = [
        EvaluationQuestion("q1", "exact_keyword", "target", ("expected.md",), True)
    ]

    result = evaluate_strategy(strategy, documents, questions)

    assert result["overall"] == {
        "question_count": 1,
        "hit_at_3": 1.0,
        "mrr": 1.0,
        "mean_source_recall": 1.0,
    }
    assert result["indexing"]["chunk_count"] > len(documents)
    assert result["indexing"]["duplicated_chars"] > 0
