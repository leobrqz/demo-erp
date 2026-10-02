# Leonardo Briquezi
# github: https://github.com/leobrqz
# linkedin: https://www.linkedin.com/in/leonardobri
import hashlib
import json
import logging
from decimal import Decimal
from typing import Any

from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy.orm import Session

from app.repositories.products import product_repository
from app.schemas.products import ProductRead

logger = logging.getLogger(__name__)
_PRODUCTS_CACHE_VERSION = "cache:products:version"
_CACHE_TTL_SECONDS = 300


def product_page(
    db: Session,
    redis: Redis,
    *,
    page: int,
    page_size: int,
    name: str | None,
    min_price: Decimal | None,
    max_price: Decimal | None,
    low_stock: int | None,
) -> dict[str, Any]:
    filters = {
        "page": page,
        "page_size": page_size,
        "name": name.strip().casefold() if name else None,
        "min_price": str(min_price) if min_price is not None else None,
        "max_price": str(max_price) if max_price is not None else None,
        "low_stock": low_stock,
    }
    encoded_filters = json.dumps(filters, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(encoded_filters.encode("utf-8")).hexdigest()[:20]
    version = 0
    cache_available = True

    try:
        version = int(redis.get(_PRODUCTS_CACHE_VERSION) or 0)
        cached = redis.get(f"cache:products:v{version}:{digest}")
        if cached:
            return json.loads(cached)
    except (RedisError, ValueError, TypeError):
        cache_available = False
        logger.warning("Redis indisponível ao ler cache de produtos; consultando PostgreSQL.")

    products, total = product_repository.list(
        db,
        name=name,
        min_price=min_price,
        max_price=max_price,
        low_stock=low_stock,
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    result = {
        "items": [ProductRead.model_validate(item).model_dump(mode="json") for item in products],
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": (total + page_size - 1) // page_size,
    }

    if cache_available:
        try:
            redis.setex(
                f"cache:products:v{version}:{digest}",
                _CACHE_TTL_SECONDS,
                json.dumps(result, separators=(",", ":")),
            )
        except RedisError:
            logger.warning("Redis indisponível ao gravar cache de produtos.")
    return result


def invalidate_product_pages(redis: Redis) -> None:
    try:
        redis.incr(_PRODUCTS_CACHE_VERSION)
    except RedisError:
        logger.warning("Redis indisponível ao invalidar cache de produtos.")
