from qdrant_client import QdrantClient

from app.config import get_settings


def create_qdrant_client() -> QdrantClient:
    """환경설정에 지정된 Qdrant에 연결할 클라이언트를 만든다."""
    settings = get_settings()
    return QdrantClient(url=settings.qdrant_url)


def check_qdrant_connection(client: QdrantClient) -> bool:
    """실제 API 요청을 보내 Qdrant가 응답 가능한지 확인한다.

    단순히 클라이언트 객체가 만들어진 것만으로는 서버 연결을 확인할 수 없다.
    Collection 목록 조회가 실패하면 예외를 그대로 전달해 장애 원인을 숨기지 않는다.
    """
    client.get_collections()
    return True
