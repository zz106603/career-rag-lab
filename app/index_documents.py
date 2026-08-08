import argparse
from dataclasses import dataclass
from pathlib import Path

from openai import OpenAI
from qdrant_client import QdrantClient

from app.chunking import chunk_by_structure
from app.config import Settings, get_settings
from app.documents import load_markdown_directory
from app.embeddings import EmbeddedChunk, create_openai_client, embed_chunks
from app.indexing import create_qdrant_indexer


DEFAULT_DOCUMENTS_PATH = Path(__file__).parents[1] / "data" / "documents"


@dataclass(frozen=True)
class IndexingSummary:
    collection_name: str
    document_count: int
    chunk_count: int


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
    chunks = [
        chunk
        for document in documents
        for chunk in chunk_by_structure(document, max_chars=max_chars)
    ]

    # 모든 문서의 Chunk를 한꺼번에 전달하면 batch 크기 안에서는 API 호출을
    # 합칠 수 있다. 결과는 document ID별로 다시 묶어 문서 단위로 교체한다.
    embedded_chunks = embed_chunks(
        chunks,
        client=openai_client or create_openai_client(active_settings),
        settings=active_settings,
    )
    grouped_items: dict[str, list[EmbeddedChunk]] = {}
    for item in embedded_chunks:
        document_id = item.chunk.metadata.document_id
        grouped_items.setdefault(document_id, []).append(item)

    indexer = create_qdrant_indexer(
        client=qdrant_client,
        settings=active_settings,
    )
    for items in grouped_items.values():
        indexer.index_document(items)

    return IndexingSummary(
        collection_name=active_settings.qdrant_collection,
        document_count=len(documents),
        chunk_count=len(chunks),
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
        f"documents={summary.document_count} chunks={summary.chunk_count}"
    )


if __name__ == "__main__":
    main()

