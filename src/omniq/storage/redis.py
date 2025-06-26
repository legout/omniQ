import asyncio
import logging
from typing import List, Optional

try:
    import redis.asyncio as redis
except ImportError:
    redis = None

from omniq.models import Schedule, Task, TaskResult
from omniq.serialization import default_serializer
from omniq.storage import BaseResultStorage, BaseScheduleStorage, BaseTaskQueue

logger = logging.getLogger(__name__)


class RedisTaskQueue(BaseTaskQueue):
    """
    A task queue using Redis. It uses the reliable RPOPLPUSH (LMOVE) pattern.
    """

    def __init__(self, url: str):
        if redis is None:
            raise ImportError("Please install 'omniq[redis]' to use the Redis backend.")
        self.redis: redis.Redis = redis.from_url(url, decode_responses=False)
        self.tasks_key_prefix = "omniq:task:"
        self.queue_key_prefix = "omniq:queue:"

    def _get_queue_key(self, queue_name: str) -> str:
        return f"{self.queue_key_prefix}{queue_name}"

    def _get_task_key(self, task_id: str) -> str:
        return f"{self.tasks_key_prefix}{task_id}"

    def _get_processing_key(self, queue_name: str) -> str:
        return f"{self.queue_key_prefix}{queue_name}:processing"

    async def enqueue(self, task: Task) -> str:
        if task.dependencies:
            raise NotImplementedError(
                "Task dependencies are not supported by the Redis backend in this version."
            )

        task_key = self._get_task_key(task.id)
        queue_key = self._get_queue_key(task.queue)
        serialized_task = default_serializer.serialize(task)

        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.set(task_key, serialized_task)
            pipe.lpush(queue_key, task.id)
            await pipe.execute()
        return task.id

    async def dequeue(self, queues: List[str], timeout: int = 0) -> Optional[Task]:
        start_time = asyncio.get_event_loop().time()
        while True:
            for queue_name in queues:
                source_key = self._get_queue_key(queue_name)
                processing_key = self._get_processing_key(queue_name)

                task_id_bytes = await self.redis.lmove(
                    source_key, processing_key, "RIGHT", "LEFT"
                )

                if task_id_bytes:
                    task_id = task_id_bytes.decode()
                    task_key = self._get_task_key(task_id)
                    serialized_task = await self.redis.get(task_key)

                    if not serialized_task:
                        logger.warning(
                            f"Task data for {task_id} not found, removing from processing."
                        )
                        await self.redis.lrem(processing_key, 1, task_id_bytes)
                        continue

                    task = default_serializer.deserialize(serialized_task, target_type=Task)
                    setattr(task, "_processing_key", processing_key)
                    return task

            if timeout == 0 or (asyncio.get_event_loop().time() - start_time) >= timeout:
                return None

            await asyncio.sleep(0.1)  # Polling delay

    async def get_task(self, task_id: str) -> Optional[Task]:
        task_key = self._get_task_key(task_id)
        serialized_task = await self.redis.get(task_key)
        if serialized_task:
            return default_serializer.deserialize(serialized_task, target_type=Task)
        return None

    async def ack(self, task: Task) -> None:
        processing_key = getattr(task, "_processing_key", None)
        if not processing_key:
            logger.warning(f"Cannot ACK task {task.id}: missing _processing_key.")
            return

        task_key = self._get_task_key(task.id)
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.lrem(processing_key, 1, task.id.encode())
            pipe.delete(task_key)
            await pipe.execute()

    async def nack(self, task: Task, requeue: bool = True) -> None:
        processing_key = getattr(task, "_processing_key", None)
        if not processing_key:
            logger.warning(f"Cannot NACK task {task.id}: missing _processing_key.")
            return

        if requeue:
            queue_key = self._get_queue_key(task.queue)
            task_key = self._get_task_key(task.id)
            new_data = default_serializer.serialize(task)

            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.set(task_key, new_data)
                pipe.lmove(processing_key, queue_key, "RIGHT", "LEFT")
                await pipe.execute()
        else:
            # For DLQ, we could move it to a dead-letter list. For now, just delete.
            await self.ack(task)

    async def list_pending_tasks(self, queue: Optional[str] = None, limit: int = 20) -> List[Task]:
        raise NotImplementedError(
            "Listing pending tasks is not efficiently supported by the Redis backend without dedicated lists."
        )

    async def list_failed_tasks(self, queue: Optional[str] = None, limit: int = 20) -> List[Task]:
        raise NotImplementedError(
            "Listing failed tasks is not efficiently supported by the Redis backend without dedicated lists."
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.redis.close()


class RedisScheduleStorage(BaseScheduleStorage):
    """
    Schedule storage using Redis.

    This implementation stores all schedules in a single Redis Hash, where each
    field is a schedule ID and the value is the serialized schedule. This is
    efficient for typical use cases and leverages Redis's atomic operations
    on hash fields.
    """

    def __init__(self, url: str):
        if redis is None:
            raise ImportError("Please install 'omniq[redis]' to use the Redis backend.")
        self.redis: redis.Redis = redis.from_url(url, decode_responses=False)
        self.schedules_hash_key = "omniq:schedules"

    async def add_schedule(self, schedule: Schedule) -> str:
        serialized_schedule = default_serializer.serialize(schedule)
        await self.redis.hset(self.schedules_hash_key, schedule.id, serialized_schedule)
        return schedule.id

    async def get_schedule(self, schedule_id: str) -> Optional[Schedule]:
        serialized_schedule = await self.redis.hget(self.schedules_hash_key, schedule_id)
        if serialized_schedule:
            return default_serializer.deserialize(serialized_schedule, target_type=Schedule)
        return None

    async def list_schedules(self) -> List[Schedule]:
        all_schedules_data = await self.redis.hvals(self.schedules_hash_key)
        return [
            default_serializer.deserialize(data, target_type=Schedule)
            for data in all_schedules_data
        ]

    async def delete_schedule(self, schedule_id: str) -> None:
        await self.redis.hdel(self.schedules_hash_key, schedule_id)

    async def _update_pause_status(
        self, schedule_id: str, is_paused: bool
    ) -> Optional[Schedule]:
        serialized_schedule = await self.redis.hget(self.schedules_hash_key, schedule_id)
        if not serialized_schedule:
            return None

        schedule = default_serializer.deserialize(serialized_schedule, target_type=Schedule)
        schedule.is_paused = is_paused

        new_serialized_schedule = default_serializer.serialize(schedule)
        await self.redis.hset(self.schedules_hash_key, schedule_id, new_serialized_schedule)
        return schedule

    async def pause_schedule(self, schedule_id: str) -> Optional[Schedule]:
        return await self._update_pause_status(schedule_id, True)

    async def resume_schedule(self, schedule_id: str) -> Optional[Schedule]:
        return await self._update_pause_status(schedule_id, False)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.redis.close()


class RedisResultStorage(BaseResultStorage):
    """Result storage using Redis."""

    def __init__(self, url: str):
        if redis is None:
            raise ImportError("Please install 'omniq[redis]' to use the Redis backend.")
        self.redis: redis.Redis = redis.from_url(url, decode_responses=False)
        self.results_key_prefix = "omniq:result:"

    def _get_result_key(self, task_id: str) -> str:
        return f"{self.results_key_prefix}{task_id}"

    async def store(self, result: TaskResult) -> None:
        key = self._get_result_key(result.task_id)
        serialized_result = default_serializer.serialize(result)
        await self.redis.set(key, serialized_result, ex=result.ttl)

    async def get(self, task_id: str) -> Optional[TaskResult]:
        key = self._get_result_key(task_id)
        serialized_result = await self.redis.get(key)
        if serialized_result:
            return default_serializer.deserialize(serialized_result, target_type=TaskResult)
        return None

    async def delete(self, task_id: str) -> None:
        key = self._get_result_key(task_id)
        await self.redis.delete(key)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.redis.close()