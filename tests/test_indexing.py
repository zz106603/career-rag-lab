from qdrant_client import QdrantClient, models
import pytest

from app.chunking import Chunk, ChunkMetadata
from app.embeddings import EmbeddedChunk
from app.indexing import (
    CollectionConfigurationError,
    InvalidIndexInputError,
    QdrantIndexer,
)


def make_item(
    index: int, *, document_id: str = "document-1", vector_size: int = 4
) -> EmbeddedChunk:
    content = f"content-{index}"
    chunk = Chunk(
        content=content,
        metadata=ChunkMetadata(
            chunk_id=f"{document_id}-chunk-{index}",
            document_id=document_id,
            source="source.md",
            section="성과",
            chunk_index=index,
            document_type="project",
            project_name="프로젝트",
            strategy="structure",
            start_char=index * 10,
            end_char=index * 10 + len(content),
        ),
    )
    return EmbeddedChunk(chunk=chunk, vector=[float(index)] * vector_size)


@pytest.fixture
def client() -> QdrantClient:
    return QdrantClient(":memory:")


@pytest.fixture
def indexer(client: QdrantClient) -> QdrantIndexer:
    return QdrantIndexer(client, collection_name="documents", vector_size=4)


def test_ensure_collection_creates_cosine_collection(
    indexer: QdrantIndexer, client: QdrantClient
) -> None:
    assert indexer.ensure_collection() is True
    assert indexer.ensure_collection() is False

    config = client.get_collection("documents").config.params.vectors
    assert isinstance(config, models.VectorParams)
    assert config.size == 4
    assert config.distance == models.Distance.COSINE


def test_ensure_collection_rejects_dimension_mismatch(client: QdrantClient) -> None:
    client.create_collection(
        "documents",
        vectors_config=models.VectorParams(size=3, distance=models.Distance.COSINE),
    )

    with pytest.raises(CollectionConfigurationError, match="size"):
        QdrantIndexer(client, "documents", vector_size=4).ensure_collection()


def test_index_document_preserves_payload_and_vector(
    indexer: QdrantIndexer, client: QdrantClient
) -> None:
    item = make_item(0)

    result = indexer.index_document([item])
    records = client.retrieve(
        collection_name="documents",
        ids=result.point_ids,
        with_payload=True,
        with_vectors=True,
    )

    assert result.document_id == "document-1"
    assert len(records) == 1
    assert records[0].vector == item.vector
    assert records[0].payload == {
        "document_id": "document-1",
        "chunk_id": "document-1-chunk-0",
        "content": "content-0",
        "source": "source.md",
        "section": "성과",
        "chunk_index": 0,
        "document_type": "project",
        "project_name": "프로젝트",
        "strategy": "structure",
        "start_char": 0,
        "end_char": 9,
    }


def test_index_document_preserves_hashes_and_lists_document_state(
    indexer: QdrantIndexer,
) -> None:
    indexer.index_document(
        [make_item(0), make_item(1)],
        document_hash="content-hash",
        index_fingerprint="pipeline-hash",
    )

    states = indexer.list_indexed_documents()

    assert states["document-1"].source == "source.md"
    assert states["document-1"].document_hash == "content-hash"
    assert states["document-1"].index_fingerprint == "pipeline-hash"


def test_reindex_same_document_does_not_increase_count(
    indexer: QdrantIndexer,
) -> None:
    items = [make_item(0), make_item(1)]

    indexer.index_document(items)
    indexer.index_document(items)

    assert indexer.count_document("document-1") == 2


def test_reindex_removes_stale_chunks(indexer: QdrantIndexer) -> None:
    indexer.index_document([make_item(0), make_item(1)])

    indexer.index_document([make_item(0)])

    assert indexer.count_document("document-1") == 1


def test_delete_document_removes_only_selected_document(
    indexer: QdrantIndexer,
) -> None:
    indexer.index_document([make_item(0, document_id="document-1")])
    indexer.index_document([make_item(0, document_id="document-2")])

    indexer.delete_document("document-1")

    assert indexer.count_document("document-1") == 0
    assert indexer.count_document("document-2") == 1


def test_index_document_rejects_mixed_documents(indexer: QdrantIndexer) -> None:
    with pytest.raises(InvalidIndexInputError, match="exactly one document"):
        indexer.index_document(
            [
                make_item(0, document_id="document-1"),
                make_item(0, document_id="document-2"),
            ]
        )


def test_index_document_validates_dimension_before_deleting_existing_points(
    indexer: QdrantIndexer,
) -> None:
    indexer.index_document([make_item(0)])

    with pytest.raises(InvalidIndexInputError, match="dimension"):
        indexer.index_document([make_item(0, vector_size=3)])

    assert indexer.count_document("document-1") == 1

