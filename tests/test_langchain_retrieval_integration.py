import uuid

from langchain_qdrant import QdrantVectorStore
import pytest

from app.langchain_indexing import index_document_with_langchain
from app.langchain_retrieval import LangChainRetrievalService
from app.qdrant import create_qdrant_client
from app.search import QdrantSearcher
from tests.test_indexing import make_item
from tests.test_langchain_retrieval import FixedQueryEmbeddings


@pytest.mark.integration
def test_actual_qdrant_retriever_matches_manual_vector_search() -> None:
    client = create_qdrant_client()
    collection_name = f"test_retriever_compare_{uuid.uuid4().hex}"
    items = [make_item(1), make_item(2), make_item(3)]
    items[0].vector[:] = [1.0, 0.0, 0.0, 0.0]
    items[1].vector[:] = [0.8, 0.2, 0.0, 0.0]
    items[2].vector[:] = [0.0, 1.0, 0.0, 0.0]

    try:
        index_document_with_langchain(
            items,
            client=client,
            collection_name=collection_name,
            vector_size=4,
        )
        embeddings = FixedQueryEmbeddings([1.0, 0.0, 0.0, 0.0])
        vector_store = QdrantVectorStore(
            client=client,
            collection_name=collection_name,
            embedding=embeddings,
            content_payload_key="content",
            metadata_payload_key="metadata",
            validate_collection_config=False,
        )

        manual = QdrantSearcher(client, collection_name).search(
            [1.0, 0.0, 0.0, 0.0], top_k=2, score_threshold=0.5
        )
        langchain = LangChainRetrievalService(vector_store).search(
            "백엔드 경험은?", top_k=2, score_threshold=0.5
        )

        assert [item.content for item in langchain] == [
            item.content for item in manual
        ]
        assert [item.source for item in langchain] == [item.source for item in manual]
        assert [item.score for item in langchain] == pytest.approx(
            [item.score for item in manual]
        )
        assert embeddings.queries == ["백엔드 경험은?"]
    finally:
        if client.collection_exists(collection_name):
            client.delete_collection(collection_name)
