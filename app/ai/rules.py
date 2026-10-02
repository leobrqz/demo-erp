# Leonardo Briquezi
# github: https://github.com/leobrqz
# linkedin: https://www.linkedin.com/in/leonardobri
import re
import unicodedata

from app.schemas.agent import QuestionIntent

_THRESHOLD = re.compile(
    r"\b(?:abaixo\s+de|menor\s+que|menor\s+de|menos\s+de|abaixo|menor|menos)\s*(\d+)\b"
)
_SEARCH = re.compile(
    r"\b(?:buscar|busque|encontre|procure|pesquise)\s+(?:o\s+produto\s+|um\s+produto\s+|por\s+|produto\s+)?(.+)$",
    re.IGNORECASE,
)
_NAMED_PRODUCT = re.compile(r"\b(?:produto|estoque\s+(?:do|da)\s+produto)\s+(.+)$", re.I)


def _normalized(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(character for character in decomposed if not unicodedata.combining(character))


def interpret_question(question: str) -> QuestionIntent:
    normalized = _normalized(question).strip(" ?.!\t\n")
    has_stock_term = "estoque" in normalized or "unidade" in normalized

    if has_stock_term and any(
        phrase in normalized
        for phrase in ("abaixo", "menor", "menos", "baixo", "sem estoque")
    ):
        if "sem estoque" in normalized:
            threshold = 0
        else:
            match = _THRESHOLD.search(normalized)
            threshold = int(match.group(1)) if match else 10
        return QuestionIntent(action="low_stock", threshold=threshold)

    generic_list_phrases = (
        "liste os produtos",
        "listar produtos",
        "quais sao os produtos",
        "mostre os produtos",
        "lista de produtos",
    )
    if any(phrase in normalized for phrase in generic_list_phrases):
        return QuestionIntent(action="list_products")

    match = _SEARCH.search(question.strip()) or _NAMED_PRODUCT.search(question.strip())
    if match:
        query = match.group(1).strip(" \t\n?!.:,;").strip()
        query = re.sub(r"^(?:o|a|um|uma|de|do|da)\s+", "", query, flags=re.IGNORECASE)
        if query and _normalized(query) not in {"com estoque baixo", "com estoque"}:
            return QuestionIntent(action="search_products", query=query[:160])

    return QuestionIntent(action="unsupported")
