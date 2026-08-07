import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    # Docker 같은 로컬 서비스가 필요한 테스트는 명시적으로 요청할 때만 실행한다.
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="run tests that require local services",
    )
    parser.addoption(
        "--run-live-api",
        action="store_true",
        default=False,
        help="run tests that call paid external APIs",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    run_integration = config.getoption("--run-integration")
    run_live_api = config.getoption("--run-live-api")
    skip_integration = pytest.mark.skip(reason="requires --run-integration")
    skip_live_api = pytest.mark.skip(reason="requires --run-live-api")
    for item in items:
        # Qdrant와 유료 OpenAI API 테스트를 서로 독립적으로 선택한다.
        if "integration" in item.keywords and not run_integration:
            item.add_marker(skip_integration)
        if "live_api" in item.keywords and not run_live_api:
            item.add_marker(skip_live_api)
