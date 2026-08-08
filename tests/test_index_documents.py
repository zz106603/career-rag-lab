from types import SimpleNamespace
from unittest.mock import Mock

from qdrant_client import QdrantClient

from app.config import Settings
from app.index_documents import DEFAULT_DOCUMENTS_PATH, index_documents


def make_settings() -> Settings:
    return Settings(
        qdrant_url="http://localhost:6333",
        qdrant_collection="pipeline_documents",
        openai_api_key="test-key",
        embedding_model="text-embedding-3-small",
        embedding_dimensions=4,
        embedding_batch_size=100,
    )


def make_openai_client() -> Mock:
    client = Mock()

    def create_response(**kwargs):
        return SimpleNamespace(
            data=[
                SimpleNamespace(index=index, embedding=[float(index)] * 4)
                for index, _ in enumerate(kwargs["input"])
            ]
        )

    client.embeddings.create.side_effect = create_response
    return client


def test_index_documents_runs_full_pipeline_without_duplicate_points() -> None:
    settings = make_settings()
    openai_client = make_openai_client()
    qdrant_client = QdrantClient(":memory:")

    first = index_documents(
        DEFAULT_DOCUMENTS_PATH,
        settings=settings,
        openai_client=openai_client,
        qdrant_client=qdrant_client,
    )
    first_count = qdrant_client.count(settings.qdrant_collection, exact=True).count

    second = index_documents(
        DEFAULT_DOCUMENTS_PATH,
        settings=settings,
        openai_client=openai_client,
        qdrant_client=qdrant_client,
    )
    second_count = qdrant_client.count(settings.qdrant_collection, exact=True).count

    assert first.document_count == 6
    assert first.chunk_count > first.document_count
    assert second == first
    assert first_count == first.chunk_count
    assert second_count == first_count
    assert openai_client.embeddings.create.call_count == 2

