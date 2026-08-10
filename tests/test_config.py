import pytest

from app.config import get_settings


def test_qdrant_url_uses_default(monkeypatch) -> None:
    monkeypatch.delenv("QDRANT_URL", raising=False)

    assert get_settings().qdrant_url == "http://localhost:6333"


def test_qdrant_url_uses_environment_variable(monkeypatch) -> None:
    monkeypatch.setenv("QDRANT_URL", "http://qdrant.example:6333")

    assert get_settings().qdrant_url == "http://qdrant.example:6333"


def test_qdrant_collection_uses_environment_variable(monkeypatch) -> None:
    monkeypatch.setenv("QDRANT_COLLECTION", "test_documents")

    assert get_settings().qdrant_collection == "test_documents"



def test_embedding_settings_use_low_cost_defaults(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_EMBEDDING_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_EMBEDDING_DIMENSIONS", raising=False)
    monkeypatch.delenv("OPENAI_EMBEDDING_BATCH_SIZE", raising=False)

    settings = get_settings()

    assert settings.embedding_model == "text-embedding-3-small"
    assert settings.embedding_dimensions == 1536
    assert settings.embedding_batch_size == 100


def test_answer_settings_use_low_cost_defaults(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_CHAT_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_ANSWER_MAX_OUTPUT_TOKENS", raising=False)
    monkeypatch.delenv("ANSWER_TOP_K", raising=False)
    monkeypatch.delenv("ANSWER_SCORE_THRESHOLD", raising=False)

    settings = get_settings()

    assert settings.chat_model == "gpt-5-nano"
    assert settings.answer_max_output_tokens == 300
    assert settings.answer_top_k == 3
    assert settings.answer_score_threshold == 0.4


def test_embedding_settings_use_environment_variables(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_EMBEDDING_MODEL", "custom-embedding-model")
    monkeypatch.setenv("OPENAI_EMBEDDING_DIMENSIONS", "512")
    monkeypatch.setenv("OPENAI_EMBEDDING_BATCH_SIZE", "20")

    settings = get_settings()

    assert settings.embedding_model == "custom-embedding-model"
    assert settings.embedding_dimensions == 512
    assert settings.embedding_batch_size == 20


@pytest.mark.parametrize("value", ["zero", "0", "-1"])
def test_embedding_dimensions_must_be_a_positive_integer(
    monkeypatch, value: str
) -> None:
    monkeypatch.setenv("OPENAI_EMBEDDING_DIMENSIONS", value)

    with pytest.raises(ValueError, match="OPENAI_EMBEDDING_DIMENSIONS"):
        get_settings()

