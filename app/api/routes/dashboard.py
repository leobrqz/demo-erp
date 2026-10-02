# Leonardo Briquezi
# github: https://github.com/leobrqz
# linkedin: https://www.linkedin.com/in/leonardobri
from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_current_user
from app.models import User
from app.services.erp_aggregate import get_erp_snapshot

router = APIRouter(prefix="/erp", tags=["erp"])


@router.get("/snapshot")
async def erp_snapshot(
    timeout_ms: int = Query(default=250, ge=1, le=5_000),
    _: User = Depends(get_current_user),
) -> dict:
    """Aggregate inventory, finance and customer mocks concurrently."""
    return await get_erp_snapshot(timeout_ms=timeout_ms, retries=1)

