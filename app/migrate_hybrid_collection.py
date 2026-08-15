import argparse

from qdrant_client import QdrantClient, models

from app.config import get_settings
from app.sparse_search import SPARSE_VECTOR_NAME, encode_sparse


def migrate_collection(
    client: QdrantClient,
    *,
    source: str,
    target: str,
    vector_size: int,
) -> int:
    """기존 Dense Point를 재Embedding 없이 Dense+Sparse Collection으로 복사한다."""
    if client.collection_exists(target):
        raise ValueError(f"Target collection already exists: {target}")
    records = []
    offset = None
    while True:
        batch, offset = client.scroll(
            source,
            limit=256,
            offset=offset,
            with_payload=True,
            with_vectors=True,
        )
        records.extend(batch)
        if offset is None:
            break
    if not records:
        raise ValueError(f"Source collection is empty: {source}")
    client.create_collection(
        target,
        vectors_config=models.VectorParams(
            size=vector_size, distance=models.Distance.COSINE
        ),
        sparse_vectors_config={
            SPARSE_VECTOR_NAME: models.SparseVectorParams(
                modifier=models.Modifier.IDF
            )
        },
    )
    client.upsert(
        target,
        points=[
            models.PointStruct(
                id=record.id,
                vector=record.vector,
                payload=record.payload,
            )
            for record in records
        ],
        wait=True,
    )
    client.update_vectors(
        target,
        points=[
            models.PointVectors(
                id=record.id,
                vector={
                    SPARSE_VECTOR_NAME: encode_sparse(record.payload["content"])
                },
            )
            for record in records
        ],
        wait=True,
    )
    return len(records)


def main() -> None:
    parser = argparse.ArgumentParser(description="Dense Collection을 Hybrid로 복사")
    parser.add_argument("--source", default="career_documents_langchain")
    args = parser.parse_args()
    settings = get_settings()
    count = migrate_collection(
        QdrantClient(url=settings.qdrant_url),
        source=args.source,
        target=settings.qdrant_collection,
        vector_size=settings.embedding_dimensions,
    )
    print(
        f"source={args.source} target={settings.qdrant_collection} "
        f"points={count} embedding_calls=0"
    )


if __name__ == "__main__":
    main()
