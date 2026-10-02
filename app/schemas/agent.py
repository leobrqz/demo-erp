# Leonardo Briquezi
# github: https://github.com/leobrqz
# linkedin: https://www.linkedin.com/in/leonardobri
from typing import Any, Literal

from pydantic import BaseModel, Field


class AgentQuestion(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class AgentResponse(BaseModel):
    question: str
    provider: str
    action: str
    answer: str
    data: Any
    tool_calls: list[str] = Field(default_factory=list)
    fallback_used: bool = False


class QuestionIntent(BaseModel):
    action: Literal["low_stock", "list_products", "search_products", "unsupported"]
    threshold: int = Field(default=10, ge=0, le=100_000)
    query: str | None = Field(default=None, max_length=160)
