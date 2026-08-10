import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from openai import OpenAI
from qdrant_client import QdrantClient

from app.chunking import Chunk, chunk_by_structure
from app.config import Settings, get_settings
from app.documents import Document, load_markdown_directory
from app.embeddings import EmbeddedChunk, create_openai_client, embed_chunks
from app.indexing import IndexedDocumentState, create_qdrant_indexer


DEFAULT_DOCUMENTS_PATH = Path(__file__).parents[1] / "data" / "documents"


@dataclass(frozen=True)
class IndexingSummary:
    collection_name: str
    document_count: int
    chunk_count: int
    added_count: int
    updated_count: int
    unchanged_count: int
    deleted_count: int
    embedded_chunk_count: int


@dataclass(frozen=True)
class PreparedDocument:
    document_id: str
    document_hash: str
    index_fingerprint: str
    chunks: list[Chunk]


def index_documents(
    documents_path: Path = DEFAULT_DOCUMENTS_PATH,
    *,
    max_chars: int = 500,
    settings: Settings | None = None,
    openai_client: OpenAI | None = None,
    qdrant_client: QdrantClient | None = None,
) -> IndexingSummary:
    """Markdown 전체를 Chunking·Embedding한 뒤 영구 Collection에 색인한다."""
    active_settings = settings or get_settings()
    documents = load_markdown_directory(documents_path)
    prepared_documents = [
        _prepare_document(document, max_chars=max_chars, settings=active_settings)
        for document in documents
    ]
    indexer = create_qdrant_indexer(
        client=qdrant_client,
        settings=active_settings,
    )
    indexer.ensure_collection()
    existing_states = indexer.list_indexed_documents()
    current_ids = {item.document_id for item in prepared_documents}
    deleted_ids = sorted(set(existing_states) - current_ids)

    added = [
        item for item in prepared_documents if item.document_id not in existing_states
    ]
    updated = [
        item
        for item in prepared_documents
        if item.document_id in existing_states
        and not _state_matches(item, existing_states[item.document_id])
    ]
    unchanged = [
        item
        for item in prepared_documents
        if item.document_id in existing_states
        and _state_matches(item, existing_states[item.document_id])
    ]
    changed = added + updated
    changed_chunks = [chunk for item in changed for chunk in item.chunks]

    # 변경된 Chunk가 하나도 없으면 OpenAI 클라이언트조차 만들지 않는다.
    embedded_chunks = (
        embed_chunks(
            changed_chunks,
            client=openai_client or create_openai_client(active_settings),
            settings=active_settings,
        )
        if changed_chunks
        else []
    )
    grouped_items: dict[str, list[EmbeddedChunk]] = {}
    for item in embedded_chunks:
        document_id = item.chunk.metadata.document_id
        grouped_items.setdefault(document_id, []).append(item)

    prepared_by_id = {item.document_id: item for item in changed}
    for document_id, items in grouped_items.items():
        prepared = prepared_by_id[document_id]
        indexer.index_document(
            items,
            document_hash=prepared.document_hash,
            index_fingerprint=prepared.index_fingerprint,
        )

    # 새 Embedding과 수정 문서 저장이 모두 끝난 뒤 현재 디렉터리에서 사라진
    # 문서를 삭제한다. Embedding 실패로 기존 색인이 먼저 지워지는 것을 막는다.
    for document_id in deleted_ids:
        indexer.delete_document(document_id)

    return IndexingSummary(
        collection_name=active_settings.qdrant_collection,
        document_count=len(documents),
        chunk_count=sum(len(item.chunks) for item in prepared_documents),
        added_count=len(added),
        updated_count=len(updated),
        unchanged_count=len(unchanged),
        deleted_count=len(deleted_ids),
        embedded_chunk_count=len(changed_chunks),
    )


def _prepare_document(
    document: Document, *, max_chars: int, settings: Settings
) -> PreparedDocument:
    chunks = chunk_by_structure(document, max_chars=max_chars)
    document_hash = hashlib.sha256(document.content.encode("utf-8")).hexdigest()
    fingerprint_input = {
        "document_hash": document_hash,
        "strategy": "structure",
        "max_chars": max_chars,
        "embedding_model": settings.embedding_model,
        "embedding_dimensions": settings.embedding_dimensions,
    }
    index_fingerprint = hashlib.sha256(
        json.dumps(fingerprint_input, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return PreparedDocument(
        document_id=chunks[0].metadata.document_id,
        document_hash=document_hash,
        index_fingerprint=index_fingerprint,
        chunks=chunks,
    )


def _state_matches(
    prepared: PreparedDocument, state: IndexedDocumentState
) -> bool:
    return (
        state.document_hash == prepared.document_hash
        and state.index_fingerprint == prepared.index_fingerprint
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="학습용 Markdown 문서를 OpenAI로 Embedding해 Qdrant에 색인합니다."
    )
    parser.add_argument(
        "--documents",
        type=Path,
        default=DEFAULT_DOCUMENTS_PATH,
        help="Markdown 문서 디렉터리",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=500,
        help="구조 기반 Chunk의 최대 글자 수",
    )
    args = parser.parse_args()

    summary = index_documents(args.documents, max_chars=args.max_chars)
    # 키나 원문은 출력하지 않고 수동 검증에 필요한 집계만 보여준다.
    print(
        f"collection={summary.collection_name} "
        f"documents={summary.document_count} chunks={summary.chunk_count} "
        f"added={summary.added_count} updated={summary.updated_count} "
        f"unchanged={summary.unchanged_count} deleted={summary.deleted_count} "
        f"embedded_chunks={summary.embedded_chunk_count}"
    )


if __name__ == "__main__":
    main()

