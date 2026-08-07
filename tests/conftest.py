import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    # Docker 같은 로컬 서비스가 필요한 테스트는 명시적으로 요청할 때만 실행한다.
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="run tests that require local services",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    if config.getoption("--run-integration"):
        return

    # 기본 pytest가 Qdrant 실행 여부에 따라 실패하지 않도록 integration marker를 건너뛴다.
    skip_integration = pytest.mark.skip(reason="requires --run-integration")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)
