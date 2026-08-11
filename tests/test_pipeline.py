from unittest.mock import Mock, patch

from app.pipeline import (
    DEFAULT_RAG_PIPELINE,
    create_default_answer_service,
    create_default_search_service,
)


def test_default_pipeline_is_langchain() -> None:
    assert DEFAULT_RAG_PIPELINE == "langchain"


@patch("app.pipeline.create_langchain_retrieval_service")
def test_default_search_uses_langchain_service(create_service: Mock) -> None:
    expected = Mock()
    create_service.return_value = expected

    assert create_default_search_service() is expected
    create_service.assert_called_once_with()


@patch("app.pipeline.create_langchain_rag_service")
def test_default_answer_uses_langchain_service(create_service: Mock) -> None:
    expected = Mock()
    create_service.return_value = expected

    assert create_default_answer_service() is expected
    create_service.assert_called_once_with()
