"""
Platform configuration service – Fix 24/7.
FR-ADM-04: Configurable platform settings with Redis cache (TTL 300s).
"""
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.models import PlatformConfig, _uuid_default

_CACHE_TTL = 300  # seconds
_CACHE_PREFIX = "platform_config:"


async def get_config(db: AsyncSession, key: str, default=None) -> str:
    """
    FR-ADM-04: Read platform config value.
    Checks Redis cache first (TTL 300s), falls back to DB.
    Gracefully degrades if Redis is unavailable.
    """
    cache_key = f"{_CACHE_PREFIX}{key}"

    # Try cache
    try:
        redis = await get_redis()
        cached = await redis.get(cache_key)
        if cached is not None:
            return cached
    except Exception:
        pass

    # DB lookup
    try:
        result = await db.execute(select(PlatformConfig).where(PlatformConfig.key == key))
        row = result.scalar_one_or_none()
        if row is None:
            return default

        # Populate cache
        try:
            redis = await get_redis()
            await redis.setex(cache_key, _CACHE_TTL, row.value)
        except Exception:
            pass

        return row.value
    except Exception:
        return default


async def set_config(db: AsyncSession, key: str, value: str, actor_id: str) -> None:
    """
    FR-ADM-04: Write platform config value to DB and invalidate Redis cache.
    """
    result = await db.execute(select(PlatformConfig).where(PlatformConfig.key == key))
    row = result.scalar_one_or_none()
    if row is None:
        row = PlatformConfig(key=key, value=value, updated_by_id=actor_id)
        db.add(row)
    else:
        row.value = value
        row.updated_by_id = actor_id

    await db.flush()

    # Invalidate Redis cache
    redis = await get_redis()
    await redis.delete(f"{_CACHE_PREFIX}{key}")
