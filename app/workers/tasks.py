# Leonardo Briquezi
# github: https://github.com/leobrqz
# linkedin: https://www.linkedin.com/in/leonardobri
from uuid import UUID

from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import LowStockAlert, Product
from app.models.entities import utc_now


def refresh_low_stock_alert(product_id: str, threshold: int | None = None) -> str:
    effective_threshold = (
        settings.low_stock_threshold if threshold is None else max(0, threshold)
    )
    with SessionLocal() as db:
        product = db.get(Product, UUID(product_id))
        if product is None:
            return "product_not_found"

        alert = db.scalar(
            select(LowStockAlert).where(LowStockAlert.product_id == product.id)
        )
        if product.quantity_in_stock <= effective_threshold:
            if alert is None:
                alert = LowStockAlert(
                    product_id=product.id,
                    threshold=effective_threshold,
                    observed_quantity=product.quantity_in_stock,
                    status="open",
                )
                db.add(alert)
            else:
                alert.threshold = effective_threshold
                alert.observed_quantity = product.quantity_in_stock
                alert.status = "open"
                alert.updated_at = utc_now()
            result = "alert_open"
        else:
            if alert is not None and alert.status == "open":
                alert.status = "resolved"
                alert.updated_at = utc_now()
            result = "alert_resolved"
        db.commit()
        return result

