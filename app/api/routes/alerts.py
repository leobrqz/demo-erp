# Leonardo Briquezi
# github: https://github.com/leobrqz
# linkedin: https://www.linkedin.com/in/leonardobri
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models import LowStockAlert, User
from app.schemas.products import LowStockAlertRead

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("/low-stock", response_model=list[LowStockAlertRead])
def list_open_low_stock_alerts(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[LowStockAlert]:
    statement = (
        select(LowStockAlert)
        .where(LowStockAlert.status == "open")
        .order_by(LowStockAlert.created_at.desc())
    )
    return list(db.scalars(statement))

