# Leonardo Briquezi
# github: https://github.com/leobrqz
# linkedin: https://www.linkedin.com/in/leonardobri
import logging
from uuid import UUID

from rq import Queue

from app.db.redis_client import get_queue_redis_client

logger = logging.getLogger(__name__)


def enqueue_low_stock_refresh(
    product_id: UUID,
    threshold: int,
) -> bool:
    try:
        Queue("default", connection=get_queue_redis_client()).enqueue(
            "app.workers.tasks.refresh_low_stock_alert",
            str(product_id),
            threshold,
            job_timeout=30,
            result_ttl=300,
        )
        return True
    except Exception:
        # The product transaction has already committed; keep the API mutation successful
        # and make the lost background work visible in operational logs.
        logger.exception("Não foi possível enfileirar a verificação de estoque do produto %s", product_id)
        return False
