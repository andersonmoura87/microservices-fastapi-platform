import json
from typing import Any

import redis.asyncio as redis
import structlog

from .config import settings

logger = structlog.get_logger(__name__)

_client: redis.Redis | None = None


def get_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(settings.redis_url, decode_responses=True)
    return _client


def key(*parts: str) -> str:
    # Version prefix guards against serving values written under an older schema.
    return ":".join((settings.cache_version, "data", *parts))


async def get_json(cache_key: str) -> Any | None:
    try:
        raw = await get_client().get(cache_key)
    except redis.RedisError as exc:
        # Cache is a best-effort optimisation — never let it break the request path.
        logger.warning("cache.get_failed", key=cache_key, error=str(exc))
        return None
    return json.loads(raw) if raw else None


async def set_json(cache_key: str, value: Any, ttl: int | None = None) -> None:
    try:
        await get_client().set(
            cache_key, json.dumps(value, default=str), ex=ttl or settings.cache_ttl
        )
    except redis.RedisError as exc:
        logger.warning("cache.set_failed", key=cache_key, error=str(exc))


async def delete(*cache_keys: str) -> None:
    if not cache_keys:
        return
    try:
        await get_client().delete(*cache_keys)
    except redis.RedisError as exc:
        logger.warning("cache.delete_failed", keys=cache_keys, error=str(exc))
