import uuid

import pytest
from qdrant_client import models

from app.qdrant import create_qdrant_client
from app.search import QdrantSearcher


@pytest.mark.integration
def test_actual_qdrant_vector_search_preserves_evidence() -> None:
    client = create_qdrant_client()
    collection_name = f"test_search_{uuid.uuid4().hex}"
    client.create_collection(
        collection_name,
        vectors_config=models.VectorParams(size=2, distance=models.Distance.COSINE),
    )
    try:
        client.upsert(
            collection_name,
            points=[
                models.PointStruct(
                    id=1,
                    vector=[1.0, 0.0],
                    payload={
                        "content": "가장 가까운 검색 근거",
                        "source": "nearest.md",
                        "section": "근거",
                    },
                ),
                models.PointStruct(
                    id=2,
                    vector=[0.0, 1.0],
                    payload={
                        "content": "관련 없는 검색 근거",
                        "source": "far.md",
                        "section": "기타",
                    },
                ),
            ],
            wait=True,
        )

        results = QdrantSearcher(client, collection_name).search(
            [1.0, 0.0], top_k=2, score_threshold=0.5
        )

        assert len(results) == 1
        assert results[0].source == "nearest.md"
        assert results[0].content == "가장 가까운 검색 근거"
        assert results[0].metadata["section"] == "근거"
        assert results[0].score == pytest.approx(1.0)
    finally:
        if client.collection_exists(collection_name):
            client.delete_collection(collection_name)
