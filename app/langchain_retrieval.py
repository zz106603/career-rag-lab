from typing import Any

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.retrievers import BaseRetriever
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

from app.config import Settings, get_settings
from app.embeddings import create_langchain_embeddings
from app.search import InvalidSearchInputError, SearchPayloadError, SearchResult


SCORE_METADATA_KEY = "_retrieval_score"


class ObservableQdrantRetriever(BaseRetriever):
    """LangChain Retriever 결과에 Qdrant score를 명시적으로 보존한다."""

    vector_store: QdrantVectorStore
    top_k: int = 5
    score_threshold: float | None = None

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        results = self.vector_store.similarity_search_with_score(
            query,
            k=self.top_k,
            score_threshold=self.score_threshold,
        )
        return [
            Document(
                id=document.id,
                page_content=document.page_content,
                metadata={**document.metadata, SCORE_METADATA_KEY: float(score)},
            )
            for document, score in results
        ]


class LangChainRetrievalService:
    """Retriever를 호출하되 기존 SearchResult 계약으로 결과를 노출한다."""

    def __init__(self, vector_store: QdrantVectorStore) -> None:
        self.vector_store = vector_store

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        score_threshold: float | None = None,
    ) -> list[SearchResult]:
        _validate_options(query, top_k, score_threshold)
        retriever = ObservableQdrantRetriever(
            vector_store=self.vector_store,
            top_k=top_k,
            score_threshold=score_threshold,
        )
        return [_to_search_result(document) for document in retriever.invoke(query)]


def create_langchain_retrieval_service(
    *,
    settings: Settings | None = None,
    embeddings: Embeddings | None = None,
    qdrant_client: QdrantClient | None = None,
) -> LangChainRetrievalService:
    active_settings = settings or get_settings()
    active_client = qdrant_client or QdrantClient(url=active_settings.qdrant_url)
    vector_store = QdrantVectorStore(
        client=active_client,
        collection_name=active_settings.qdrant_collection,
        embedding=embeddings or create_langchain_embeddings(active_settings),
        content_payload_key="content",
        metadata_payload_key="metadata",
        # 기본 검증은 dummy_text를 Embedding해 차원을 확인하므로 서비스 생성만으로
        # 유료 API가 호출된다. Collection 설정은 색인 단계에서 이미 검증한다.
        validate_collection_config=False,
    )
    return LangChainRetrievalService(vector_store)


def _validate_options(
    query: str, top_k: int, score_threshold: float | None
) -> None:
    if not query.strip():
        raise InvalidSearchInputError("query must not be empty")
    if top_k <= 0:
        raise InvalidSearchInputError("top_k must be greater than 0")
    if score_threshold is not None and not -1.0 <= score_threshold <= 1.0:
        raise InvalidSearchInputError("score_threshold must be between -1 and 1")


def _to_search_result(document: Document) -> SearchResult:
    metadata: dict[str, Any] = dict(document.metadata)
    source = metadata.pop("source", None)
    score = metadata.pop(SCORE_METADATA_KEY, None)
    if not isinstance(source, str) or not isinstance(score, (int, float)):
        raise SearchPayloadError(
            "Retriever result requires string source and numeric score"
        )
    return SearchResult(
        content=document.page_content,
        source=source,
        score=float(score),
        metadata=metadata,
    )
