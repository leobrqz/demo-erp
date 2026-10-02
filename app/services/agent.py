# Leonardo Briquezi
# github: https://github.com/leobrqz
# linkedin: https://www.linkedin.com/in/leonardobri
import asyncio
import logging
import re
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.orm import Session

from app.ai.rules import interpret_question
from app.core.config import settings
from app.schemas.agent import AgentResponse
from app.services.products import query_products_for_agent

logger = logging.getLogger(__name__)


def _rule_based_answer(db: Session, question: str, provider: str) -> AgentResponse:
    intent = interpret_question(question)
    data: list[dict[str, Any]] = []
    if intent.action != "unsupported":
        data = query_products_for_agent(
            db,
            action=intent.action,
            threshold=intent.threshold,
            query=intent.query,
        )

    if intent.action == "low_stock":
        answer = f"Encontrei {len(data)} produto(s) com estoque de até {intent.threshold} unidade(s)."
    elif intent.action == "list_products":
        answer = f"Encontrei {len(data)} produto(s)."
    elif intent.action == "search_products":
        answer = f"Encontrei {len(data)} produto(s) correspondentes a {intent.query!r}."
    else:
        answer = (
            "Ainda entendo consultas de estoque baixo, listagem e busca por nome. "
            "Tente reformular a pergunta."
        )

    return AgentResponse(
        question=question,
        provider=provider,
        action=intent.action,
        answer=answer,
        data=data,
        fallback_used=provider.endswith("fallback"),
    )


def _model_unavailable_answer(question: str) -> AgentResponse:
    return AgentResponse(
        question=question,
        provider="local_model_unavailable",
        action="temporarily_unavailable",
        answer="Não consegui consultar o assistente agora. Tente novamente em instantes.",
        data=[],
        fallback_used=True,
    )


def _model_clarification(question: str) -> AgentResponse:
    return AgentResponse(
        question=question,
        provider=f"local:{settings.llm_model}",
        action="clarification",
        answer="Não entendi o que você quer consultar. Pode explicar de outro jeito?",
        data=[],
    )


async def answer_erp_question(db: Session, question: str) -> AgentResponse:
    if settings.ai_provider == "local":
        try:
            from app.ai.local_agent import ask_local_model

            async with asyncio.timeout(settings.llm_timeout_seconds):
                response = await ask_local_model(question)
            if response.tool_calls:
                if not response.answer:
                    response.answer = "Consultei os dados, mas não consegui resumir o resultado. Tente novamente."
                return response
            if response.answer:
                return response
            logger.info("Modelo local não retornou uma resposta.")
            return _model_clarification(question)
        except Exception:
            logger.exception("Falha no agente local.")
            return _model_unavailable_answer(question)
    return _rule_based_answer(db, question, "rules")


async def stream_erp_question(db: Session, question: str) -> AsyncIterator[dict[str, Any]]:
    if settings.ai_provider == "local":
        emitted_paragraph = False
        model_failed = False
        response: AgentResponse | None = None
        try:
            from app.ai.local_agent import stream_local_model

            async with asyncio.timeout(settings.llm_timeout_seconds):
                async for event in stream_local_model(question):
                    if event["event"] == "paragraph":
                        emitted_paragraph = True
                        yield event
                    elif event["event"] == "done":
                        response = AgentResponse.model_validate(event["data"])
                    elif event["event"] == "no_tool":
                        break
            if response is not None:
                yield {"event": "done", "data": response.model_dump(mode="json")}
                return
        except Exception:
            logger.exception("Falha no streaming local.")
            model_failed = True

        if emitted_paragraph:
            yield {"event": "replace", "data": {}}
        response = (
            _model_unavailable_answer(question)
            if model_failed
            else _model_clarification(question)
        )
        yield {"event": "paragraph", "data": {"text": response.answer}}
        yield {"event": "done", "data": response.model_dump(mode="json")}
        return

    response = _rule_based_answer(db, question, "rules")
    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", response.answer)
        if paragraph.strip()
    ]
    for paragraph in paragraphs:
        yield {"event": "paragraph", "data": {"text": paragraph}}
    yield {"event": "done", "data": response.model_dump(mode="json")}
