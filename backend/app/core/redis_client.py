"""Redis 客户端：同步（Celery/锁）与异步（FastAPI 会话/限流）。"""
from typing import Optional

import redis
import redis.asyncio as aioredis

from app.core.config import settings

_sync: Optional[redis.Redis] = None
_async: Optional[aioredis.Redis] = None


def get_redis() -> redis.Redis:
    global _sync
    if _sync is None:
        _sync = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    return _sync


def get_async_redis() -> aioredis.Redis:
    global _async
    if _async is None:
        _async = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _async


async def close_redis() -> None:
    global _async
    if _async is not None:
        await _async.aclose()
        _async = None