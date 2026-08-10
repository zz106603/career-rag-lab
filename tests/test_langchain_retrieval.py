from langchain_core.embeddings import Embeddings
from qdrant_client import QdrantClient
import pytest

from app.langchain_indexing import index_document_with_langchain
from app.langchain_retrieval import LangChainRetrievalService
from app.search import InvalidSearchInputError, QdrantSearcher
from tests.test_indexing import make_item


class FixedQueryEmbeddings(Embeddings):
    def __init__(self, query_vector: list[float]) -> None:
        self.query_vector = query_vector
        self.queries: list[str] = []

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    def embed_query(self, text: str) -> list[float]:
        self.queries.append(text)
        return list(self.query_vector)


def make_vector_store_service() -> tuple[
    QdrantClient, LangChainRetrievalService, FixedQueryEmbeddings
]:
    client = QdrantClient(":memory:")
    items = [make_item(1), make_item(2), make_item(3)]
    items[0].vector[:] = [1.0, 0.0, 0.0, 0.0]
    items[1].vector[:] = [0.8, 0.2, 0.0, 0.0]
    items[2].vector[:] = [0.0, 1.0, 0.0, 0.0]
    index_document_with_langchain(
        items, client=client, collection_name="documents", vector_size=4
    )
    embeddings = FixedQueryEmbeddings([1.0, 0.0, 0.0, 0.0])
    from langchain_qdrant import QdrantVectorStore

    vector_store = QdrantVectorStore(
        client=client,
        collection_name="documents",
        embedding=embeddings,
        content_payload_key="content",
        metadata_payload_key="metadata",
        validate_collection_config=False,
    )
    return client, LangChainRetrievalService(vector_store), embeddings


def test_retriever_matches_manual_search_order_scores_and_sources() -> None:
    client, service, embeddings = make_vector_store_service()

    manual = QdrantSearcher(client, "documents").search(
        [1.0, 0.0, 0.0, 0.0], top_k=2, score_threshold=0.5
    )
    langchain = service.search("백엔드 경험은?", top_k=2, score_threshold=0.5)

    assert [item.content for item in langchain] == [item.content for item in manual]
    assert [item.source for item in langchain] == [item.source for item in manual]
    assert [item.score for item in langchain] == [item.score for item in manual]
    assert embeddings.queries == ["백엔드 경험은?"]


def test_retriever_keeps_score_and_metadata_separate_from_answer() -> None:
    _, service, _ = make_vector_store_service()

    results = service.search("질문", top_k=1)

    assert len(results) == 1
    assert results[0].score == 1.0
    assert results[0].source == "source.md"
    assert results[0].metadata["chunk_id"] == "document-1-chunk-1"


def test_retriever_threshold_can_return_no_evidence() -> None:
    _, service, embeddings = make_vector_store_service()
    embeddings.query_vector = [0.0, 0.0, 1.0, 0.0]

    assert service.search("질문", top_k=3, score_threshold=0.5) == []


@pytest.mark.parametrize(
    ("query", "top_k", "threshold", "message"),
    [(" ", 1, None, "query"), ("질문", 0, None, "top_k"), ("질문", 1, 1.1, "threshold")],
)
def test_retriever_rejects_invalid_options(
    query: str, top_k: int, threshold: float | None, message: str
) -> None:
    _, service, _ = make_vector_store_service()

    with pytest.raises(InvalidSearchInputError, match=message):
        service.search(query, top_k=top_k, score_threshold=threshold)
