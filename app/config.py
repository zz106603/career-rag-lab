import os
from dataclasses import dataclass, field

from dotenv import load_dotenv


# 로컬 `.env`를 프로세스 환경변수로 읽는다. 이미 설정된 환경변수는 덮어쓰지 않는다.
load_dotenv()


@dataclass(frozen=True)
class Settings:
    """애플리케이션 전역에서 사용할 외부 서비스 연결 설정."""

    qdrant_url: str
    qdrant_collection: str
    openai_api_key: str | None = field(repr=False)
    embedding_model: str
    embedding_dimensions: int
    embedding_batch_size: int


def get_settings() -> Settings:
    # 로컬 개발자는 별도 설정 없이 기본 주소를 사용하고,
    # 배포·테스트 환경에서는 환경변수만 바꿔 같은 코드를 재사용한다.
    return Settings(
        qdrant_url=os.getenv("QDRANT_URL", "http://localhost:6333"),
        qdrant_collection=os.getenv("QDRANT_COLLECTION", "career_documents"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        embedding_model=os.getenv(
            "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"
        ),
        embedding_dimensions=_positive_int_env(
            "OPENAI_EMBEDDING_DIMENSIONS", default=1536
        ),
        embedding_batch_size=_positive_int_env(
            "OPENAI_EMBEDDING_BATCH_SIZE", default=100
        ),
    )


def _positive_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        value = int(raw_value)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer") from error
    if value <= 0:
        raise ValueError(f"{name} must be greater than 0")
    return value
