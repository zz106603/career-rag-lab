from unittest.mock import Mock

import pytest

from app.qdrant import check_qdrant_connection, create_qdrant_client


def test_qdrant_connection_checks_collections() -> None:
    client = Mock()

    assert check_qdrant_connection(client) is True
    client.get_collections.assert_called_once_with()


@pytest.mark.integration
def test_local_qdrant_is_available() -> None:
    client = create_qdrant_client()

    assert check_qdrant_connection(client) is True

