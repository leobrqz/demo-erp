# Leonardo Briquezi
# github: https://github.com/leobrqz
# linkedin: https://www.linkedin.com/in/leonardobri
import logging
from decimal import Decimal
from uuid import UUID

from redis import Redis
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Product
from app.repositories.products import product_repository
from app.schemas.products import ProductCreate, ProductUpdate
from app.services.cache import invalidate_product_pages
from app.services.job_queue import enqueue_low_stock_refresh

logger = logging.getLogger(__name__)


class ProductNotFoundError(LookupError):
    pass


class ProductAlreadyExistsError(ValueError):
    pass


def create_product(db: Session, redis: Redis, payload: ProductCreate) -> Product:
    if product_repository.get_by_name(db, payload.name):
        raise ProductAlreadyExistsError("Já existe um produto com esse nome.")
    product = Product(
        name=payload.name,
        price=payload.price,
        quantity_in_stock=payload.quantity_in_stock,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    invalidate_product_pages(redis)
    enqueue_low_stock_refresh(product.id, settings.low_stock_threshold)
    return product


def get_product(db: Session, product_id: UUID) -> Product:
    product = product_repository.get(db, product_id)
    if product is None:
        raise ProductNotFoundError
    return product


def update_product(
    db: Session,
    redis: Redis,
    product_id: UUID,
    payload: ProductUpdate,
) -> Product:
    product = get_product(db, product_id)
    changes = payload.model_dump(exclude_unset=True)
    if "name" in changes:
        existing = product_repository.get_by_name(db, changes["name"])
        if existing and existing.id != product.id:
            raise ProductAlreadyExistsError("Já existe um produto com esse nome.")
    stock_may_have_changed = "quantity_in_stock" in changes
    for field_name, value in changes.items():
        setattr(product, field_name, value)
    db.commit()
    db.refresh(product)
    invalidate_product_pages(redis)
    if stock_may_have_changed:
        enqueue_low_stock_refresh(product.id, settings.low_stock_threshold)
    return product


def delete_product(db: Session, redis: Redis, product_id: UUID) -> None:
    product = get_product(db, product_id)
    db.delete(product)
    db.commit()
    invalidate_product_pages(redis)


def query_products_for_agent(
    db: Session,
    *,
    action: str,
    threshold: int = 10,
    query: str | None = None,
) -> list[dict[str, object]]:
    if action == "low_stock":
        products, _ = product_repository.list(db, low_stock=threshold, limit=100)
    elif action == "search_products":
        products, _ = product_repository.list(db, name=query, limit=100)
    else:
        products, _ = product_repository.list(db, limit=100)
    return [
        {
            "id": str(product.id),
            "name": product.name,
            "price": str(Decimal(product.price)),
            "quantity_in_stock": product.quantity_in_stock,
            "created_at": product.created_at.isoformat(),
            "updated_at": product.updated_at.isoformat(),
        }
        for product in products
    ]
