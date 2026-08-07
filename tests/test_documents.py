from pathlib import Path

import pytest

from app.documents import (
    EmptyDocumentError,
    UnsupportedDocumentError,
    load_markdown_directory,
    load_markdown_file,
)


PROJECT_ROOT = Path(__file__).parents[1]
DOCUMENTS_DIR = PROJECT_ROOT / "data" / "documents"


def test_load_markdown_file_preserves_content_and_metadata() -> None:
    path = DOCUMENTS_DIR / "finance-transfer-system.md"

    document = load_markdown_file(path)

    assert document.content == path.read_text(encoding="utf-8")
    assert document.metadata.source == "finance-transfer-system.md"
    assert document.metadata.file_name == "finance-transfer-system.md"
    assert document.metadata.document_type == "project"
    assert document.metadata.project_name == "재무자료 전송 시스템"


def test_load_profile_document_has_no_project_name() -> None:
    document = load_markdown_file(DOCUMENTS_DIR / "backend-skills.md")

    assert document.metadata.document_type == "profile"
    assert document.metadata.project_name is None


def test_load_markdown_directory_returns_all_documents_in_source_order() -> None:
    documents = load_markdown_directory(DOCUMENTS_DIR)

    assert len(documents) == 6
    assert [document.metadata.source for document in documents] == sorted(
        path.name for path in DOCUMENTS_DIR.glob("*.md")
    )
    assert all(document.content for document in documents)


def test_load_markdown_file_rejects_empty_document(tmp_path: Path) -> None:
    empty_document = tmp_path / "empty.md"
    empty_document.write_text("  \n", encoding="utf-8")

    with pytest.raises(EmptyDocumentError, match="empty.md"):
        load_markdown_file(empty_document)


def test_directory_load_stops_when_a_markdown_document_is_empty(
    tmp_path: Path,
) -> None:
    (tmp_path / "valid.md").write_text("# Valid\n", encoding="utf-8")
    (tmp_path / "empty.md").write_text("", encoding="utf-8")

    with pytest.raises(EmptyDocumentError, match="empty.md"):
        load_markdown_directory(tmp_path)


def test_load_markdown_file_rejects_unsupported_extension(tmp_path: Path) -> None:
    text_document = tmp_path / "document.txt"
    text_document.write_text("not Markdown", encoding="utf-8")

    with pytest.raises(UnsupportedDocumentError, match="document.txt"):
        load_markdown_file(text_document)


def test_directory_load_ignores_non_markdown_files(tmp_path: Path) -> None:
    (tmp_path / "document.md").write_text("# Markdown\n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("ignored", encoding="utf-8")

    documents = load_markdown_directory(tmp_path)

    assert [document.metadata.source for document in documents] == ["document.md"]


def test_load_markdown_file_rejects_missing_path(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.md"

    with pytest.raises(FileNotFoundError, match="missing.md"):
        load_markdown_file(missing_path)


def test_load_markdown_directory_rejects_file_path(tmp_path: Path) -> None:
    file_path = tmp_path / "document.md"
    file_path.write_text("# Document\n", encoding="utf-8")

    with pytest.raises(NotADirectoryError, match="document.md"):
        load_markdown_directory(file_path)

