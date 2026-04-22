import hashlib

from fastapi import Request
from redis import Redis

from app.core.config import settings

_redis: Redis | None = None


def _client() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


def _identify(request: Request) -> str:
    client_id = request.headers.get("x-client-id")
    if client_id:
        return f"cid:{client_id[:64]}"

    forwarded = request.headers.get("x-forwarded-for")
    ip = forwarded.split(",")[0].strip() if forwarded else (
        request.client.host if request.client else "unknown"
    )
    return "ip:" + hashlib.sha256(ip.encode()).hexdigest()[:32]


def _key(identity: str) -> str:
    return f"anon_quota:{identity}"


def get_remaining(request: Request) -> int:
    used = _client().get(_key(_identify(request)))
    used_int = int(used) if used else 0
    return max(0, settings.FREE_ANONYMOUS_USES - used_int)


def consume(request: Request) -> int:
    """Increment usage and return remaining."""
    key = _key(_identify(request))
    pipe = _client().pipeline()
    pipe.incr(key)
    pipe.expire(key, settings.ANONYMOUS_QUOTA_TTL_SECONDS)
    used_int, _ = pipe.execute()
    return max(0, settings.FREE_ANONYMOUS_USES - int(used_int))
