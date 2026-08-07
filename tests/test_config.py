from app.config import get_settings


def test_qdrant_url_uses_default(monkeypatch) -> None:
    monkeypatch.delenv("QDRANT_URL", raising=False)

    assert get_settings().qdrant_url == "http://localhost:6333"


def test_qdrant_url_uses_environment_variable(monkeypatch) -> None:
    monkeypatch.setenv("QDRANT_URL", "http://qdrant.example:6333")

    assert get_settings().qdrant_url == "http://qdrant.example:6333"

