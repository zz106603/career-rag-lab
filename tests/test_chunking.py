from pathlib import Path

import pytest

from app.chunking import (
    chunk_by_fixed_size,
    chunk_by_langchain_recursive,
    chunk_by_structure,
    compare_chunking_strategies,
    summarize_chunks,
)
from app.compare_chunking import compare_document
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
        langchain_chunk_size=180,
        langchain_overlap=20,
    )

    assert comparison.structure
    assert comparison.fixed
    assert comparison.langchain_recursive
    assert all(chunk.metadata.strategy == "structure" for chunk in comparison.structure)
    assert all(chunk.metadata.strategy == "fixed" for chunk in comparison.fixed)
    assert all(
        chunk.metadata.strategy == "langchain_recursive"
        for chunk in comparison.langchain_recursive
    )
    assert [chunk.content for chunk in comparison.structure] != [
        chunk.content for chunk in comparison.fixed
    ]


def test_langchain_chunks_preserve_content_source_and_metadata() -> None:
    document = load_test_document()

    chunks = chunk_by_langchain_recursive(document, chunk_size=180, overlap=20)

    assert chunks
    assert [chunk.metadata.chunk_index for chunk in chunks] == list(range(len(chunks)))
    assert len({chunk.metadata.document_id for chunk in chunks}) == 1
    for chunk in chunks:
        metadata = chunk.metadata
        assert metadata.source == document.metadata.source
        assert metadata.document_type == document.metadata.document_type
        assert metadata.project_name == document.metadata.project_name
        assert metadata.section
        assert document.content[metadata.start_char : metadata.end_char] == chunk.content


def test_langchain_splitter_keeps_configured_maximum_and_overlap() -> None:
    document = Document(
        content="A" * 140 + "B" * 140 + "C" * 140,
        metadata=DocumentMetadata(
            source="continuous.md",
            file_name="continuous.md",
            document_type="profile",
            project_name=None,
        ),
    )

    chunks = chunk_by_langchain_recursive(document, chunk_size=160, overlap=30)
    statistics = summarize_chunks(chunks)

    assert max(statistics.lengths) <= 160
    assert statistics.overlaps == (30, 30)
    assert all(
        previous.content[-30:] == current.content[:30]
        for previous, current in zip(chunks, chunks[1:])
    )


def test_statistics_expose_count_average_boundaries_and_overlap() -> None:
    chunks = chunk_by_fixed_size(load_test_document(), chunk_size=180, overlap=20)

    statistics = summarize_chunks(chunks)

    assert statistics.chunk_count == len(chunks)
    assert statistics.average_length == pytest.approx(
        sum(len(chunk.content) for chunk in chunks) / len(chunks)
    )
    assert statistics.boundaries == tuple(
        (chunk.metadata.start_char, chunk.metadata.end_char) for chunk in chunks
    )
    assert statistics.overlaps == (20,) * (len(chunks) - 1)


def test_comparison_report_shows_three_strategies_and_observable_values() -> None:
    report = compare_document(DOCUMENT_PATH, chunk_size=180, overlap=20)

    assert "strategy chunks average_length boundaries overlaps" in report
    assert "structure 5 119.20" in report
    assert "fixed 4 164.00" in report
    assert "langchain_recursive 4 150.75" in report


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
    with pytest.raises(ValueError, match="greater than 0"):
        chunk_by_langchain_recursive(document, chunk_size=invalid_size)


@pytest.mark.parametrize("overlap", [-1, 100])
def test_fixed_overlap_must_be_within_chunk_size(overlap: int) -> None:
    with pytest.raises(ValueError, match="overlap"):
        chunk_by_fixed_size(load_test_document(), chunk_size=100, overlap=overlap)
    with pytest.raises(ValueError, match="overlap"):
        chunk_by_langchain_recursive(
            load_test_document(), chunk_size=100, overlap=overlap
        )

