from pathlib import Path


REVIEW_PATH = Path(__file__).parents[1] / "docs" / "FINAL_REVIEW.md"


def test_final_review_contains_all_required_sections() -> None:
    content = REVIEW_PATH.read_text(encoding="utf-8")
    required_sections = (
        "## 1. 직접 구현한 RAG 데이터 흐름",
        "## 2. LangChain 적용 전후 비교",
        "## 3. 최종 Chunk 전략",
        "## 4. 최종 검색 전략",
        "## 5. 평가 결과",
        "## 6. 근거 없는 답변 방지 방식",
        "## 7. 운영 시 고려할 항목",
        "## 8. career-fit-ai에 이식할 구성요소",
        "## 9. Java에서 다시 설계해야 할 부분",
        "## 10. 현재 구현의 한계",
    )

    assert all(section in content for section in required_sections)


def test_final_review_distinguishes_recommendation_from_current_answer_path() -> None:
    content = REVIEW_PATH.read_text(encoding="utf-8")

    assert "`POST /search/hybrid`는 구현" in content
    assert "`POST /answer`의 기본 Retriever는 아직" in content
    assert "Hybrid가 아직 연결되지 않았다" in content
    assert "Hit@3 | 1.000 | 1.000" in content
    assert "Mean source recall | 0.917 | 0.917" in content
