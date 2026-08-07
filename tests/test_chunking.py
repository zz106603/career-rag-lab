from pathlib import Path

import pytest

from app.chunking import (
    chunk_by_fixed_size,
    chunk_by_structure,
    compare_chunking_strategies,
)
from app.documents import Document, DocumentMetadata, load_markdown_file


PROJECT_ROOT = Path(__file__).parents[1]
DOCUMENT_PATH = PROJECT_ROOT / "data" / "documents" / "finance-transfer-system.md"


def load_test_document() -> Document:
    return load_markdown_file(DOCUMENT_PATH)


def test_structure_chunking_is_deterministic() -> None:
    document = load_test_document()

    first = chunk_by_structure(document, max_chars=180)
    second = chunk_by_structure(document, max_chars=180)

    assert [chunk.metadata.chunk_id for chunk in first] == [
        chunk.metadata.chunk_id for chunk in second
    ]


def test_structure_chunks_follow_sections_and_reconstruct_original() -> None:
    document = load_test_document()

    chunks = chunk_by_structure(document, max_chars=180)

    assert "프로젝트 개요" in {chunk.metadata.section for chunk in chunks}
    assert "문제 해결" in {chunk.metadata.section for chunk in chunks}
    assert "".join(chunk.content for chunk in chunks) == document.content
    assert all(0 < len(chunk.content) <= 180 for chunk in chunks)


def test_fixed_chunks_keep_requested_overlap() -> None:
    document = load_test_document()

    chunks = chunk_by_fixed_size(document, chunk_size=160, overlap=30)

    for previous, current in zip(chunks, chunks[1:]):
        assert previous.content[-30:] == current.content[:30]
        assert current.metadata.start_char == previous.metadata.end_char - 30


def test_every_chunk_preserves_source_and_original_position() -> None:
    document = load_test_document()

    chunks = chunk_by_structure(document, max_chars=180)

    assert [chunk.metadata.chunk_index for chunk in chunks] == list(
        range(len(chunks))
    )
    assert len({chunk.metadata.document_id for chunk in chunks}) == 1
    for chunk in chunks:
        metadata = chunk.metadata
        assert metadata.source == document.metadata.source
        assert metadata.document_type == document.metadata.document_type
        assert metadata.project_name == document.metadata.project_name
        assert document.content[metadata.start_char : metadata.end_char] == chunk.content


def test_comparison_exposes_both_strategies() -> None:
    comparison = compare_chunking_strategies(
        load_test_document(),
        structure_max_chars=180,
        fixed_chunk_size=180,
        fixed_overlap=20,
    )

    assert comparison.structure
    assert comparison.fixed
    assert all(chunk.metadata.strategy == "structure" for chunk in comparison.structure)
    assert all(chunk.metadata.strategy == "fixed" for chunk in comparison.fixed)
    assert [chunk.content for chunk in comparison.structure] != [
        chunk.content for chunk in comparison.fixed
    ]


def test_long_paragraph_is_split_at_maximum_size() -> None:
    document = Document(
        content="# Long\n\n" + "a" * 250,
        metadata=DocumentMetadata(
            source="long.md",
            file_name="long.md",
            document_type="profile",
            project_name=None,
        ),
    )

    chunks = chunk_by_structure(document, max_chars=100)

    assert max(len(chunk.content) for chunk in chunks) <= 100
    assert "".join(chunk.content for chunk in chunks) == document.content


@pytest.mark.parametrize("invalid_size", [0, -1])
def test_chunk_sizes_must_be_positive(invalid_size: int) -> None:
    document = load_test_document()

    with pytest.raises(ValueError, match="greater than 0"):
        chunk_by_structure(document, max_chars=invalid_size)
    with pytest.raises(ValueError, match="greater than 0"):
        chunk_by_fixed_size(document, chunk_size=invalid_size)


@pytest.mark.parametrize("overlap", [-1, 100])
def test_fixed_overlap_must_be_within_chunk_size(overlap: int) -> None:
    with pytest.raises(ValueError, match="overlap"):
        chunk_by_fixed_size(load_test_document(), chunk_size=100, overlap=overlap)

