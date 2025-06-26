import asyncio
from typing import Dict, List, Optional

try:
    import redis.asyncio as redis
except ImportError:
    redis = None

from omniq.models import Schedule
from omniq.serialization import default_serializer
from omniq.storage import BaseScheduleStorage


class RedisScheduleStorage(BaseScheduleStorage):
    """Schedule storage using Redis."""

    def __init__(self, url: str):
        if redis is None:
            raise ImportError("Please install 'omniq[redis]' to use the Redis backend.")
        self.redis: redis.Redis = redis.from_url(url, decode_responses=False)
        self.schedules_key = "omniq:schedules"
        self._lock = asyncio.Lock()

    async def add_schedule(self, schedule: Schedule) -> str:
        async with self._lock:
            await self._load_schedules()
            self._schedules[schedule.id] = schedule
            await self._save_schedules()
        return schedule.id

    async def get_schedule(self, schedule_id: str) -> Optional[Schedule]:
        async with self._lock:
            await self._load_schedules()
            return self._schedules.get(schedule_id)

    async def list_schedules(self) -> List[Schedule]:
        async with self._lock:
            await self._load_schedules()
            return list(self._schedules.values())

    async def delete_schedule(self, schedule_id: str) -> None:
        async with self._lock:
            await self._load_schedules()
            if schedule_id in self._schedules:
                del self._schedules[schedule_id]
                await self._save_schedules()

    async def _load_schedules(self) -> None:
        """Load schedules from Redis."""
        data = await self.redis.get(self.schedules_key)
        if data:
            self._schedules: Dict[str, Schedule] = default_serializer.deserialize(data)
        else:
            self._schedules: Dict[str, Schedule] = {}

    async def _save_schedules(self) -> None:
        """Save schedules to Redis."""
        data = default_serializer.serialize(self._schedules)
        await self.redis.set(self.schedules_key, data)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.redis.close()