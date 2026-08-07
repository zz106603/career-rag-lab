import json
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).parents[1]
QUESTIONS_PATH = PROJECT_ROOT / "data" / "evaluation" / "questions.json"
DOCUMENTS_DIR = PROJECT_ROOT / "data" / "documents"
EXPECTED_CATEGORIES = {
    "semantic",
    "exact_keyword",
    "conditional",
    "multi_document",
    "unanswerable",
}
REQUIRED_FIELDS = {
    "id",
    "category",
    "question",
    "expected_sources",
    "answerable",
}


def load_questions() -> list[dict]:
    return json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))


def test_evaluation_set_has_unique_ids_and_required_fields() -> None:
    questions = load_questions()

    assert len(questions) >= 15
    assert len({item["id"] for item in questions}) == len(questions)
    for item in questions:
        assert set(item) == REQUIRED_FIELDS
        assert item["question"].strip()
        assert isinstance(item["answerable"], bool)


def test_evaluation_set_covers_all_question_categories() -> None:
    category_counts = Counter(item["category"] for item in load_questions())

    assert set(category_counts) == EXPECTED_CATEGORIES
    assert all(category_counts[category] >= 3 for category in EXPECTED_CATEGORIES)


def test_expected_sources_reference_existing_documents() -> None:
    document_names = {path.name for path in DOCUMENTS_DIR.glob("*.md")}

    for item in load_questions():
        assert set(item["expected_sources"]) <= document_names


def test_answerability_matches_expected_sources() -> None:
    for item in load_questions():
        if item["answerable"]:
            assert item["expected_sources"]
        else:
            assert item["category"] == "unanswerable"
            assert item["expected_sources"] == []
