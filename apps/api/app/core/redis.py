"""
Redis connection pool.
D-04: OTP store, rate limit, dispatch queue, WebSocket pub/sub.
"""
from redis.asyncio import Redis, from_url

from app.core.config import get_settings

_redis: Redis | None = None


async def get_redis() -> Redis:
    global _redis
    if _redis is None:
        settings = get_settings()
        _redis = from_url(settings.redis_url, decode_responses=True, protocol=2)
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
