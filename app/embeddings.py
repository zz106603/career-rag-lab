from dataclasses import dataclass

from openai import OpenAI

from app.chunking import Chunk
from app.config import Settings, get_settings


class EmbeddingError(ValueError):
    """Embedding 입력이나 응답을 신뢰할 수 없을 때 발생한다."""


class MissingOpenAIAPIKeyError(EmbeddingError):
    """실제 OpenAI 클라이언트를 만들 때 API 키가 없으면 발생한다."""


class EmptyEmbeddingInputError(EmbeddingError):
    """Embedding할 Chunk가 하나도 없을 때 발생한다."""


class EmbeddingResponseError(EmbeddingError):
    """API 응답의 개수나 벡터 차원이 설정과 다를 때 발생한다."""


@dataclass(frozen=True)
class EmbeddedChunk:
    """원본 Chunk와 API가 반환한 벡터를 순서대로 연결한다."""

    chunk: Chunk
    vector: list[float]


def create_openai_client(settings: Settings | None = None) -> OpenAI:
    """환경변수의 비밀 키로 OpenAI 클라이언트를 만든다."""
    active_settings = settings or get_settings()
    if not active_settings.openai_api_key:
        raise MissingOpenAIAPIKeyError("OPENAI_API_KEY is not configured")
    return OpenAI(api_key=active_settings.openai_api_key)


def embed_chunks(
    chunks: list[Chunk],
    client: OpenAI | None = None,
    settings: Settings | None = None,
) -> list[EmbeddedChunk]:
    """Chunk를 batch로 나눠 Embedding하고 입력 순서대로 벡터를 연결한다.

    API 예외는 숨기거나 키와 함께 다시 출력하지 않고 그대로 전달한다.
    호출자가 네트워크 오류, 인증 오류, rate limit을 구분해 처리할 수 있다.
    """
    if not chunks:
        raise EmptyEmbeddingInputError("At least one Chunk is required")

    active_settings = settings or get_settings()
    active_client = client or create_openai_client(active_settings)
    embedded_chunks: list[EmbeddedChunk] = []

    for start in range(0, len(chunks), active_settings.embedding_batch_size):
        batch = chunks[start : start + active_settings.embedding_batch_size]
        response = active_client.embeddings.create(
            model=active_settings.embedding_model,
            input=[chunk.content for chunk in batch],
            dimensions=active_settings.embedding_dimensions,
        )

        # API의 index를 기준으로 정렬해야 요청한 Chunk 순서와 정확히 대응한다.
        response_items = sorted(response.data, key=lambda item: item.index)
        if len(response_items) != len(batch):
            raise EmbeddingResponseError(
                "Embedding response count does not match the input count"
            )

        for chunk, response_item in zip(batch, response_items):
            vector = list(response_item.embedding)
            if len(vector) != active_settings.embedding_dimensions:
                raise EmbeddingResponseError(
                    "Embedding vector dimension does not match the configured dimension"
                )
            embedded_chunks.append(EmbeddedChunk(chunk=chunk, vector=vector))

    return embedded_chunks

