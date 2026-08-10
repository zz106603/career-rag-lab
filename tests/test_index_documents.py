from types import SimpleNamespace
from unittest.mock import Mock

from qdrant_client import QdrantClient
import pytest

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


def test_unchanged_documents_skip_embedding_and_keep_points() -> None:
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
    assert first.added_count == 6
    assert first.updated_count == 0
    assert first.unchanged_count == 0
    assert first.deleted_count == 0
    assert first.embedded_chunk_count == first.chunk_count
    assert second.added_count == 0
    assert second.updated_count == 0
    assert second.unchanged_count == 6
    assert second.deleted_count == 0
    assert second.embedded_chunk_count == 0
    assert first_count == first.chunk_count
    assert second_count == first_count
    assert openai_client.embeddings.create.call_count == 1


def test_modified_document_is_reembedded_and_replaces_old_chunks(tmp_path) -> None:
    first_path = tmp_path / "first.md"
    second_path = tmp_path / "second.md"
    first_path.write_text("# 첫 문서\n\n처음 내용", encoding="utf-8")
    second_path.write_text("# 둘째 문서\n\n유지할 내용", encoding="utf-8")
    settings = make_settings()
    openai_client = make_openai_client()
    qdrant_client = QdrantClient(":memory:")

    first = index_documents(
        tmp_path,
        settings=settings,
        openai_client=openai_client,
        qdrant_client=qdrant_client,
    )
    first_path.write_text("# 첫 문서\n\n수정된 새로운 내용", encoding="utf-8")
    second = index_documents(
        tmp_path,
        settings=settings,
        openai_client=openai_client,
        qdrant_client=qdrant_client,
    )
    records, _ = qdrant_client.scroll(
        settings.qdrant_collection, limit=100, with_payload=True
    )
    contents = [record.payload["content"] for record in records]

    assert first.added_count == 2
    assert second.added_count == 0
    assert second.updated_count == 1
    assert second.unchanged_count == 1
    assert second.deleted_count == 0
    assert second.embedded_chunk_count == 1
    assert openai_client.embeddings.create.call_count == 2
    assert any("수정된 새로운 내용" in content for content in contents)
    assert all("처음 내용" not in content for content in contents)


def test_deleted_document_points_are_removed_without_embedding(tmp_path) -> None:
    first_path = tmp_path / "first.md"
    second_path = tmp_path / "second.md"
    first_path.write_text("# 첫 문서\n\n남길 내용", encoding="utf-8")
    second_path.write_text("# 둘째 문서\n\n삭제할 내용", encoding="utf-8")
    settings = make_settings()
    openai_client = make_openai_client()
    qdrant_client = QdrantClient(":memory:")
    index_documents(
        tmp_path,
        settings=settings,
        openai_client=openai_client,
        qdrant_client=qdrant_client,
    )

    second_path.unlink()
    summary = index_documents(
        tmp_path,
        settings=settings,
        openai_client=openai_client,
        qdrant_client=qdrant_client,
    )
    records, _ = qdrant_client.scroll(
        settings.qdrant_collection, limit=100, with_payload=True
    )

    assert summary.added_count == 0
    assert summary.updated_count == 0
    assert summary.unchanged_count == 1
    assert summary.deleted_count == 1
    assert summary.embedded_chunk_count == 0
    assert openai_client.embeddings.create.call_count == 1
    assert {record.payload["source"] for record in records} == {"first.md"}


def test_embedding_failure_does_not_delete_missing_document(tmp_path) -> None:
    first_path = tmp_path / "first.md"
    second_path = tmp_path / "second.md"
    first_path.write_text("# 첫 문서\n\n처음 내용", encoding="utf-8")
    second_path.write_text("# 둘째 문서\n\n삭제 예정 내용", encoding="utf-8")
    settings = make_settings()
    openai_client = make_openai_client()
    qdrant_client = QdrantClient(":memory:")
    index_documents(
        tmp_path,
        settings=settings,
        openai_client=openai_client,
        qdrant_client=qdrant_client,
    )

    first_path.write_text("# 첫 문서\n\n수정 내용", encoding="utf-8")
    second_path.unlink()
    openai_client.embeddings.create.side_effect = RuntimeError("embedding failed")

    with pytest.raises(RuntimeError, match="embedding failed"):
        index_documents(
            tmp_path,
            settings=settings,
            openai_client=openai_client,
            qdrant_client=qdrant_client,
        )

    records, _ = qdrant_client.scroll(
        settings.qdrant_collection, limit=100, with_payload=True
    )
    assert {record.payload["source"] for record in records} == {
        "first.md",
        "second.md",
    }
    assert any("처음 내용" in record.payload["content"] for record in records)

