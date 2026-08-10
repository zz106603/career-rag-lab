import uuid

import pytest
from qdrant_client import QdrantClient

from app.config import Settings
from app.index_documents import index_documents
from app.indexing import QdrantIndexer
from app.qdrant import create_qdrant_client
from tests.test_indexing import make_item
from tests.test_index_documents import make_openai_client


@pytest.mark.integration
def test_qdrant_document_reindex_and_delete() -> None:
    client: QdrantClient = create_qdrant_client()
    collection_name = f"test_indexing_{uuid.uuid4().hex}"
    indexer = QdrantIndexer(client, collection_name=collection_name, vector_size=4)

    try:
        items = [make_item(0), make_item(1)]
        first_result = indexer.index_document(
            items,
            document_hash="content-hash",
            index_fingerprint="pipeline-hash",
        )
        records = client.retrieve(
            collection_name=collection_name,
            ids=first_result.point_ids,
            with_payload=True,
            with_vectors=True,
        )
        assert len(records) == 2
        assert records[0].payload["source"] == "source.md"
        assert records[0].payload["document_hash"] == "content-hash"
        assert len(records[0].vector) == 4
        assert indexer.list_indexed_documents()[
            "document-1"
        ].index_fingerprint == "pipeline-hash"

        indexer.index_document(items)
        assert indexer.count_document("document-1") == 2

        indexer.index_document([items[0]])
        assert indexer.count_document("document-1") == 1

        indexer.delete_document("document-1")
        assert indexer.count_document("document-1") == 0
    finally:
        if client.collection_exists(collection_name):
            client.delete_collection(collection_name)


@pytest.mark.integration
def test_actual_qdrant_incremental_indexing_scenarios(tmp_path) -> None:
    client: QdrantClient = create_qdrant_client()
    collection_name = f"test_incremental_{uuid.uuid4().hex}"
    settings = Settings(
        qdrant_url="http://localhost:6333",
        qdrant_collection=collection_name,
        openai_api_key="test-key",
        embedding_model="text-embedding-3-small",
        embedding_dimensions=4,
        embedding_batch_size=100,
    )
    openai_client = make_openai_client()
    first_path = tmp_path / "first.md"
    second_path = tmp_path / "second.md"
    first_path.write_text("# 첫 문서\n\n처음 내용", encoding="utf-8")
    second_path.write_text("# 둘째 문서\n\n삭제할 내용", encoding="utf-8")

    try:
        first = index_documents(
            tmp_path,
            settings=settings,
            openai_client=openai_client,
            qdrant_client=client,
        )
        unchanged = index_documents(
            tmp_path,
            settings=settings,
            openai_client=openai_client,
            qdrant_client=client,
        )
        first_path.write_text("# 첫 문서\n\n실제 Qdrant 수정 내용", encoding="utf-8")
        second_path.unlink()
        changed = index_documents(
            tmp_path,
            settings=settings,
            openai_client=openai_client,
            qdrant_client=client,
        )
        records, _ = client.scroll(
            collection_name, limit=100, with_payload=True, with_vectors=False
        )

        assert first.added_count == 2
        assert unchanged.unchanged_count == 2
        assert unchanged.embedded_chunk_count == 0
        assert changed.updated_count == 1
        assert changed.deleted_count == 1
        assert changed.embedded_chunk_count == 1
        assert openai_client.embeddings.create.call_count == 2
        assert {record.payload["source"] for record in records} == {"first.md"}
        assert "실제 Qdrant 수정 내용" in records[0].payload["content"]
        assert records[0].payload["document_hash"]
        assert records[0].payload["index_fingerprint"]
    finally:
        if client.collection_exists(collection_name):
            client.delete_collection(collection_name)
