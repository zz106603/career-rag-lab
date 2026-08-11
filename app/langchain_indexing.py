import uuid
from collections.abc import Sequence

from langchain_core.embeddings import Embeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, models

from app.embeddings import EmbeddedChunk
from app.indexing import (
    IndexResult,
    IndexedDocumentState,
    IndexingError,
    InvalidIndexInputError,
    QdrantIndexer,
)


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
    document_hash: str | None = None,
    index_fingerprint: str | None = None,
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
    metadatas = [
        _to_metadata(
            item,
            document_hash=document_hash,
            index_fingerprint=index_fingerprint,
        )
        for item in items
    ]
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


class LangChainQdrantIndexer:
    """증분 상태를 보존하면서 LangChain payload로 문서를 관리한다."""

    def __init__(self, client: QdrantClient, collection_name: str, vector_size: int):
        self.client = client
        self.collection_name = collection_name
        self.vector_size = vector_size
        self._collection = QdrantIndexer(client, collection_name, vector_size)

    def ensure_collection(self) -> bool:
        return self._collection.ensure_collection()

    def index_document(
        self,
        items: list[EmbeddedChunk],
        *,
        document_hash: str | None = None,
        index_fingerprint: str | None = None,
    ) -> IndexResult:
        return index_document_with_langchain(
            items,
            client=self.client,
            collection_name=self.collection_name,
            vector_size=self.vector_size,
            document_hash=document_hash,
            index_fingerprint=index_fingerprint,
        )

    def delete_document(self, document_id: str) -> None:
        self.client.delete(
            collection_name=self.collection_name,
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

    def list_indexed_documents(self) -> dict[str, IndexedDocumentState]:
        if not self.client.collection_exists(self.collection_name):
            return {}
        states: dict[str, IndexedDocumentState] = {}
        offset = None
        while True:
            records, offset = self.client.scroll(
                self.collection_name,
                limit=256,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            for record in records:
                metadata = (record.payload or {}).get("metadata")
                if not isinstance(metadata, dict):
                    raise IndexingError("LangChain Point requires metadata payload")
                document_id = metadata.get("document_id")
                source = metadata.get("source")
                if not isinstance(document_id, str) or not isinstance(source, str):
                    raise IndexingError(
                        "Indexed Point requires string document_id and source"
                    )
                state = IndexedDocumentState(
                    document_id=document_id,
                    source=source,
                    document_hash=_optional_string(metadata.get("document_hash")),
                    index_fingerprint=_optional_string(
                        metadata.get("index_fingerprint")
                    ),
                )
                previous = states.get(document_id)
                if previous is not None and previous != state:
                    raise IndexingError(
                        f"Indexed document state is inconsistent: {document_id}"
                    )
                states[document_id] = state
            if offset is None:
                return states


def _to_metadata(
    item: EmbeddedChunk,
    *,
    document_hash: str | None = None,
    index_fingerprint: str | None = None,
) -> dict[str, object]:
    metadata = item.chunk.metadata
    result: dict[str, object] = {
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
    if document_hash is not None:
        result["document_hash"] = document_hash
    if index_fingerprint is not None:
        result["index_fingerprint"] = index_fingerprint
    return result


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise IndexingError("Indexed document hashes must be strings")
    return value
