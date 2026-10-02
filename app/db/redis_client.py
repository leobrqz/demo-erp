# Leonardo Briquezi
# github: https://github.com/leobrqz
# linkedin: https://www.linkedin.com/in/leonardobri
from functools import lru_cache

from redis import Redis

from app.core.config import settings


@lru_cache
def get_redis_client() -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True)


@lru_cache
def get_queue_redis_client() -> Redis:
    # RQ stores serialized job data as bytes and must not use decode_responses.
    return Redis.from_url(settings.redis_url)
