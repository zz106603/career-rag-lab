from unittest.mock import Mock

import pytest

from app.config import get_settings
from app.langchain_rag import create_langchain_rag_service
from app.search import SearchResult


@pytest.mark.live_api
def test_langchain_rag_generates_answer_from_synthetic_evidence() -> None:
    retrieval_service = Mock()
    retrieval_service.search.return_value = [
        SearchResult(
            content="합성 프로젝트에서 장애 알림 자동화를 구현했다.",
            source="synthetic.md",
            score=0.9,
            metadata={"section": "합성 경험"},
        )
    ]
    service = create_langchain_rag_service(
        settings=get_settings(), retrieval_service=retrieval_service
    )

    result = service.answer("장애 대응 자동화 경험이 있나요?")

    assert result.status == "answered"
    assert result.answer.strip()
    assert result.sources == ["synthetic.md"]
    assert result.generated is True
