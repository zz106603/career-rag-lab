from langchain_core.prompts import PromptTemplate

from app.search import SearchResult


ANSWER_PROMPT_TEMPLATE = PromptTemplate.from_template(
    "[질문]\n{query}\n\n[검색 근거]\n{context}"
)


def build_langchain_answer_prompt(
    query: str, evidence: list[SearchResult]
) -> str:
    """질문과 검색 Context를 LangChain 변수로 분리해 Prompt를 구성한다."""
    context = _format_context(evidence)
    return ANSWER_PROMPT_TEMPLATE.format(query=query, context=context)


def _format_context(evidence: list[SearchResult]) -> str:
    """검색에 실제로 포함된 원문·출처·section만 모델 Context로 전달한다."""
    parts = []
    for index, item in enumerate(evidence, start=1):
        section = item.metadata.get("section", "")
        parts.append(
            f"[검색 근거 {index}]\n"
            f"출처: {item.source}\n"
            f"섹션: {section}\n"
            f"내용:\n{item.content}"
        )
    return "\n\n".join(parts)
