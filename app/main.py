# Leonardo Briquezi
# github: https://github.com/leobrqz
# linkedin: https://www.linkedin.com/in/leonardobri
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.redis_client import get_queue_redis_client, get_redis_client
from app.db.session import SessionLocal

configure_logging()


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    get_redis_client().close()
    get_queue_redis_client().close()


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="API de produtos, estoque, tarefas em background e consulta assistida do ERP.",
    lifespan=lifespan,
)
app.include_router(api_router)


@app.get("/health/live", tags=["health"])
def liveness() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/ready", tags=["health"])
def readiness() -> dict[str, str]:
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        get_redis_client().ping()
    except (SQLAlchemyError, RedisError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PostgreSQL ou Redis ainda não está pronto.",
        ) from exc
    return {"status": "ready"}
