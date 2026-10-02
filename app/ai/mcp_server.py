# Leonardo Briquezi
# github: https://github.com/leobrqz
# linkedin: https://www.linkedin.com/in/leonardobri
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from app.db.session import SessionLocal
from app.services.products import query_products_for_agent

mcp = FastMCP("erp-demo-readonly")


@mcp.tool()
def find_low_stock_products(
    threshold: Annotated[int, Field(ge=0, le=100_000)] = 10,
) -> dict[str, Any]:
    """Consulta o estoque atual e retorna itens no limite ou abaixo dele.

    Use quando a pessoa quer identificar produtos com pouca disponibilidade,
    quase esgotados ou que precisam de reposição. Interprete o limite pelo
    contexto; se não houver um valor definido, use 10. Somente leitura.
    """
    with SessionLocal() as db:
        items = query_products_for_agent(db, action="low_stock", threshold=threshold)
    return {"threshold": threshold, "items": items}


@mcp.tool()
def search_products(
    query: Annotated[str, Field(min_length=1, max_length=160)],
) -> dict[str, Any]:
    """Localiza itens do catálogo por parte do nome, sem diferenciar maiúsculas.

    Use quando o pedido se refere a um ou mais produtos identificáveis pelo
    nome, inclusive para consultar preço ou estoque atuais. Envie o nome
    relevante do produto, não a pergunta inteira. Não altera dados.
    """
    with SessionLocal() as db:
        items = query_products_for_agent(db, action="search_products", query=query)
    return {"query": query, "items": items}


@mcp.tool()
def list_products(
    limit: Annotated[int, Field(ge=1, le=100)] = 20,
) -> dict[str, Any]:
    """Consulta o catálogo atual e retorna seus itens e quantidade.

    Use para pedidos sobre o catálogo como um todo, incluindo seu conteúdo ou
    o total de produtos cadastrados. O campo count sempre informa o total do
    catálogo, mesmo quando items é limitado por limit. Somente leitura.
    """
    with SessionLocal() as db:
        all_items = query_products_for_agent(db, action="list_products")
    return {"items": all_items[:limit], "count": len(all_items)}
