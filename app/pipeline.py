from typing import Literal

from app.langchain_rag import LangChainRagService, create_langchain_rag_service
from app.langchain_retrieval import (
    LangChainRetrievalService,
    create_langchain_retrieval_service,
)


# 증분 색인부터 검색·답변까지 같은 LangChain payload를 사용하는 기본 경로다.
DEFAULT_RAG_PIPELINE: Literal["langchain"] = "langchain"


def create_default_search_service() -> LangChainRetrievalService:
    """API가 사용하는 기본 검색 경로를 한 곳에서 명시한다."""
    return create_langchain_retrieval_service()


def create_default_answer_service() -> LangChainRagService:
    """API가 사용하는 기본 답변 경로를 한 곳에서 명시한다."""
    return create_langchain_rag_service()
