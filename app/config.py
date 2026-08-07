import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """애플리케이션 전역에서 사용할 외부 서비스 연결 설정."""

    qdrant_url: str


def get_settings() -> Settings:
    # 로컬 개발자는 별도 설정 없이 기본 주소를 사용하고,
    # 배포·테스트 환경에서는 환경변수만 바꿔 같은 코드를 재사용한다.
    return Settings(qdrant_url=os.getenv("QDRANT_URL", "http://localhost:6333"))
