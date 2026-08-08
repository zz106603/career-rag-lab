import uuid
from dataclasses import dataclass

from qdrant_client import QdrantClient, models

from app.config import Settings, get_settings
from app.embeddings import EmbeddedChunk


class IndexingError(ValueError):
    """색인 입력이나 Collection 설정을 신뢰할 수 없을 때 발생한다."""


class CollectionConfigurationError(IndexingError):
    """기존 Collection의 벡터 설정이 현재 Embedding 설정과 다를 때 발생한다."""


class InvalidIndexInputError(IndexingError):
    """하나의 문서로 색인할 수 없는 입력이 전달되면 발생한다."""


@dataclass(frozen=True)
class IndexResult:
    document_id: str
    point_ids: list[str]


class QdrantIndexer:
    """EmbeddedChunk를 Qdrant Point로 변환하고 문서 단위로 관리한다."""

    def __init__(
        self, client: QdrantClient, collection_name: str, vector_size: int
    ) -> None:
        if not collection_name.strip():
            raise ValueError("collection_name must not be empty")
        if vector_size <= 0:
            raise ValueError("vector_size must be greater than 0")
        self.client = client
        self.collection_name = collection_name
        self.vector_size = vector_size

    def ensure_collection(self) -> bool:
        """Collection을 만들거나 기존 설정이 현재 Embedding과 같은지 검증한다.

        반환값은 이번 호출에서 새 Collection을 만들었는지를 나타낸다.
        """
        if not self.client.collection_exists(self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=self.vector_size,
                    distance=models.Distance.COSINE,
                ),
            )
            return True

        collection = self.client.get_collection(self.collection_name)
        vector_config = collection.config.params.vectors
        if not isinstance(vector_config, models.VectorParams):
            raise CollectionConfigurationError(
                "Named vector collections are not supported by this indexer"
            )
        if vector_config.size != self.vector_size:
            raise CollectionConfigurationError(
                f"Collection vector size is {vector_config.size}, "
                f"but Embedding size is {self.vector_size}"
            )
        if vector_config.distance != models.Distance.COSINE:
            raise CollectionConfigurationError(
                "Collection distance must be Cosine"
            )
        return False

    def index_document(self, items: list[EmbeddedChunk]) -> IndexResult:
        """한 문서의 기존 Point를 지우고 현재 Chunk 집합으로 교체한다."""
        document_id = self._validate_items(items)
        self.ensure_collection()

        # 벡터 검증이 모두 끝난 뒤 삭제해야 잘못된 입력 때문에 기존 색인이
        # 먼저 사라지는 일을 막을 수 있다.
        self.delete_document(document_id)
        points = [self._to_point(item) for item in items]
        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
            wait=True,
        )
        return IndexResult(
            document_id=document_id,
            point_ids=[str(point.id) for point in points],
        )

    def delete_document(self, document_id: str) -> None:
        """payload의 document_id가 같은 Point를 모두 삭제한다."""
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=_document_filter(document_id),
            wait=True,
        )

    def count_document(self, document_id: str) -> int:
        """재색인 중복 여부를 관찰할 수 있도록 문서별 Point 수를 반환한다."""
        result = self.client.count(
            collection_name=self.collection_name,
            count_filter=_document_filter(document_id),
            exact=True,
        )
        return result.count

    def _validate_items(self, items: list[EmbeddedChunk]) -> str:
        if not items:
            raise InvalidIndexInputError("At least one EmbeddedChunk is required")

        document_ids = {item.chunk.metadata.document_id for item in items}
        if len(document_ids) != 1:
            raise InvalidIndexInputError(
                "index_document accepts chunks from exactly one document"
            )
        chunk_ids = [item.chunk.metadata.chunk_id for item in items]
        if len(set(chunk_ids)) != len(chunk_ids):
            raise InvalidIndexInputError("Chunk IDs must be unique within a document")
        for item in items:
            if len(item.vector) != self.vector_size:
                raise InvalidIndexInputError(
                    "Embedding vector dimension does not match the Collection"
                )
        return next(iter(document_ids))

    def _to_point(self, item: EmbeddedChunk) -> models.PointStruct:
        chunk = item.chunk
        metadata = chunk.metadata
        # Qdrant Point ID는 UUID 또는 정수여야 하므로 결정적 chunk_id를 UUID5로
        # 변환한다. 원래 chunk_id는 payload에도 보존한다.
        point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, metadata.chunk_id))
        payload = {
            "document_id": metadata.document_id,
            "chunk_id": metadata.chunk_id,
            "content": chunk.content,
            "source": metadata.source,
            "section": metadata.section,
            "chunk_index": metadata.chunk_index,
            "document_type": metadata.document_type,
            "project_name": metadata.project_name,
            "strategy": metadata.strategy,
            "start_char": metadata.start_char,
            "end_char": metadata.end_char,
        }
        return models.PointStruct(id=point_id, vector=item.vector, payload=payload)


def create_qdrant_indexer(
    client: QdrantClient | None = None, settings: Settings | None = None
) -> QdrantIndexer:
    active_settings = settings or get_settings()
    active_client = client or QdrantClient(url=active_settings.qdrant_url)
    return QdrantIndexer(
        client=active_client,
        collection_name=active_settings.qdrant_collection,
        vector_size=active_settings.embedding_dimensions,
    )


def _document_filter(document_id: str) -> models.Filter:
    return models.Filter(
        must=[
            models.FieldCondition(
                key="document_id",
                match=models.MatchValue(value=document_id),
            )
        ]
    )

