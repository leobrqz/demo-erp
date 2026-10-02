# Leonardo Briquezi
# github: https://github.com/leobrqz
# linkedin: https://www.linkedin.com/in/leonardobri
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import LowStockAlert, Product


class ProductRepository:
    def get(self, db: Session, product_id: UUID) -> Product | None:
        return db.get(Product, product_id)

    def get_by_name(self, db: Session, name: str) -> Product | None:
        return db.scalar(select(Product).where(func.lower(Product.name) == name.lower()))

    def list(
        self,
        db: Session,
        *,
        name: str | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
        low_stock: int | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Product], int]:
        filters = []
        if name:
            filters.append(Product.name.ilike(f"%{name.strip()}%"))
        if min_price is not None:
            filters.append(Product.price >= min_price)
        if max_price is not None:
            filters.append(Product.price <= max_price)
        if low_stock is not None:
            filters.append(Product.quantity_in_stock <= low_stock)

        total = db.scalar(select(func.count()).select_from(Product).where(*filters)) or 0
        statement = (
            select(Product)
            .where(*filters)
            .order_by(Product.created_at.desc(), Product.id)
            .offset(offset)
            .limit(limit)
        )
        return list(db.scalars(statement)), total

    def list_open_alerts(self, db: Session) -> list[LowStockAlert]:
        statement = (
            select(LowStockAlert)
            .where(LowStockAlert.status == "open")
            .order_by(LowStockAlert.created_at.desc())
        )
        return list(db.scalars(statement))


product_repository = ProductRepository()
