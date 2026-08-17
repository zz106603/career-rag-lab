from unittest.mock import Mock

import pytest

from app.hybrid_search import RRF_K, HybridSearchService
from app.langchain_retrieval import SearchFilters
from app.search import InvalidSearchInputError, SearchResult


def make_result(source: str, chunk_id: str, score: float) -> SearchResult:
    return SearchResult(
        content=f"{source} {chunk_id}",
        source=source,
        score=score,
        metadata={"chunk_id": chunk_id},
    )


def test_rrf_promotes_candidate_found_by_both_searches() -> None:
    dense_service = Mock()
    sparse_service = Mock()
    dense_service.search.return_value = [
        make_result("dense.md", "dense", 0.9),
        make_result("both.md", "both", 0.8),
    ]
    sparse_service.search.return_value = [
        make_result("sparse.md", "sparse", 5.0),
        make_result("both.md", "both", 3.0),
    ]
    service = HybridSearchService(dense_service, sparse_service)

    result = service.search("질문", top_k=2, candidate_k=2)

    assert [item.source for item in result.hybrid] == ["both.md", "dense.md"]
    assert result.hybrid[0].score == pytest.approx(2 / (RRF_K + 2))
    assert result.hybrid[0].metadata["dense_rank"] == 2
    assert result.hybrid[0].metadata["sparse_rank"] == 2
    assert result.dense == dense_service.search.return_value
    assert result.sparse == sparse_service.search.return_value


def test_hybrid_passes_same_filter_and_candidate_size_to_both() -> None:
    dense_service = Mock(search=Mock(return_value=[]))
    sparse_service = Mock(search=Mock(return_value=[]))
    service = HybridSearchService(dense_service, sparse_service)
    filters = SearchFilters(document_type="project")

    service.search("질문", top_k=3, filters=filters)

    dense_service.search.assert_called_once_with("질문", top_k=6, filters=filters)
    sparse_service.search.assert_called_once_with("질문", top_k=6, filters=filters)


def test_hybrid_rejects_candidate_size_smaller_than_result_size() -> None:
    service = HybridSearchService(Mock(), Mock())

    with pytest.raises(InvalidSearchInputError, match="candidate_k"):
        service.search("질문", top_k=3, candidate_k=2)
