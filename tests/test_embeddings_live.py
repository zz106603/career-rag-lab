from pathlib import Path

import pytest

from app.chunking import chunk_by_structure
from app.config import get_settings
from app.documents import load_markdown_file
from app.embeddings import (
    create_langchain_embeddings,
    create_openai_client,
    embed_chunks,
    embed_chunks_with_langchain,
)


PROJECT_ROOT = Path(__file__).parents[1]


@pytest.mark.live_api
def test_openai_creates_embedding_for_one_small_chunk() -> None:
    settings = get_settings()
    document = load_markdown_file(
        PROJECT_ROOT / "data" / "documents" / "finance-transfer-system.md"
    )
    chunk = chunk_by_structure(document, max_chars=100)[0]

    result = embed_chunks(
        [chunk], client=create_openai_client(settings), settings=settings
    )

    assert result[0].chunk.metadata.chunk_id == chunk.metadata.chunk_id
    assert len(result[0].vector) == settings.embedding_dimensions


@pytest.mark.live_api
def test_langchain_creates_existing_embedded_chunk_shape() -> None:
    settings = get_settings()
    document = load_markdown_file(
        PROJECT_ROOT / "data" / "documents" / "finance-transfer-system.md"
    )
    chunk = chunk_by_structure(document, max_chars=100)[0]

    result = embed_chunks_with_langchain(
        [chunk],
        embeddings=create_langchain_embeddings(settings),
        settings=settings,
    )

    assert result[0].chunk.metadata.chunk_id == chunk.metadata.chunk_id
    assert len(result[0].vector) == settings.embedding_dimensions

