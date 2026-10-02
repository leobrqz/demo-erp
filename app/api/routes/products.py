# Leonardo Briquezi
# github: https://github.com/leobrqz
# linkedin: https://www.linkedin.com/in/leonardobri
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from redis import Redis
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_admin
from app.db.redis_client import get_redis_client
from app.db.session import get_db
from app.models import User
from app.schemas.products import ProductCreate, ProductPage, ProductRead, ProductUpdate
from app.services.cache import product_page
from app.services.products import (
    ProductAlreadyExistsError,
    ProductNotFoundError,
    create_product,
    delete_product,
    get_product,
    update_product,
)

router = APIRouter(prefix="/products", tags=["products"])


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis_client),
    _: User = Depends(require_admin),
) -> ProductRead:
    try:
        return create_product(db, redis, payload)
    except ProductAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("", response_model=ProductPage)
def list_products(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    name: str | None = Query(default=None, max_length=160),
    min_price: Decimal | None = Query(default=None, ge=0),
    max_price: Decimal | None = Query(default=None, ge=0),
    low_stock: int | None = Query(default=None, ge=0, le=2_147_483_647),
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis_client),
    _: User = Depends(get_current_user),
) -> dict:
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="min_price não pode ser maior que max_price.",
        )
    return product_page(
        db,
        redis,
        page=page,
        page_size=page_size,
        name=name,
        min_price=min_price,
        max_price=max_price,
        low_stock=low_stock,
    )


@router.get("/{product_id}", response_model=ProductRead)
def read_product(
    product_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ProductRead:
    try:
        return get_product(db, product_id)
    except ProductNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado.") from exc


@router.patch("/{product_id}", response_model=ProductRead)
def update(
    product_id: UUID,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis_client),
    _: User = Depends(require_admin),
) -> ProductRead:
    try:
        return update_product(db, redis, product_id, payload)
    except ProductNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado.") from exc
    except ProductAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove(
    product_id: UUID,
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis_client),
    _: User = Depends(require_admin),
) -> Response:
    try:
        delete_product(db, redis, product_id)
    except ProductNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado.") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
