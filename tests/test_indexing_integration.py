import uuid

import pytest
from qdrant_client import QdrantClient

from app.indexing import QdrantIndexer
from app.qdrant import create_qdrant_client
from tests.test_indexing import make_item


@pytest.mark.integration
def test_qdrant_document_reindex_and_delete() -> None:
    client: QdrantClient = create_qdrant_client()
    collection_name = f"test_indexing_{uuid.uuid4().hex}"
    indexer = QdrantIndexer(client, collection_name=collection_name, vector_size=4)

    try:
        items = [make_item(0), make_item(1)]
        first_result = indexer.index_document(items)
        records = client.retrieve(
            collection_name=collection_name,
            ids=first_result.point_ids,
            with_payload=True,
            with_vectors=True,
        )
        assert len(records) == 2
        assert records[0].payload["source"] == "source.md"
        assert len(records[0].vector) == 4

        indexer.index_document(items)
        assert indexer.count_document("document-1") == 2

        indexer.index_document([items[0]])
        assert indexer.count_document("document-1") == 1

        indexer.delete_document("document-1")
        assert indexer.count_document("document-1") == 0
    finally:
        if client.collection_exists(collection_name):
            client.delete_collection(collection_name)
