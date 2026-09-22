import logging

from app.exceptions.http_exceptions import APIException
from app.services.common.redis import redis_client

logger = logging.getLogger("rate_limit")

_FIXED_WINDOW_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
return {current, redis.call('TTL', KEYS[1])}
"""


async def enforce_rate_limit(key: str, *, limit: int, window_seconds: int) -> None:
    """Apply an atomic Redis fixed-window limit; fail open if Redis is unavailable."""
    try:
        current, ttl = await redis_client.redis.eval(
            _FIXED_WINDOW_SCRIPT, 1, f"rate_limit:{key}", window_seconds
        )
    except Exception as exc:
        logger.warning("Rate limit unavailable: error_type=%s", type(exc).__name__)
        return

    if int(current) > limit:
        raise APIException(
            code=1011,
            message="Too many requests, please try again later",
            status_code=429,
            data={"retry_after_seconds": max(int(ttl), 1)},
        )
