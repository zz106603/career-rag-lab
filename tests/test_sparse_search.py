from qdrant_client import QdrantClient, models

from app.migrate_hybrid_collection import migrate_collection
from app.sparse_search import SPARSE_VECTOR_NAME, SparseSearchService, encode_sparse


def test_sparse_encoder_is_deterministic_and_separates_english_term() -> None:
    first = encode_sparse("Playwright를 사용했다")
    second = encode_sparse("Playwright를 사용했다")

    assert first == second
    assert len(first.indices) == 2


def test_migration_reuses_dense_vector_and_adds_searchable_sparse_vector() -> None:
    client = QdrantClient(":memory:")
    client.create_collection(
        "dense",
        vectors_config=models.VectorParams(size=2, distance=models.Distance.COSINE),
    )
    client.upsert(
        "dense",
        points=[
            models.PointStruct(
                id=1,
                vector=[1.0, 0.0],
                payload={
                    "content": "Celery 비동기 작업",
                    "metadata": {"source": "project.md", "chunk_index": 0},
                },
            )
        ],
        wait=True,
    )

    count = migrate_collection(
        client, source="dense", target="hybrid", vector_size=2
    )
    stored = client.retrieve("hybrid", [1], with_vectors=True)[0]
    results = SparseSearchService(client, "hybrid").search("Celery", top_k=1)

    assert count == 1
    assert stored.vector[""] == [1.0, 0.0]
    assert SPARSE_VECTOR_NAME in stored.vector
    assert results[0].source == "project.md"
