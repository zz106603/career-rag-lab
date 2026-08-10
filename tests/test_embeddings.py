from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.chunking import Chunk, ChunkMetadata
from app.config import Settings
from app.embeddings import (
    EmbeddingResponseError,
    EmptyEmbeddingInputError,
    MissingOpenAIAPIKeyError,
    create_openai_client,
    create_langchain_embeddings,
    embed_chunks,
    embed_chunks_with_langchain,
)


def make_settings(
    *, api_key: str | None = "test-key", dimensions: int = 3, batch_size: int = 2
) -> Settings:
    return Settings(
        qdrant_url="http://localhost:6333",
        qdrant_collection="career_documents",
        openai_api_key=api_key,
        embedding_model="text-embedding-3-small",
        embedding_dimensions=dimensions,
        embedding_batch_size=batch_size,
    )


def make_chunk(index: int) -> Chunk:
    return Chunk(
        content=f"chunk-{index}",
        metadata=ChunkMetadata(
            chunk_id=f"chunk-{index}",
            document_id="document-1",
            source="source.md",
            section="section",
            chunk_index=index,
            document_type="project",
            project_name="project",
            strategy="structure",
            start_char=index * 10,
            end_char=index * 10 + 7,
        ),
    )


def make_client(dimensions: int) -> Mock:
    client = Mock()

    def create_response(**kwargs):
        return SimpleNamespace(
            data=[
                SimpleNamespace(index=index, embedding=[float(index)] * dimensions)
                for index, _ in enumerate(kwargs["input"])
            ]
        )

    client.embeddings.create.side_effect = create_response
    return client


def test_embed_single_chunk_preserves_chunk_and_dimension() -> None:
    chunk = make_chunk(0)
    client = make_client(3)

    result = embed_chunks([chunk], client=client, settings=make_settings())

    assert result[0].chunk is chunk
    assert len(result[0].vector) == 3
    client.embeddings.create.assert_called_once_with(
        model="text-embedding-3-small",
        input=["chunk-0"],
        dimensions=3,
    )


def test_embed_multiple_chunks_uses_configured_batch_size() -> None:
    chunks = [make_chunk(index) for index in range(5)]
    client = make_client(3)

    result = embed_chunks(chunks, client=client, settings=make_settings(batch_size=2))

    assert [item.chunk for item in result] == chunks
    assert client.embeddings.create.call_count == 3
    assert [
        call.kwargs["input"] for call in client.embeddings.create.call_args_list
    ] == [["chunk-0", "chunk-1"], ["chunk-2", "chunk-3"], ["chunk-4"]]


def test_embed_chunks_rejects_empty_input_without_calling_api() -> None:
    client = make_client(3)

    with pytest.raises(EmptyEmbeddingInputError):
        embed_chunks([], client=client, settings=make_settings())

    client.embeddings.create.assert_not_called()


def test_embed_chunks_rejects_response_count_mismatch() -> None:
    client = Mock()
    client.embeddings.create.return_value = SimpleNamespace(data=[])

    with pytest.raises(EmbeddingResponseError, match="count"):
        embed_chunks([make_chunk(0)], client=client, settings=make_settings())


def test_embed_chunks_rejects_vector_dimension_mismatch() -> None:
    with pytest.raises(EmbeddingResponseError, match="dimension"):
        embed_chunks(
            [make_chunk(0)], client=make_client(2), settings=make_settings(dimensions=3)
        )


def test_embed_chunks_propagates_api_error() -> None:
    client = Mock()
    client.embeddings.create.side_effect = RuntimeError("API unavailable")

    with pytest.raises(RuntimeError, match="API unavailable"):
        embed_chunks([make_chunk(0)], client=client, settings=make_settings())


def test_create_openai_client_requires_api_key() -> None:
    with pytest.raises(MissingOpenAIAPIKeyError):
        create_openai_client(make_settings(api_key=None))


def test_settings_repr_does_not_expose_api_key() -> None:
    settings = make_settings(api_key="secret-value")

    assert "secret-value" not in repr(settings)


def test_langchain_embeddings_use_same_model_dimension_and_batch_settings() -> None:
    embeddings = create_langchain_embeddings(
        make_settings(api_key="secret-value", dimensions=4, batch_size=7)
    )

    assert embeddings.model == "text-embedding-3-small"
    assert embeddings.dimensions == 4
    assert embeddings.chunk_size == 7
    assert "secret-value" not in repr(embeddings)


def test_langchain_embedding_preserves_chunk_order_for_existing_indexer() -> None:
    chunks = [make_chunk(index) for index in range(3)]
    embeddings = Mock()
    embeddings.embed_documents.return_value = [
        [0.0, 0.0, 0.0],
        [1.0, 1.0, 1.0],
        [2.0, 2.0, 2.0],
    ]

    result = embed_chunks_with_langchain(
        chunks, embeddings=embeddings, settings=make_settings()
    )

    embeddings.embed_documents.assert_called_once_with(
        ["chunk-0", "chunk-1", "chunk-2"]
    )
    assert [item.chunk for item in result] == chunks
    assert [item.vector[0] for item in result] == [0.0, 1.0, 2.0]


def test_manual_and_langchain_results_have_same_pipeline_shape() -> None:
    chunks = [make_chunk(index) for index in range(2)]
    settings = make_settings()
    manual = embed_chunks(chunks, client=make_client(3), settings=settings)
    embeddings = Mock()
    embeddings.embed_documents.return_value = [
        [0.0, 0.0, 0.0],
        [1.0, 1.0, 1.0],
    ]

    langchain = embed_chunks_with_langchain(
        chunks, embeddings=embeddings, settings=settings
    )

    assert langchain == manual


def test_langchain_embedding_rejects_empty_input_without_calling_provider() -> None:
    embeddings = Mock()

    with pytest.raises(EmptyEmbeddingInputError):
        embed_chunks_with_langchain(
            [], embeddings=embeddings, settings=make_settings()
        )

    embeddings.embed_documents.assert_not_called()


def test_langchain_embedding_rejects_response_count_mismatch() -> None:
    embeddings = Mock()
    embeddings.embed_documents.return_value = []

    with pytest.raises(EmbeddingResponseError, match="count"):
        embed_chunks_with_langchain(
            [make_chunk(0)], embeddings=embeddings, settings=make_settings()
        )


def test_langchain_embedding_rejects_vector_dimension_mismatch() -> None:
    embeddings = Mock()
    embeddings.embed_documents.return_value = [[0.0, 0.0]]

    with pytest.raises(EmbeddingResponseError, match="dimension"):
        embed_chunks_with_langchain(
            [make_chunk(0)], embeddings=embeddings, settings=make_settings()
        )


def test_langchain_embedding_propagates_provider_error() -> None:
    embeddings = Mock()
    embeddings.embed_documents.side_effect = RuntimeError("API unavailable")

    with pytest.raises(RuntimeError, match="API unavailable"):
        embed_chunks_with_langchain(
            [make_chunk(0)], embeddings=embeddings, settings=make_settings()
        )


def test_create_langchain_embeddings_requires_api_key() -> None:
    with pytest.raises(MissingOpenAIAPIKeyError):
        create_langchain_embeddings(make_settings(api_key=None))
