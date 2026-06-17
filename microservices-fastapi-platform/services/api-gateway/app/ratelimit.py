import redis.asyncio as redis
import structlog

from .config import settings

logger = structlog.get_logger(__name__)


class RateLimiter:
    """Fixed-window rate limiter backed by Redis.

    Redis (not in-process state) is what makes the limit consistent across the
    multiple gateway workers/replicas. It fails open: if Redis is unreachable we
    let the request through rather than turning a cache outage into an outage.
    """

    def __init__(self, client: redis.Redis):
        self._client = client

    async def hit(self, identity: str) -> tuple[bool, int]:
        window = settings.rate_limit_window
        key = f"v1:ratelimit:{identity}:{settings.rate_limit_requests}"
        try:
            pipe = self._client.pipeline()
            pipe.incr(key)
            pipe.expire(key, window, nx=True)
            count, _ = await pipe.execute()
        except redis.RedisError as exc:
            logger.warning("ratelimit.unavailable", error=str(exc))
            return True, 0

        if count > settings.rate_limit_requests:
            ttl = await self._client.ttl(key)
            return False, max(ttl, 1)
        return True, 0
