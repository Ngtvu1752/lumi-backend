import json
import uuid
from datetime import datetime

import redis.asyncio as redis

from app.core.config import settings
from app.schemas.energy import EnergyScheduleResponse

_redis: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


def _cache_key(user_id: uuid.UUID, date: datetime) -> str:
    return f"energy:{user_id}:{date.strftime('%Y-%m-%d')}"


async def get_cached_energy(user_id: uuid.UUID, date: datetime) -> EnergyScheduleResponse | None:
    r = await get_redis()
    data = await r.get(_cache_key(user_id, date))
    if data:
        parsed = json.loads(data)
        return EnergyScheduleResponse.model_validate(parsed)
    return None


async def set_cached_energy(user_id: uuid.UUID, date: datetime, response: EnergyScheduleResponse) -> None:
    r = await get_redis()
    payload = response.model_dump_json()
    await r.set(_cache_key(user_id, date), payload, ex=settings.ENERGY_CACHE_TTL)


async def invalidate_energy_cache(user_id: uuid.UUID, date: datetime) -> None:
    r = await get_redis()
    await r.delete(_cache_key(user_id, date))
