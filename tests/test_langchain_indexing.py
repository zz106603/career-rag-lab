from qdrant_client import QdrantClient
import pytest

from app.indexing import InvalidIndexInputError, QdrantIndexer
from app.langchain_indexing import index_document_with_langchain
from tests.test_indexing import make_item


def test_langchain_vector_store_preserves_vectors_ids_content_and_metadata() -> None:
    client = QdrantClient(":memory:")
    items = [make_item(0), make_item(1)]
    manual = QdrantIndexer(client, "manual", vector_size=4)

    manual_result = manual.index_document(items)
    langchain_result = index_document_with_langchain(
        items,
        client=client,
        collection_name="langchain",
        vector_size=4,
    )
    manual_records = client.retrieve(
        "manual", manual_result.point_ids, with_payload=True, with_vectors=True
    )
    langchain_records = client.retrieve(
        "langchain", langchain_result.point_ids, with_payload=True, with_vectors=True
    )

    assert langchain_result.point_ids == manual_result.point_ids
    assert [record.vector for record in langchain_records] == [
        record.vector for record in manual_records
    ]
    for manual_record, langchain_record in zip(manual_records, langchain_records):
        assert langchain_record.payload["content"] == manual_record.payload["content"]
        assert (
            langchain_record.payload["metadata"]["source"]
            == manual_record.payload["source"]
        )
        assert (
            langchain_record.payload["metadata"]["chunk_id"]
            == manual_record.payload["chunk_id"]
        )


def test_langchain_reindex_removes_stale_chunks() -> None:
    client = QdrantClient(":memory:")
    items = [make_item(0), make_item(1)]

    index_document_with_langchain(
        items, client=client, collection_name="documents", vector_size=4
    )
    index_document_with_langchain(
        [items[0]], client=client, collection_name="documents", vector_size=4
    )
    records, _ = client.scroll("documents", limit=100, with_payload=True)

    assert len(records) == 1
    assert records[0].payload["metadata"]["chunk_id"] == "document-1-chunk-0"


def test_langchain_validates_vectors_before_deleting_existing_document() -> None:
    client = QdrantClient(":memory:")
    index_document_with_langchain(
        [make_item(0)], client=client, collection_name="documents", vector_size=4
    )

    with pytest.raises(InvalidIndexInputError, match="dimension"):
        index_document_with_langchain(
            [make_item(0, vector_size=3)],
            client=client,
            collection_name="documents",
            vector_size=4,
        )

    assert client.count("documents", exact=True).count == 1
