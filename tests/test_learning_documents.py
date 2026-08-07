import re
from pathlib import Path


DOCUMENTS_DIR = Path(__file__).parents[1] / "data" / "documents"
SYNTHETIC_DATA_NOTICE = "이 문서는 RAG 학습을 위해 작성한 합성 데이터"


def get_learning_documents() -> list[Path]:
    return sorted(DOCUMENTS_DIR.glob("*.md"))


def test_learning_document_count_is_in_expected_range() -> None:
    assert 5 <= len(get_learning_documents()) <= 10


def test_learning_documents_are_identified_as_synthetic() -> None:
    for document in get_learning_documents():
        content = document.read_text(encoding="utf-8")

        assert content.startswith("# ")
        assert SYNTHETIC_DATA_NOTICE in content


def test_learning_documents_do_not_contain_contact_information() -> None:
    email_pattern = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
    korean_phone_pattern = re.compile(r"01[016789][ -]?\d{3,4}[ -]?\d{4}")

    for document in get_learning_documents():
        content = document.read_text(encoding="utf-8")

        assert email_pattern.search(content) is None
        assert korean_phone_pattern.search(content) is None


def test_experience_boundaries_include_explicit_non_experience() -> None:
    content = (DOCUMENTS_DIR / "experience-boundaries.md").read_text(
        encoding="utf-8"
    )

    assert "사용 경험이 없는 기술" in content
    assert "경험은 없다" in content
