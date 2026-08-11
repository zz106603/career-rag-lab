from collections.abc import Mapping
from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import (
    Runnable,
    RunnableBranch,
    RunnableLambda,
    RunnablePassthrough,
)
from langchain_openai import ChatOpenAI

from app.answers import (
    ANSWER_INSTRUCTIONS,
    REFUSAL_ANSWER,
    AnswerGenerationError,
    AnswerResult,
    InvalidAnswerInputError,
    RetrievalPipelineError,
)
from app.config import Settings, get_settings
from app.embeddings import MissingOpenAIAPIKeyError
from app.langchain_prompts import ANSWER_PROMPT_TEMPLATE, format_evidence_context
from app.langchain_retrieval import (
    LangChainRetrievalService,
    SearchFilters,
    create_langchain_retrieval_service,
)
from app.search import SearchResult


class LangChainRagService:
    """검색·근거 판정·Prompt·생성을 LCEL 조건 Chain으로 연결한다."""

    def __init__(
        self,
        retrieval_service: LangChainRetrievalService,
        generation_model: Runnable[Any, Any],
        settings: Settings,
    ) -> None:
        self.retrieval_service = retrieval_service
        self.settings = settings

        prompt_chain = (
            RunnableLambda(_to_prompt_variables)
            | ANSWER_PROMPT_TEMPLATE
            | generation_model
            | StrOutputParser()
        )
        generation_branch = (
            RunnablePassthrough.assign(answer=prompt_chain)
            | RunnableLambda(_to_answered_result)
        )
        self.chain = (
            RunnablePassthrough.assign(retrieval=RunnableLambda(self._retrieve))
            | RunnableLambda(_select_evidence)
            | RunnableBranch(
                (
                    lambda state: not state["evidence"],
                    RunnableLambda(_to_refusal_result),
                ),
                generation_branch,
            )
        )

    def answer(
        self,
        query: str,
        *,
        top_k: int | None = None,
        score_threshold: float | None = None,
        filters: SearchFilters | None = None,
    ) -> AnswerResult:
        active_top_k = self.settings.answer_top_k if top_k is None else top_k
        active_threshold = (
            self.settings.answer_score_threshold
            if score_threshold is None
            else score_threshold
        )
        _validate_options(active_top_k, active_threshold)
        try:
            return self.chain.invoke(
                {
                    "query": query,
                    "top_k": active_top_k,
                    "score_threshold": active_threshold,
                    "filters": filters,
                }
            )
        except RetrievalPipelineError:
            raise
        except AnswerGenerationError:
            raise
        except Exception as error:
            raise AnswerGenerationError("Answer generation failed") from error

    def _retrieve(self, state: Mapping[str, Any]) -> list[SearchResult]:
        try:
            return self.retrieval_service.search(
                str(state["query"]),
                top_k=int(state["top_k"]),
                filters=state.get("filters"),
            )
        except Exception as error:
            raise RetrievalPipelineError("Retrieval failed") from error


def create_langchain_rag_service(
    *,
    settings: Settings | None = None,
    retrieval_service: LangChainRetrievalService | None = None,
    generation_model: Runnable[Any, Any] | None = None,
) -> LangChainRagService:
    active_settings = settings or get_settings()
    if generation_model is None and not active_settings.openai_api_key:
        raise MissingOpenAIAPIKeyError("OPENAI_API_KEY is not configured")
    active_model = generation_model or ChatOpenAI(
        api_key=active_settings.openai_api_key,
        model=active_settings.chat_model,
        reasoning={"effort": "minimal"},
        max_completion_tokens=active_settings.answer_max_output_tokens,
        use_responses_api=True,
    ).bind(instructions=ANSWER_INSTRUCTIONS)
    return LangChainRagService(
        retrieval_service=retrieval_service
        or create_langchain_retrieval_service(settings=active_settings),
        generation_model=active_model,
        settings=active_settings,
    )


def _select_evidence(state: dict[str, Any]) -> dict[str, Any]:
    retrieval = state["retrieval"]
    threshold = float(state["score_threshold"])
    return {
        **state,
        "evidence": [item for item in retrieval if item.score >= threshold],
    }


def _to_prompt_variables(state: dict[str, Any]) -> dict[str, str]:
    return {
        "query": str(state["query"]),
        "context": format_evidence_context(state["evidence"]),
    }


def _to_refusal_result(state: dict[str, Any]) -> AnswerResult:
    return AnswerResult(
        status="insufficient_evidence",
        answer=REFUSAL_ANSWER,
        sources=[],
        retrieval=state["retrieval"],
        generated=False,
    )


def _to_answered_result(state: dict[str, Any]) -> AnswerResult:
    answer = str(state["answer"]).strip()
    if not answer:
        raise AnswerGenerationError("Answer generation returned empty text")
    evidence = state["evidence"]
    return AnswerResult(
        status="answered",
        answer=answer,
        sources=list(dict.fromkeys(item.source for item in evidence)),
        retrieval=state["retrieval"],
        generated=True,
    )


def _validate_options(top_k: int, score_threshold: float) -> None:
    if top_k <= 0:
        raise InvalidAnswerInputError("top_k must be greater than 0")
    if not -1.0 <= score_threshold <= 1.0:
        raise InvalidAnswerInputError("score_threshold must be between -1 and 1")
