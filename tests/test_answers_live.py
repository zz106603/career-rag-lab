from openai import OpenAI
import pytest

from app.answers import AnswerService
from app.config import get_settings
from app.embeddings import create_openai_client
from app.search import SearchResult


@pytest.mark.live_api
def test_gpt_5_nano_generates_answer_from_supplied_evidence() -> None:
    settings = get_settings()
    search_service = type(
        "FixedSearchService",
        (),
        {
            "search": lambda self, query, top_k: [
                SearchResult(
                    content="합성 문서에 따르면 장애 알림 분류를 자동화했다.",
                    source="synthetic.md",
                    score=0.9,
                    metadata={"section": "경험"},
                )
            ]
        },
    )()
    client: OpenAI = create_openai_client(settings)

    result = AnswerService(search_service, client, settings).answer(
        "어떤 자동화 경험이 있나요?"
    )

    assert result.status == "answered"
    assert result.generated is True
    assert result.answer.strip()
    assert result.sources == ["synthetic.md"]
