# Leonardo Briquezi
# github: https://github.com/leobrqz
# linkedin: https://www.linkedin.com/in/leonardobri
from collections.abc import Iterator
from typing import Any

from app.schemas.agent import AgentResponse


def _tool_results(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _tool_results(item)


def _product_word(count: int) -> str:
    return "produto" if count == 1 else "produtos"


def ground_tool_response(response: AgentResponse) -> AgentResponse:
    """Use the MCP result as the source for numeric product summaries."""
    calls = set(response.tool_calls)
    if not calls:
        return response

    for result in _tool_results(response.data):
        items = result.get("items")
        if not isinstance(items, list):
            continue

        count = result.get("count")
        if "list_products" in calls and isinstance(count, int) and not isinstance(count, bool):
            response.answer = (
                f"Há {count} {_product_word(count)} cadastrados."
                if count != 1
                else "Há 1 produto cadastrado."
            )
            return response

        if "find_low_stock_products" in calls:
            threshold = result.get("threshold")
            if isinstance(threshold, int) and not isinstance(threshold, bool):
                count = len(items)
                unit = "unidade" if threshold == 1 else "unidades"
                response.answer = (
                    f"Encontrei {count} {_product_word(count)} com estoque de até "
                    f"{threshold} {unit}."
                )
                return response

        if "search_products" in calls and isinstance(result.get("query"), str):
            query = result["query"]
            count = len(items)
            noun = _product_word(count)
            match_word = "correspondente" if count == 1 else "correspondentes"
            response.answer = f"Encontrei {count} {noun} {match_word} para {query!r}."
            return response

    return response
