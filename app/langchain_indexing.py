import uuid
from collections.abc import Sequence

from langchain_core.embeddings import Embeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, models

from app.embeddings import EmbeddedChunk
from app.indexing import IndexResult, InvalidIndexInputError, QdrantIndexer


class PrecomputedEmbeddings(Embeddings):
    """이미 생성한 벡터를 LangChain VectorStore에 전달하는 비교용 Adapter.

    P2-03에서는 VectorStore만 비교해야 하므로 같은 Chunk를 OpenAI에 다시 보내지
    않는다. 예상과 다른 텍스트를 받으면 잘못된 벡터 연결을 막기 위해 실패한다.
    """

    def __init__(self, texts: list[str], vectors: list[list[float]]) -> None:
        self._texts = texts
        self._vectors = vectors

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if texts != self._texts:
            raise InvalidIndexInputError(
                "LangChain requested texts in an unexpected order"
            )
        return [list(vector) for vector in self._vectors]

    def embed_query(self, text: str) -> list[float]:
        raise NotImplementedError("PrecomputedEmbeddings supports indexing only")


def index_document_with_langchain(
    items: list[EmbeddedChunk],
    *,
    client: QdrantClient,
    collection_name: str,
    vector_size: int,
) -> IndexResult:
    """기존 EmbeddedChunk를 LangChain QdrantVectorStore로 문서 단위 저장한다."""
    document_id = _validate_items(items, vector_size)
    indexer = QdrantIndexer(client, collection_name, vector_size)
    indexer.ensure_collection()

    texts = [item.chunk.content for item in items]
    vectors = [item.vector for item in items]
    point_ids = [
        str(uuid.uuid5(uuid.NAMESPACE_URL, item.chunk.metadata.chunk_id))
        for item in items
    ]
    metadatas = [_to_metadata(item) for item in items]
    vector_store = QdrantVectorStore(
        client=client,
        collection_name=collection_name,
        embedding=PrecomputedEmbeddings(texts, vectors),
        content_payload_key="content",
        metadata_payload_key="metadata",
        # Collection 검증은 기존 QdrantIndexer가 실제 vector size와 Cosine 설정을
        # 확인한다. 비교용 Embeddings에 dummy API 호출을 요구하지 않게 한다.
        validate_collection_config=False,
    )

    # LangChain도 단순 upsert만으로 stale Chunk를 제거하지 않으므로 기존과 같은
    # 문서 단위 교체 규칙을 명시적으로 적용한다.
    client.delete(
        collection_name=collection_name,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="metadata.document_id",
                        match=models.MatchValue(value=document_id),
                    )
                ]
            )
        ),
        wait=True,
    )
    vector_store.add_texts(
        texts=texts,
        metadatas=metadatas,
        ids=point_ids,
        batch_size=len(items),
    )
    return IndexResult(document_id=document_id, point_ids=point_ids)


def _validate_items(items: Sequence[EmbeddedChunk], vector_size: int) -> str:
    if not items:
        raise InvalidIndexInputError("At least one EmbeddedChunk is required")
    document_ids = {item.chunk.metadata.document_id for item in items}
    if len(document_ids) != 1:
        raise InvalidIndexInputError(
            "index_document accepts chunks from exactly one document"
        )
    chunk_ids = [item.chunk.metadata.chunk_id for item in items]
    if len(set(chunk_ids)) != len(chunk_ids):
        raise InvalidIndexInputError("Chunk IDs must be unique")
    if any(len(item.vector) != vector_size for item in items):
        raise InvalidIndexInputError(
            "Embedding vector dimension does not match the collection"
        )
    return next(iter(document_ids))


def _to_metadata(item: EmbeddedChunk) -> dict[str, object]:
    metadata = item.chunk.metadata
    return {
        "document_id": metadata.document_id,
        "chunk_id": metadata.chunk_id,
        "source": metadata.source,
        "section": metadata.section,
        "chunk_index": metadata.chunk_index,
        "document_type": metadata.document_type,
        "project_name": metadata.project_name,
        "strategy": metadata.strategy,
        "start_char": metadata.start_char,
        "end_char": metadata.end_char,
    }
